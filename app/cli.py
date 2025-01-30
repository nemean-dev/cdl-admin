import click
import pandas as pd
import sqlalchemy as sa
from flask import Blueprint
from app import db
from app.models import Vendor

bp = Blueprint('cli', __name__)

@bp.cli.command('add-vendors')
@click.argument('csv_path')
def add_vendors(csv_path):
    '''Load vendors from a CSV file into the db'''
    df = pd.read_csv(csv_path)

    # Remove rows if vendor is nan/empty
    df = df.dropna(subset=['Vendor'])
    df = df[df['Vendor'].str.strip() != '']

    vendors = df['Vendor'].unique()
    for name in vendors:
        existing_vendor = db.session.scalar(sa.select(Vendor).where(Vendor.name == name))
        if not existing_vendor:
            new_vendor = Vendor(name=name)
            db.session.add(new_vendor)
    db.session.commit()
    print('Vendors added successfully.')
