import click
import pandas as pd
import sqlalchemy as sa
from flask import Blueprint
from app import db
from app.models import Vendor
from app.utils import simple_lower_ascii

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
        print(f"Adding '{name}'...")
        conflicting_vendor = db.session.scalar(sa.select(Vendor).where(Vendor.compare_name == simple_lower_ascii(name)))
        if not conflicting_vendor:
            new_vendor = Vendor()
            new_vendor.set_name(name)
            db.session.add(new_vendor)

        else:
            existing_vendor = db.session.scalar(sa.select(Vendor).where(Vendor.name == name))
            if existing_vendor:
                continue
            else: 
                print(f"Failed to add {name} because there is already a vendor with a similar name: {conflicting_vendor.name}.")
                print(f"Which name do you want to keep?\n  1. {conflicting_vendor.name}\n  2. {name}")

                while True:
                    user_input = input("Enter 1 or 2: ").strip()
                    if user_input in {"1", "2"}:
                        break
                    print("Invalid input.")

                if user_input == "1":
                    continue
                elif user_input == "2":
                    conflicting_vendor.name = name
                    db.session.add(conflicting_vendor)

        db.session.commit()

    print('Vendors added successfully.')
