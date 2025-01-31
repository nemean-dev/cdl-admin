import os
import json
from datetime import datetime, timezone
from flask import redirect, url_for, request, flash, render_template, send_file, current_app
from flask_login import login_required, current_user
import sqlalchemy as sa
from app import db
from app.models import AdminAction, Vendor
from app.shop import bp
from app.shop.forms import SubmitForm, QueryProductsForm
from app.shop.price_tags import generate_pdf
from app.integrations.sheety import clear_inventory_updates_sheet, fetch_etiquetas, fetch_inventory_updates
from app.shop.inventory import get_local_inventory, delete_local_inventory, write_local_inventory, complete_sheety_data,\
    adjust_variant_quantities, set_variant_price, set_variant_cost, set_metafields, get_variants_using_query
from app.shop.captura import get_captura, captura_clenup_and_validation

@bp.route('/generar-pdf-etiquetas')
@login_required
def generate_labels():
    try:
        data = fetch_etiquetas()
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"labels_{timestamp}.pdf"
        pdf_path = os.path.join(current_app.static_folder, 'pdfs', pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        generate_pdf(data, pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

    except Exception as e:
        current_app.logger.error(f"Error generating labels: {e}")
        flash('Failed to generate labels. Please try again.', 'danger')
        return redirect(url_for('dashboard.index'))

@bp.route('/actualizar_cantidades', methods=['GET', 'POST'])
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
    
@bp.route('/proceso-subir-cantidades', methods=['POST'])
@login_required
def start_upload_product_quantities():
    form = SubmitForm()

    if form.validate_on_submit():
        return redirect(url_for('dashboard.loading', 
                                process_description='Actualizando Inventario...', 
                                process_view='shop.upload_product_quantities',
                                final_view='shop.update_product_quantities'))
    
@bp.route('/subir-cantidades-shopify')
@login_required
def upload_product_quantities():
    # TODO: view is dirty but working... needs a lot of refactoring
    df, timestamp, total_errors = get_local_inventory()
    if total_errors > 0:
        flash('No es posible subir cantidades mientras aún hay errores. Porfavor revisa los reglones marcadoes en rojo.', 'error')
        return redirect(url_for('shop.update_product_quantities'))
    
    if not current_user.is_superadmin:
        flash('Tu usuario no tiene los permisos necesarios para realizar esta acción.')
        return redirect(url_for('shop.update_product_quantities'))

    # TODO: check for updates in sheety before adjusting. Don't do it if timestamp is very recent.
    # TODO 3 dicide which of these queries will update the metafield information for cost history, or create another one.

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
        return redirect(url_for('shop.update_product_quantities'))
    
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
        flash(f'Hubieron errores al actualizar los precios de venta de algunos productos. Por favor actualízalos a mano. \nskus: {", ".join(error_skus)}', 'error')
        update_prices_action.status = 'Incompleto'
    else:
        flash('Se actualizaron los precios de venta correctamente')
        update_prices_action.status = 'Completado'
    db.session.add(update_prices_action)
    db.session.commit()

    # UPDATE PRODUCT COST
    cost_changes = df.loc[~df['newCost'].isna()]
    update_costs_action = AdminAction(action="Actualizar precios de compra de variantes", status='En progreso', admin=current_user)
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
        flash(f'Hubieron problemas al actualizar los precios de compra de algunos productos. Por favor actualízalos a mano. \nskus: {", ".join(error_skus)}', 'error')
        update_costs_action.status = 'Incompleto'
    else:
        flash('Se actualizaron los precios de compra correctamente')
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

    return "finished"

@bp.route('/captura', methods=['GET', 'POST'])
@login_required
def captura():
    refresh_form, upload_form = SubmitForm(), SubmitForm()
    refresh_form.submit.label.text = 'Actualizar desde Google Sheets'
    upload_form.submit.label.text = 'Subir a Shopify'

    if request.method == 'GET':
        df = get_captura() # TODO make async
        column_list = ['rowNum', 'vendor', 'title', 'sku', 'cost', 'price', 'quantityDelta', 'dateOfPurchase']

        products = captura_clenup_and_validation(df)
        total_warnings = products['warnings'].count()
        total_errors = products['errors'].count()
        products = products.to_dict(orient='records')
        
        return render_template('shop/captura.html', title='Captura', 
                               refresh_form=refresh_form, upload_form=upload_form,
                               products=products, column_list=column_list, 
                               errors=total_errors, warnings=total_warnings)
    
    if refresh_form.validate_on_submit():
        return redirect(url_for('shop.captura'))

@bp.route('/proceso-subir-captura')
@login_required
def start_upload_new_products():
    return 'Not yet implemented...'

@bp.route('/etiquetas')
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

@bp.route('/query_products', methods=['GET', 'POST'])
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
