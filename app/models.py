from typing import Optional
from datetime import datetime, timezone
import sqlalchemy as sa
import sqlalchemy.orm as orm
from app import db

class User(db.Model):
    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    email: orm.Mapped[str] = orm.mapped_column(sa.String(256), index=True,
                                             unique=True)
    fname: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(128))
    lname: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(128))
    password_hash: orm.Mapped[str] = orm.mapped_column(sa.String(256))
    last_seen: orm.Mapped[Optional[datetime]] = orm.mapped_column(
        default=lambda: datetime.now(timezone.utc))
    actions: orm.WriteOnlyMapped['AdminAction'] = orm.relationship(
        back_populates='admin')

    def __repr__(self):
        return '<User {}>'.format(self.email)
    
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
    