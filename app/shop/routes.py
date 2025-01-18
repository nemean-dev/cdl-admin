import os
import json
from datetime import datetime, timezone
from flask import redirect, url_for, request, flash, render_template, send_file
from flask_login import login_required, current_user
from app import app, db
from app.models import AdminAction
from app.shop import bp
from app.shop.forms import SubmitForm
from app.shop.price_tags import generate_pdf
from app.shop.sheety import clear_inventory_updates_sheet, fetch_etiquetas, fetch_inventory_updates
from app.shop.shopify import adjust_variant_quantities, set_variant_price, set_variant_cost
from app.shop.inventory_updates import get_local_inventory, delete_local_inventory, write_local_inventory, complete_sheety_data

@bp.route('/generar-pdf-etiquetas')
@login_required
def generate_labels():
    try:
        data = fetch_etiquetas()
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"labels_{timestamp}.pdf"
        pdf_path = os.path.join(app.static_folder, 'pdfs', pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        generate_pdf(data, pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

    except Exception as e:
        app.logger.error(f"Error generating labels: {e}")
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

            data = json.loads(df.to_json(orient='records'))
            enable_upload_btn=(total_errors==0)

        return render_template('actualizar_cantidades.html', 
                        refresh_form=refresh_form, confirm_form=confirm_form, 
                        data=data, time=time, enable_upload=enable_upload_btn)
    
    if refresh_form.validate_on_submit():
        sheety = fetch_inventory_updates('actualizarCantidades', 'cantidades')        

        if sheety.shape[0] == 0:
            flash('No se encontraron productos en Google Sheets', 'error')
            delete_local_inventory()

            return redirect(url_for('shop.update_product_quantities'))
        
        df = complete_sheety_data(sheety)
        write_local_inventory(df)

        return redirect(url_for('shop.update_product_quantities'))
    
@bp.route('/subir_inventario_shopify', methods=['POST'])
@login_required
def upload_product_quantities():
    # TODO: view is dirty but working... needs a lot of refactoring
    df, timestamp, total_errors = get_local_inventory()
    if total_errors > 0:
        flash('Cannot post data with errors.', 'error')
        return redirect(url_for('update_product_quantities'))
    
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
        pass
    except:
        flash('Fracasó el intento de actualizar el inventario. Si el error persiste, contacta a un administrador.', 'error')
        return redirect(url_for('update_product_quantities'))
    
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
        flash(f'Hubieron problemas al actualizar los precios de venta de algunos productos. Por favor actualízalos a mano. \nskus: {", ".join(error_skus)}', 'error')
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
        update_prices_action.status = 'Incompleto'
    else:
        flash('Se actualizaron los precios de compra correctamente')
        update_prices_action.status = 'Completado'
    db.session.add(update_prices_action)
    db.session.commit()

    # CLEAR GOOGLE SHEETS SPREADSHEET
    clear_inventory_updates_sheet()

    return redirect(url_for('shop.update_product_quantities'))

@bp.route('/captura')
@login_required
def captura():
    return render_template('captura.html', title='Captura')

@bp.route('/etiquetas')
def etiquetas():    
    return render_template('price_tags.html', title='Etiquetas')

@bp.route('/exportar-productos')
@login_required
def exportar_productos():
    return 'building...'