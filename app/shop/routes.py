import os
import json
import io
from datetime import datetime, timezone
from flask import redirect, url_for, request, flash, render_template, send_file, \
    current_app, jsonify, Response
from flask_login import login_required, current_user
import sqlalchemy as sa
from app import db, storage_service
from app.models import AdminAction, Vendor, File, Metadata
from app.utils import get_timestamp
from app.shop import bp
from app.shop.forms import SubmitForm, QueryProductsForm
from app.shop.price_tags import generate_pdf
from app.integrations.sheety import clear_inventory_updates_sheet, \
    fetch_etiquetas, fetch_inventory_updates
from app.integrations.gsheets import append_df_to_sheet, clear_sheet_except_header
from app.shop.inventory import get_local_inventory, delete_local_inventory, \
    write_local_inventory, complete_sheety_data, adjust_variant_quantities, \
        set_variant_price, set_variant_cost, set_metafields, get_variants_using_query
from app.shop.captura import get_captura, captura_cleanup_and_validation, \
    add_product_handles, upload_to_shopify, add_cost_histories

@bp.route('/etiquetas-generar-pdf')
@login_required
def generate_labels():
    data = fetch_etiquetas()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(current_app.config['DATA_DIR'], f"pdfs/etiquetas_{timestamp}.pdf")
    if current_app.config['USE_LOCAL_STORAGE']:
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        generate_pdf(data, pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)
    else:
        data = fetch_etiquetas()

        pdf_buffer = io.BytesIO()
        generate_pdf(data, pdf_buffer)
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"labels_{timestamp}.pdf"

        storage = storage_service()
        pdf_content = pdf_buffer.getvalue()
        storage.upload_bytes(f'labels/{pdf_filename}', io.BytesIO(pdf_content), content_type='application/pdf')

        return Response(pdf_content, content_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename={pdf_filename}"
        })

@bp.route('/etiquetas')
@login_required
def etiquetas():    
    return render_template('shop/price_tags.html', title='Etiquetas')

@bp.route('/productos', methods=['GET', 'POST'])
@login_required
def products():
    form = QueryProductsForm()

    if form.validate_on_submit():
        state = f"metafields.custom.estado:'{form.state.data}'" if form.state.data else ''
        town = f"metafields.custom.pueblo:'{form.town.data}'" if form.town.data else ''
        vendor = f"vendor:'{form.vendor.data}'" if form.vendor.data else ''

        filters = [field for field in [state, town, vendor] if field]

        if not filters:
            flash('No seleccionaste ningún filtro.', 'warning')
            return redirect(url_for('shop.products'))
        
        query = ' AND '.join(filters)
        print(f'{query = }')

        return redirect(url_for('shop.query_products', query=query))

    return render_template('shop/products_search.html', form=form)

@bp.route('/productos-busqueda', methods=['GET', 'POST'])
@login_required
def query_products():
    query = request.args.get('query')
    print(query)
    if not query:
        flash('Something went wrong.', 'error')
        current_app.logger.error('No query was entered.')
        return redirect(url_for('dashboard.index'))
    
    nodes, cursor = get_variants_using_query(query)

    # if cursor: # TODO along with the to-do inget_variants_using_query()
        # show next page button
    prods = []
    for node in nodes:
        metafields = {meta['key']: meta['value'] for meta in node['metafields']['nodes']}
        prod = {
            'vendor': node['vendor'],
            'title': node['title'],
            'pueblo': metafields.get('custom.pueblo'),
            'estado': metafields.get('custom.estado'),
            'variants': [{
                'variantTitle': variant['title'],
                'cost': variant['inventoryItem']['unitCost']['amount'],
                'costHistory': variant['metafield'] if variant['metafield'] else None,
                'price': variant['price'],
                'sku': variant['sku'],
                'quantity': variant['inventoryItem']['inventoryLevel']['quantities'][0]['quantity'],
            } for variant in node['variants']['nodes']],
        }
        prods.append(prod)

    
    return render_template('shop/products_results.html', products=prods)

