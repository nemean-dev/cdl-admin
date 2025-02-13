from typing import Optional
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask import current_app
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as orm
from app import db, login
from app.utils import simple_lower_ascii, is_multiline

MIN_PASSWORD_LENGTH = 8

@login.user_loader
def load_user(id) -> 'User':
    return db.session.get(User, int(id))

class User(UserMixin, db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    email: orm.Mapped[str] = orm.mapped_column(sa.String(256), index=True,
                                             unique=True)
    fname: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(128))
    lname: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(128))
    password_hash: orm.Mapped[str] = orm.mapped_column(sa.String(256))
    last_seen: orm.Mapped[Optional[datetime]] = orm.mapped_column()
    created_at: orm.Mapped[datetime] = orm.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    actions: orm.WriteOnlyMapped['AdminAction'] = orm.relationship(
        back_populates='admin')
    is_superadmin: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, default=False)
    failed_logins: orm.Mapped[int] = orm.mapped_column(sa.Integer, default=0)

    def __repr__(self):
        return '<User {}>'.format(self.email)

    def set_password(self, password: str):
        '''Must be at least MIN_PASSWORD_LENGTH characters long.'''
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
        self.password_hash = generate_password_hash(password+current_app.config.get('PASSWORD_PEPPER'))

    def check_password(self, password):
        return check_password_hash(self.password_hash, password+current_app.config.get('PASSWORD_PEPPER'))
    
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password_uid': self.id, 'exp': (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp()},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token) -> 'User | None':
        try:
            uid = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password_uid']
        except:
            return
        return db.session.get(User, uid)

class AdminAction(db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    timestamp: orm.Mapped[datetime] = orm.mapped_column(
        index= True, 
        default= lambda: datetime.now(timezone.utc))
    action: orm.Mapped[str] = orm.mapped_column(sa.String(128))
    status: orm.Mapped[str] = orm.mapped_column(sa.String(16))
    errors: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(256))
    user_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey(User.id),
                                                 index=True)
    admin: orm.Mapped[User] = orm.relationship(back_populates='actions')
    files: orm.WriteOnlyMapped['File'] = orm.relationship(
        back_populates='admin_action')

    def __repr__(self):
        return '<AdminAction {}>'.format(self.action)
    
class File(db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    path: orm.Mapped[str] = orm.mapped_column(sa.String(256))
    admin_action_id: orm.Mapped[int] = orm.mapped_column(
        sa.ForeignKey(AdminAction.id), index=True)
    admin_action: orm.Mapped[AdminAction] = orm.relationship(back_populates='files')

    def __repr__(self):
        return '<File {}>'.format(self.path)

class State(db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str] = orm.mapped_column(
        sa.String(32), index=True, unique=True)
    code: orm.Mapped[Optional[str]] = orm.mapped_column(
        sa.String(16), index=True, unique=True)
    towns: orm.WriteOnlyMapped['Town'] = orm.relationship(
        back_populates='state')
    
    def __repr__(self):
        return f'<State {self.code if self.code else '-'} {self.name}>'

class Town(db.Model):
    __table_args__ = (sa.UniqueConstraint('name', 'state_id'),)

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(128), index=True)
    state_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey(State.id),
                                                 index=True)
    state: orm.Mapped[State] = orm.relationship(back_populates='towns')
    vendors: orm.WriteOnlyMapped['Vendor'] = orm.relationship(
        back_populates='town')
    
    def __repr__(self):
        return f'<Town {self.id}: {self.name}>'

class Vendor(db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(256), index=True,
                                             unique=True)
    compare_name: orm.Mapped[str] = orm.mapped_column(sa.String(256), index=True,
                                                      unique=True)
    # towns_shopify is comma-separated list of town ids associated with this vendor
    towns_shopify: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String()) 
    total_products: orm.Mapped[int] = orm.mapped_column(sa.Integer(), default=0)
    total_variants: orm.Mapped[int] = orm.mapped_column(sa.Integer(), default=0)
    # town_id is actual intended value. When data is clean, str(town_id) == towns_shopify
    town_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey(Town.id),
                                                 index=True)
    town: orm.Mapped[Optional['Town']] = orm.relationship(back_populates='vendors')   
    shopify_vendors: orm.WriteOnlyMapped['ShopifyVendor'] = orm.relationship(
        back_populates='vendor')
    
    def __repr__(self):
        return '<Vendor {}>'.format(self.name)
    
    def set_name(self, name):
        if is_multiline(name):
            raise ValueError('Multiline strings not allowed as Vendor names.')
        self.name = name
        self.compare_name = simple_lower_ascii(name) #lowered, no accents, and no multiple consecutive whitespace characters

    def get_shopify_towns_ids(self)-> list[int]:
        return list(map(int, self.towns_shopify.split(','))) if self.towns_shopify else []
    
    def add_shopify_town(self, town):
        '''town may be town id integer or Town object'''
        towns_ids = self.get_shopify_towns_ids()
        if isinstance(town, int):
            town = db.session.get(Town, town)
        if not isinstance(town, Town):
            return
        if town.id not in towns_ids:
            towns_ids.append(town.id)
            self.towns_shopify = ','.join(map(str,towns_ids))

class ShopifyVendor(db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(256), index=True,
                                             unique=True)
    vendor: orm.Mapped[Vendor] = orm.relationship(back_populates='shopify_vendors')

    def __repr__(self):
        return f'<Town {self.name}>'

class Metadata(db.Model):
    key: orm.Mapped[str] = orm.mapped_column(sa.String(128), primary_key=True)
    value: orm.Mapped[str] = orm.mapped_column(sa.Text, nullable=False)

    def __repr__(self):
        return f'<Metadata {self.key}: {self.value}>'
    
    @classmethod
    def get_last_product_handle(cls) -> str:
        '''
        Return the value of the key 'products_last_handle'. If the key does not 
        exist, sets it to 'default-handle-0' and returns that.
        '''
        metadata = db.session.get(cls, 'products_last_handle')
        if metadata is None:
            metadata = cls(key='products_last_handle', value='default-handle-0')
            db.session.add(metadata)
            db.session.commit()
        return metadata.value

    @classmethod
    def set_last_product_handle(cls, handle: str) -> None:
        metadata = db.session.get(cls, 'products_last_handle')
        if metadata is None:
            metadata = cls(key='products_last_handle', value=handle)
            db.session.add(metadata)
        else:
            metadata.value = handle
        db.session.commit()
