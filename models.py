from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer') # admin, engineer, customer

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Null for guest
    engineer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Guest details
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(100), nullable=True)
    guest_phone = db.Column(db.String(20), nullable=True)
    
    service_category = db.Column(db.String(100), nullable=True)
    issue = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    preferred_date = db.Column(db.Date, nullable=False)
    location_lat = db.Column(db.Float, nullable=False)
    location_lng = db.Column(db.Float, nullable=False)
    physical_address = db.Column(db.String(500))
    status = db.Column(db.String(20), default='Pending') # Pending, Assigned, In Progress, Done, Completed
    image_path = db.Column(db.String(255), nullable=True)
    qr_code_data = db.Column(db.String(100), unique=True, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id], backref='customer_appointments')
    engineer = db.relationship('User', foreign_keys=[engineer_id], backref='engineer_appointments')

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    service_fee = db.Column(db.Float, default=0.0)
    transport_fee = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Unpaid') # Unpaid, Paid

    appointment = db.relationship('Appointment', backref=db.backref('invoices', lazy=True))

class Completion(db.Model):
    __tablename__ = 'completions'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    engineer_confirm = db.Column(db.Boolean, default=False)
    customer_confirm = db.Column(db.Boolean, default=False)
    engineer_signature = db.Column(db.Text, nullable=True) # Base64 signature
    customer_signature = db.Column(db.Text, nullable=True) # Base64 signature
    
    appointment = db.relationship('Appointment', backref=db.backref('completion', uselist=False))

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1-5
    feedback = db.Column(db.Text, nullable=True)
    
    appointment = db.relationship('Appointment', backref=db.backref('rating', uselist=False))

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Null for general/system alerts
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    role_target = db.Column(db.String(20), nullable=True) # Target specific role (admin/engineer)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
