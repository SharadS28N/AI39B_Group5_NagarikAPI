import secrets
import hashlib
from datetime import datetime
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
    requests = db.relationship('KYCRequest', backref='institution', lazy=True,
                                foreign_keys='KYCRequest.company_id')


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


def seed_demo_data():
    if User.query.count() > 0:
        return

    company = Company(
        name='Bank Nepal',
        registration_number='BN-001'
    )
    db.session.add(company)
    db.session.flush()

    admin = User(
        full_name='Superuser Admin',
        email='admin@nagarikapi.com',
        role='admin'
    )
    admin.set_password('Admin123')
    db.session.add(admin)

    company_admin = User(
        full_name='Company Admin',
        email='hr@banknepal.com',
        role='company_admin',
        company_id=company.id
    )
    company_admin.set_password('CompanyAdmin123')
    db.session.add(company_admin)

    end_user = User(
        full_name='End User',
        email='user@example.com',
        role='user',
        company_id=company.id
    )
    end_user.set_password('User123')
    db.session.add(end_user)

    db.session.commit()