@bp.route('/artesanos')
@login_required
def vendors():
    page = request.args.get('page', 1, int)
    query = sa.select(Vendor).order_by(Vendor.name)

    vendors = db.paginate(query, page=page, 
                        per_page=current_app.config.get('VENDORS_PER_PAGE', 50), 
                        error_out=False)
    pagination = {
        'page': page,
        'next_url': url_for('shop.vendors', page=vendors.next_num) \
            if vendors.has_next else None,
        'prev_url': url_for('shop.vendors', page=vendors.prev_num) \
            if vendors.has_prev else None,
    }

    return render_template('shop/vendors.html', vendors=vendors, pagination=pagination)

# --------------------------- ACTUALIZAR CANTIDADES --------------------------- #
@bp.route('/cantidades', methods=['GET', 'POST'])
@login_required
def update_product_quantities():
    refresh_form, confirm_form = SubmitForm(), SubmitForm()
    refresh_form.submit.label.text = 'Actualizar desde Google Sheets'
    confirm_form.submit.label.text = 'Subir a Shopify'

    if request.method == 'GET':
        df, time, total_errors = get_local_inventory()
        data = None
        enable_upload_btn = False

        if df is not None and df.shape[0] > 0:
            if total_errors:
                flash(f'No es posible subir los productos actualmente: hay {total_errors} SKU con errores.', 'warning')
            else:
                enable_upload_btn=True
            data = json.loads(df.to_json(orient='records'))
            for row in data:
                if row.get('costHistory'):
                    row['costHistory'] = json.loads(row['costHistory'])

        return render_template('shop/actualizar_cantidades.html', 
                        refresh_form=refresh_form, confirm_form=confirm_form, 
                        data=data, time=time, enable_upload=enable_upload_btn)
    
    if refresh_form.validate_on_submit():  # Only refresh_form targets this view on submit.
        sheety = fetch_inventory_updates()

        if sheety.shape[0] == 0:
            flash('No se encontraron productos en Google Sheets', 'error')
            delete_local_inventory()

            return redirect(url_for('shop.update_product_quantities'))
        
        df = complete_sheety_data(sheety)
        write_local_inventory(df)

        return redirect(url_for('shop.update_product_quantities'))
    
@bp.route('/cantidades-cargando', methods=['POST'])
@login_required
def start_upload_product_quantities():
    if not current_user.is_superadmin:
        flash("Tu usuario no tiene los permisos necesarios para realizar esta acción.", 'warning')
        return redirect(url_for('shop.update_product_quantities'))
    
    form = SubmitForm()

    if form.validate_on_submit():
        return redirect(url_for('dashboard.loading', 
                                process_description='Actualizando Inventario...', 
                                process_view='shop.upload_product_quantities',
                                final_view='shop.update_product_quantities'))

