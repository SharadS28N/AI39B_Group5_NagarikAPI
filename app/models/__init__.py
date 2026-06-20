import secrets
import hashlib
from datetime import datetime, timedelta
from app.extensions import db, bcrypt
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user')
    # roles: 'admin', 'company_admin', 'user'
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kyc_requests = db.relationship('KYCRequest', backref='submitter', lazy=True,
                                   foreign_keys='KYCRequest.user_id')
    company = db.relationship('Company', backref='users', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(30), default='bank')
    # types: bank, fintech, insurance, university, mfi
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    webhook_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    api_keys = db.relationship('APIKey', backref='company', lazy=True)
    # Use consistent relationship names, keep institution as an alias
    kyc_requests = db.relationship('KYCRequest', back_populates='company', lazy=True,
                                   foreign_keys='KYCRequest.company_id')
    # Alias for backward compatibility
    @property
    def requests(self):
        return self.kyc_requests


class APIKey(db.Model):
    __tablename__ = 'api_keys'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False,
                   default=lambda: secrets.token_hex(32))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    name = db.Column(db.String(100), default='Default Key')
    is_active = db.Column(db.Boolean, default=True)
    requests_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def mask(self):
        return f"{self.key[:8]}...{self.key[-4:]}"


class KYCRequest(db.Model):
    __tablename__ = 'kyc_requests'
    id = db.Column(db.Integer, primary_key=True)
    case_ref = db.Column(db.String(20), unique=True, nullable=False,
                        default=lambda: f"KYC-{secrets.token_hex(4).upper()}")
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    # Use back_populates for relationships
    company = db.relationship('Company', back_populates='kyc_requests', foreign_keys=[company_id])
    # Alias for backward compatibility
    @property
    def institution(self):
        return self.company

    # Verification type
    verification_type = db.Column(db.String(20), default='kyc')
    # types: kyc, student

    # Document info
    document_type = db.Column(db.String(20), default='national_id')
    id_image_path = db.Column(db.String(500), nullable=True)
    selfie_path = db.Column(db.String(500), nullable=True)

    # OCR extracted data
    full_name = db.Column(db.String(200), nullable=True)
    date_of_birth = db.Column(db.String(30), nullable=True)
    id_number = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    citizenship_no = db.Column(db.String(50), nullable=True)
    issue_date = db.Column(db.String(30), nullable=True)
    issue_district = db.Column(db.String(100), nullable=True)

    # Student verification extra fields
    institution_name = db.Column(db.String(200), nullable=True)
    student_id = db.Column(db.String(50), nullable=True)
    enrollment_year = db.Column(db.String(10), nullable=True)
    program = db.Column(db.String(200), nullable=True)

    # Scores
    ocr_confidence = db.Column(db.Float, default=0.0)
    face_match_score = db.Column(db.Float, default=0.0)
    overall_score = db.Column(db.Float, default=0.0)

    # Status
    status = db.Column(db.String(20), default='pending')
    # pending | processing | verified | rejected | manual_review

    is_flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.Text, nullable=True)

    # Raw OCR data
    raw_ocr_data = db.Column(db.JSON, nullable=True)

    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow)

    audit_logs = db.relationship('AuditLog', backref='case', lazy=True)

    def to_dict(self):
        return {
            'case_ref': self.case_ref,
            'status': self.status,
            'verification_type': self.verification_type,
            'full_name': self.full_name,
            'date_of_birth': self.date_of_birth,
            'id_number': self.id_number,
            'address': self.address,
            'citizenship_no': self.citizenship_no,
            'ocr_confidence': round(self.ocr_confidence or 0, 3),
            'face_match_score': round(self.face_match_score or 0, 3),
            'overall_score': round(self.overall_score or 0, 3),
            'is_flagged': self.is_flagged,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('kyc_requests.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentRecord(db.Model):
    __tablename__ = 'student_records'
    id = db.Column(db.Integer, primary_key=True)
    kyc_request_id = db.Column(db.Integer, db.ForeignKey('kyc_requests.id'))
    institution_name = db.Column(db.String(200))
    student_id = db.Column(db.String(50))
    program = db.Column(db.String(200))
    enrollment_year = db.Column(db.String(10))
    expected_grad = db.Column(db.String(10))
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GovernmentCitizenRecord(db.Model):
    """Fake government database citizen record"""
    __tablename__ = 'government_citizen_records'
    id = db.Column(db.Integer, primary_key=True)
    id_number = db.Column(db.String(50), unique=True, nullable=False)  # National ID number
    citizenship_no = db.Column(db.String(50), unique=True, nullable=True)
    full_name = db.Column(db.String(200), nullable=False)
    date_of_birth = db.Column(db.String(30), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    address = db.Column(db.Text, nullable=True)
    issue_date = db.Column(db.String(30), nullable=True)
    issue_district = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DataAccessPermission(db.Model):
    """Tracks which companies have access to which citizen data"""
    __tablename__ = 'data_access_permissions'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    citizen_id = db.Column(db.Integer, db.ForeignKey('government_citizen_records.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Which user's data is shared
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who granted access
    access_type = db.Column(db.String(50), default='full')  # 'full', 'basic', 'read-only'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    company = db.relationship('Company', foreign_keys=[company_id])
    citizen = db.relationship('GovernmentCitizenRecord', foreign_keys=[citizen_id])


class DataAccessLog(db.Model):
    """Audit log for data access events"""
    __tablename__ = 'data_access_logs'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    api_key_id = db.Column(db.Integer, db.ForeignKey('api_keys.id'), nullable=False)
    citizen_id = db.Column(db.Integer, db.ForeignKey('government_citizen_records.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who's data was accessed
    accessed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who accessed it (if from portal)
    access_type = db.Column(db.String(50), nullable=False)  # 'read', 'write', 'verify', etc.
    data_accessed = db.Column(db.JSON, nullable=True)  # What data was accessed
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company', foreign_keys=[company_id])
    api_key = db.relationship('APIKey', foreign_keys=[api_key_id])
    citizen = db.relationship('GovernmentCitizenRecord', foreign_keys=[citizen_id])


def seed_demo_data():
    if User.query.count() > 0:
        return

    # Create companies
    company1 = Company(
        name='Bank Nepal',
        registration_number='BN-001'
    )
    db.session.add(company1)
    
    company2 = Company(
        name='Nepal Fintech',
        registration_number='NF-002'
    )
    db.session.add(company2)
    
    db.session.flush()

    # Create admin user
    admin = User(
        full_name='Superuser Admin',
        email='admin@nagarikapi.com',
        role='admin'
    )
    admin.set_password('Admin123')
    db.session.add(admin)

    # Create company admins
    company_admin1 = User(
        full_name='Rajesh Kumar',
        email='hr@banknepal.com',
        role='company_admin',
        company_id=company1.id
    )
    company_admin1.set_password('CompanyAdmin123')
    db.session.add(company_admin1)
    
    company_admin2 = User(
        full_name='Sita Shrestha',
        email='admin@nepalfintech.com',
        role='company_admin',
        company_id=company2.id
    )
    company_admin2.set_password('CompanyAdmin123')
    db.session.add(company_admin2)

    # Create Sharad's user account
    sharad_user = User(
        full_name='Sharad Bhandari',
        email='sharad.bhandari222@gmail.com',
        role='user',
        company_id=company1.id
    )
    sharad_user.set_password('nayamill0')
    db.session.add(sharad_user)
    
    # Create demo API keys
    api_key1 = APIKey(
        company_id=company1.id,
        name='Production Key',
        is_active=True
    )
    db.session.add(api_key1)
    
    api_key2 = APIKey(
        company_id=company2.id,
        name='Development Key',
        is_active=True
    )
    db.session.add(api_key2)
    
    db.session.flush()
    
    # Create ONLY Sharad's government citizen record
    sharad_citizen = GovernmentCitizenRecord(
        id_number='026-207-7515',
        full_name='Sharad Bhandari',
        date_of_birth='2006-11-03',
        gender='Male',
        address='',
        issue_date='2024-06-11',
        issue_district='',
        is_active=True
    )
    db.session.add(sharad_citizen)
    
    db.session.flush()

    db.session.commit()
