from typing import Optional
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as orm
from app import db, login

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
    last_seen: orm.Mapped[Optional[datetime]] = orm.mapped_column(
        default=lambda: datetime.now(timezone.utc))#TODO delete default and instead add a 'created' field.
    actions: orm.WriteOnlyMapped['AdminAction'] = orm.relationship(
        back_populates='admin')
    is_superadmin: orm.Mapped[bool] = orm.mapped_column(sa.Boolean, default=False)

    def __repr__(self):
        return '<User {}>'.format(self.email)
    
    def set_password(self, password):
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
    user_id: orm.Mapped[int] = orm.mapped_column(sa.ForeignKey(User.id),
                                                 index=True)
    admin: orm.Mapped[User] = orm.relationship(back_populates='actions')

    def __repr__(self):
        return '<AdminAction {}>'.format(self.action)
    