@bp.route('/cantidades-subir')
@login_required
def upload_product_quantities():    
    # TODO: view is dirty but working... needs a lot of refactoring
    df, timestamp, total_errors = get_local_inventory()
    if total_errors > 0:
        flash('No es posible subir cantidades mientras aún hay errores. '
              'Porfavor revisa los reglones marcadoes en rojo.', 
              'error')
        return jsonify({'redirect_url': url_for('shop.update_product_quantities')})
    
    if not current_user.is_superadmin:
        flash('Tu usuario no tiene los permisos necesarios para realizar esta acción.', 
              'warning')
        return jsonify({'redirect_url': url_for('shop.update_product_quantities')})

    # TODO: check for updates in sheety before adjusting. Don't do it if timestamp is very recent.

    # UPDATE INVENTORY QUANTITIES
    quantity_changes = [
        {
            'inventoryItemId': row['inventoryItemId'],
            'delta': row['quantity']
        } 
        for _, row in df.iterrows() ]
    try:
        adjust_variant_quantities(quantity_changes)
    except:
        flash('Fracasó el intento de actualizar el inventario. Si el error persiste, contacta a un administrador.', 'error')
        return jsonify({'redirect_url': url_for('shop.update_product_quantities')})
    
    flash("Se actualizaron las cantidades correctamente.")
    update_quantities_action = AdminAction(action="Actualizar cantidades de inventario", status='Completado', admin=current_user)
    db.session.add(update_quantities_action)
    db.session.commit()

    # UPDATE PRODUCT PRICE
    price_changes = df.loc[~df['newPrice'].isna()]
    update_prices_action = AdminAction(action="Actualizar precios de venta de variantes", status='En progreso', admin=current_user)
    db.session.add(update_prices_action)
    db.session.commit()
    error_skus = []
    for _, row in price_changes.iterrows():
        try:
            set_variant_price(row['productId'], row['variantId'],row['newPrice'])
        except:
            error_skus += row['sku']
            update_prices_action.errors += f"{row['sku']},"
            continue
    if error_skus:
        flash('Hubieron errores al actualizar los precios de venta de algunos productos.' 
              'Por favor actualízalos a mano. \nskus: {", ".join(error_skus)}', 
              'error')
        update_prices_action.status = 'Incompleto'
    else:
        flash("Se actualizaron los precios de venta correctamente")
        update_prices_action.status = 'Completado'
    db.session.add(update_prices_action)
    db.session.commit()

    # UPDATE PRODUCT COST
    cost_changes = df.loc[~df['newCost'].isna()]
    update_costs_action = AdminAction(action="Actualizar precios de compra de variantes", 
                                      status='En progreso', admin=current_user)
    db.session.add(update_costs_action)
    db.session.commit()
    error_skus = []
    for _, row in cost_changes.iterrows():
        try:
            set_variant_cost(row['inventoryItemId'], row['newCost'])
        except:
            error_skus += row['sku']
            update_costs_action.errors += f"{row['sku']},"
            continue
    if error_skus:
        flash(f'Hubieron problemas al actualizar los precios de compra de algunos productos.'
              ' Por favor actualízalos a mano. \nskus: {", ".join(error_skus)}',
              'error')
        update_costs_action.status = 'Incompleto'
    else:
        flash("Se actualizaron los precios de compra correctamente")
        update_costs_action.status = 'Completado'
    db.session.add(update_costs_action)
    db.session.commit()

    # CLEAR GOOGLE SHEETS SPREADSHEET
    #clear_inventory_updates_sheet()

    # UPDATE COST HISTORY METAFIELD
    cost_histories = df['costHistory'].to_list()
    for i in range(len(cost_histories)):
        cost_histories[i] = json.loads(cost_histories[i])
    update_cost_history_action = AdminAction(action="Actualizar historial de costos (variant metafield)", status='En progreso', admin=current_user)
    db.session.add(update_cost_history_action)
    db.session.commit()
    try:
        set_metafields(cost_histories)
    except:
        flash('Hubieron errores al actualizar el metafield "cost history"', 'error')
        update_cost_history_action.status = 'Incompleto'
    else:
        flash("Se actualizaron los metafields correctamente")
        update_cost_history_action.status = 'Completado'
    db.session.add(update_cost_history_action)
    db.session.commit()

    return jsonify({'redirect_url': url_for('shop.update_product_quantities')})

# ---------------------------------- CAPTURA ---------------------------------- #
@bp.route('/captura', methods=['GET', 'POST'])
@login_required
def review_new_products():
    refresh_form, upload_form = SubmitForm(), SubmitForm()
    refresh_form.submit.label.text = 'Actualizar desde Google Sheets'
    upload_form.submit.label.text = 'Subir a Shopify'

    if request.method == 'GET': #only refresh form tagets this endpoint
        df = get_captura() # TODO make async
    
        column_list = ['rowNum', 'vendor', 'title', 'sku', 'cost', 'price', 'quantityDelta', 'dateOfPurchase']

        if df.shape[0] == 0:
            return render_template('shop/captura.html', title='Captura', 
                                   refresh_form=refresh_form, column_list=column_list)

        products = captura_cleanup_and_validation(df)
        total_warnings = products['warnings'].count()
        total_errors = products['errors'].count()
        products_dict = products.to_dict(orient='records')
        
        return render_template('shop/captura.html', title='Captura', 
                               refresh_form=refresh_form, upload_form=upload_form,
                               products=products_dict, column_list=column_list, 
                               errors=total_errors, warnings=total_warnings)
    
    if refresh_form.validate_on_submit():
        print('refresh clicked')
        return redirect(url_for('shop.review_new_products'))

