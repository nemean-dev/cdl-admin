from typing import Optional
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as orm
from app import db, login
from app.utils import simple_lower_ascii, is_multiline

MIN_PASSWORD_LENGTH = 8

@login.user_loader
def load_user(id):
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

    def __repr__(self):
        return '<User {}>'.format(self.email)
    
    def set_password(self, password):
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

class Vendor(db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    name: orm.Mapped[str] = orm.mapped_column(sa.String(256), index=True,
                                             unique=True)
    compare_name: orm.Mapped[str] = orm.mapped_column(sa.String(256), index=True,
                                                      unique=True)
    pueblo: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(128), index=True)
    estado: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(16), index=True)
    pueblos_estados_shopify: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String())
    
    def __repr__(self):
        return '<Vendor {}>'.format(self.name)
    
    def set_name(self, name):
        if is_multiline(name):
            raise ValueError('Multiline strings not allowed as Vendor names.')
        self.name = name
        self.compare_name = simple_lower_ascii(name) #lowered, no accents, and no multiple consecutive whitespace characters
    
    def set_pueblo(self, pueblo):
        if is_multiline(pueblo):
            raise ValueError('Multiline strings not allowed as Vendor names.')
        if not self.name:
            raise ValueError('You must set the vendor name before pueblo or estado.')
        if self.compare_name in ['anonimo', 'x']:
            return
        self.pueblo = pueblo

    def set_estado(self, estado):
        if is_multiline(estado):
            raise ValueError('Multiline strings not allowed as Vendor names.')
        if not self.name:
            raise ValueError('You must set the vendor name before pueblo or estado.')
        if self.compare_name in ['anonimo', 'x']:
            return
        self.estado = estado

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
