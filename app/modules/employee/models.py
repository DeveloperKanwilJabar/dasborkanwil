import uuid
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.extensions import db

class Employee(db.Model):
    """Masterdata Pegawai"""
    __tablename__ = 'employees'

    # Kolom
    id = db.Column('id', db.Integer(), primary_key=True)
    uuid = db.Column('uuid', db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    nip = db.Column('nip', db.String(18), unique=True, nullable=False, index=True)
    name = db.Column('name', db.String(255), nullable=False)
    email = db.Column('email', db.String(120), nullable=True, unique=True)
    details = db.Column('details', JSONB, nullable=True)  # Kolom JSON untuk atribut dinamis
    active = db.Column('is_active', db.Boolean(), server_default='1')
    created_at = db.Column('created_at', db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column('updated_at', db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    deleted_at = db.Column('deleted_at', db.DateTime(timezone=True), nullable=True)

    # Relasi ke model User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)
    user = relationship('User', back_populates='employee', lazy='joined')  # Eager loading

    def __repr__(self):
        return f"<Employee {self.nip} - {self.name}>"