@bp.route('/captura-cargando', methods=['POST'])
@login_required
def start_upload_new_products():
    if not current_user.is_superadmin:
        flash("Tu usuario no tiene los permisos necesarios para realizar esta acción.", 'warning')
        return redirect(url_for('shop.review_new_products'))
    
    form = SubmitForm()

    if form.validate_on_submit():
        return redirect(url_for('dashboard.loading', 
                                process_description='Publicando productos...', 
                                process_view='shop.upload_new_products',
                                final_view='shop.review_new_products'))

@bp.route('/captura-proceso')
@login_required
def upload_new_products():
    if not current_user.is_superadmin:
        flash("Tu usuario no tiene los permisos necesarios para realizar esta acción.", 'warning')
        return redirect(url_for('shop.review_new_products'))
    
    df = get_captura()
    if df.shape[0] == 0:
        flash('There are no products to upload')
        return redirect(url_for('dashboard.index'))

    products = captura_cleanup_and_validation(df)
    total_errors = products['errors'].count()
    total_warnings = products['warnings'].count()

    # check for errors and warnings
    if total_errors:
        flash('No es posible subir cantidades mientras aún hay errores. '
              'Porfavor revisa los reglones marcadoes en rojo.', 
              'error')
        return jsonify({'redirect_url': url_for('shop.review_new_products')})
    
    if total_warnings and not current_user.is_superadmin:
        flash('Si los productos tienen advertencias (renglones en amarillo), '
              'solo un admisnitrador los puede subir.', 
              'error')
        return jsonify({'redirect_url': url_for('shop.review_new_products')})

    # Add product handle and cost history
    if 'handle' not in products:
        products = add_product_handles(products)
    else:
        current_app.logger.error(
            'Cannot add automatic handles with add_product_handles() if custom handles have been entered.')
        flash('No se subieron los productos pues no puede haber una columna "handle" en los datos.', 
              'error')
        return jsonify({'redirect_url': url_for('shop.review_new_products')})

    products = add_cost_histories(products)
    
    # create the AdminAction
    publish_products_action = AdminAction(action="Publicar Productos", 
                                          status='En proceso...', 
                                          admin=current_user)
    db.session.add(publish_products_action)
    db.session.commit()

    timestamp = int(get_timestamp())

    # captura_path = os.path.join(current_app.config['DATA_DIR'], 'captura')
    # os.makedirs(captura_path, exist_ok=True)

    # add files to the AdminAction
    storage = storage_service()

    raw_csv_path = f'captura/raw_products{timestamp}.csv'
    storage.upload_csv(raw_csv_path, df)
    raw_csv_file = File(path=raw_csv_path, admin_action=publish_products_action)
    db.session.add(raw_csv_file)
    db.session.commit()

    # add files to the AdminAction
    processed_csv_path = f'captura/processed_products{timestamp}.csv'
    storage.upload_csv(processed_csv_path, products)
    processed_csv_file = File(path=processed_csv_path, admin_action=publish_products_action)
    db.session.add(processed_csv_file)
    db.session.commit()

    try:
        upload_to_shopify(products)
    except Exception as e:
        current_app.logger.error(e)
        flash('Sucedió un error inesperado. No vuelvas a subir los productos. '
              'Contacta a un administrador.', 
              'error')
    else:
        Metadata.set_last_product_handle(products.iloc[-1]['handle'])

        captura_id = current_app.config['GSHEETS_CAPTURA_ID']
        append_df_to_sheet(captura_id, 'Historial', products)
        clear_sheet_except_header(captura_id, 'Captura')
        publish_products_action.status = "Completado"
        db.session.add(publish_products_action)
        db.session.commit()

    return jsonify({'redirect_url': url_for('shop.review_new_products')})
