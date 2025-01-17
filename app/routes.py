import os
import time
import json
from datetime import datetime, timezone
import pandas as pd
from numpy import nan
from flask import render_template, abort, flash, redirect, url_for, request, send_file
from flask_login import login_required, current_user
import sqlalchemy as sa
from app import app, db
from app.models import User, AdminAction
from app.forms import UserSettingsForm, SubmitForm
from app.sheety import fetch_sheet_data
from app.price_tags import generate_pdf
from app.shopify import get_variants_by_sku

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/action-log')
@login_required
def action_log():
    actions = db.session.scalars(sa.select(AdminAction)).all()
    return render_template('action_log.html', actions=actions) #TODO add pagination here and in the user profiles
    #TODO: add number id to action log and proper spacing

@app.route('/user/<id>')
@login_required
def user(id):
    user = db.session.get(User, id)
    if user is None:
        abort(404)

    actions = db.session.scalars(sa.select(AdminAction).where(AdminAction.admin == user))

    return render_template('user.html', user=user, actions=actions)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    form = UserSettingsForm()

    if form.validate_on_submit():
        current_user.fname = form.fname.data
        current_user.lname = form.lname.data
        db.session.commit()
        flash('Tus cambios se guardaron con éxito.')
        return redirect(url_for('user', id=current_user.id))
    
    elif request.method == 'GET':
        form.fname.data = current_user.fname
        form.lname.data = current_user.lname

    return render_template('user_settings.html', title='Editar Perfil', form=form)

@app.route('/captura')
@login_required
def captura():
    return render_template('captura.html', title='Captura')

@app.route('/actualizar_cantidades', methods=['GET', 'POST'])
@login_required
def update_product_quantities():
    refresh_form, confirm_form = SubmitForm(), SubmitForm()
    refresh_form.submit.label.text = 'Actualizar desde Google Sheets'
    confirm_form.submit.label.text = 'Subir a Shopify'

    base_path = os.path.join(os.getcwd(), 'data/update_quantities')

    if request.method == 'GET':
        try:
            local_data = pd.read_csv('data/update_quantities/quantities.csv')
            with open(os.path.join(base_path, 'timestamp'), 'r') as f:
                saved_time = float(f.read(50))
                time = datetime.fromtimestamp(saved_time, 
                                                       tz=timezone.utc)
            total_errors = local_data.loc[local_data['errors'] != 'none', 'errors'].count()
            flash(f'No es posible subir los productos actualmente ya que hay {total_errors} SKU con errores.', 'warning')
            data = json.loads(local_data.to_json(orient='records'))

        except FileNotFoundError:
            data = None
            time = None

        return render_template('actualizar_cantidades.html', 
                           refresh_form=refresh_form, confirm_form=confirm_form, 
                           data=data, time=time)
    
    if refresh_form.validate_on_submit():
        sheety = fetch_sheet_data('actualizarCantidades', 'cantidades')        

        if sheety.shape[0] == 0:
            flash('No se encontraron productos en Google Sheets', 'error')
            return redirect(url_for('update_product_quantities'))
        
        # csv cols: sku, qty, display_name, vendor, new_price, price_delta, new_cost, cost_delta
        combined_data = []
        for _, row in sheety.iterrows():
            sku = row['clave (sku)']
            new_price = row['nuevoPrecioVenta']
            new_cost = row['nuevoPrecioCompra']

            # Query shopify for the variant corresponding to this SKU
            variants = get_variants_by_sku(sku)

            if len(variants) >= 2:
                combined_data.append({
                    'sku': sku,
                    'errors': f'Hay más de un producto con clave "{sku}".'
                })
                continue

            elif len(variants) == 0:
                combined_data.append({
                    'sku': sku,
                    'errors': f'No se encontró ningún producto con clave "{sku}".'
                })
                continue
            
            variant = variants[0]
            
            # row is from Google Sheets and variant is the corresponding Shopify productVariant
            combined_product_data = {
                'sku': sku, 
                'quantity': row['cantidadAAgregar'], 
                'displayName': variant['displayName'],
                'vendor': variant['vendor'],
                'newPrice': new_price if new_price else nan,
                'priceDelta': new_price - float(variant['price']) if new_price else nan,
                'newCost': new_cost if new_cost else nan,
                'costDelta': new_cost - float(variant['unitCost']) if new_cost else nan,
                'errors': 'none',
            }
            combined_data.append(combined_product_data)
        
        # write combined data to csv for loading and add timestamp
        df = pd.DataFrame.from_records(combined_data)
        df.to_csv(os.path.join(base_path, 'quantities.csv'))
        with open(os.path.join(base_path, 'timestamp'), 'w') as f:
            now = datetime.now(timezone.utc)
            f.write(str(now.timestamp()))

        return redirect(url_for('update_product_quantities'))

@app.route('/subir_inventario_shopify', methods=['POST'])
@login_required
def upload_product_quantities():
    # TODO: admin action
    # we need the location Id. See: https://shopify.dev/docs/api/admin-graphql/2025-01/mutations/inventoryAdjustQuantities

    # 1. upload products
    # 2. delete files in data/update_quantities
    # 3. delete rows from Google Sheets and put them in history

    return redirect(url_for('update_product_quantities'))

@app.route('/etiquetas')
def etiquetas():    
    return render_template('price_tags.html', title='Etiquetas')

@app.route('/generar-pdf-etiquetas')
@login_required
def generate_labels():
    try:
        data = fetch_sheet_data('etiquetas', 'etiquetas')
        
        timestamp = int(time.time())
        pdf_filename = f"labels_{timestamp}.pdf"
        pdf_path = os.path.join(app.static_folder, 'pdfs', pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        generate_pdf(data, pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

    except Exception as e:
        app.logger.error(f"Error generating labels: {e}")
        flash('Failed to generate labels. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/exportar-productos')
@login_required
def exportar_productos():
    return 'building...'