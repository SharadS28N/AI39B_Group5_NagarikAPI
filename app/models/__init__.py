from datetime import datetime
from app import db, bcrypt
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user') # 'admin', 'user', 'company_admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    kyc_requests = db.relationship('KYCRequest', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employees = db.relationship('User', backref='company', lazy=True)
    kyc_verifications = db.relationship('KYCRequest', backref='organization', lazy=True)

class KYCRequest(db.Model):
    __tablename__ = 'kyc_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    document_type = db.Column(db.String(20), nullable=False) # 'national_id', 'passport'
    status = db.Column(db.String(20), default='pending') # 'pending', 'approved', 'rejected'
    ocr_data = db.Column(db.JSON, nullable=True)
    verification_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
