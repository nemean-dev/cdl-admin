from app import db, create_app
from app.models import User
import sqlalchemy as sa

#TODO: remove this from boot script after deployment.
def create_admin():
    app = create_app()

    with app.app_context():
        if not db.session.scalars(sa.select(User)).first():
            admins = app.config.get('ADMINS')
            pwd = app.config.get('ADMIN_PWD')

            if not (pwd and admins):
                return

            u = User(email=admins[0], is_superadmin=True)
            u.set_password(pwd)
            db.session.add(u)
            db.session.commit()
            print("Admin user created.")

        else:
            print("Admin user already exists.")

create_admin()