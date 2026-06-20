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

    # Create end users
    end_user1 = User(
        full_name='Ram Bahadur',
        email='ram@example.com',
        role='user',
        company_id=company1.id
    )
    end_user1.set_password('User123')
    db.session.add(end_user1)
    
    end_user2 = User(
        full_name='Gita Rai',
        email='gita@example.com',
        role='user',
        company_id=company2.id
    )
    end_user2.set_password('User123')
    db.session.add(end_user2)
    
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
    
    # Create demo KYC cases
    # Verified case
    kyc1 = KYCRequest(
        case_ref='KYC-2026-0001',
        user_id=end_user1.id,
        company_id=company1.id,
        verification_type='kyc',
        document_type='national_id',
        full_name='Ram Bahadur',
        date_of_birth='1990-05-15',
        id_number='1234567890123',
        address='Kathmandu, Nepal',
        ocr_confidence=94.5,
        face_match_score=88.2,
        overall_score=91.3,
        status='verified',
        is_flagged=False,
        created_at=datetime.utcnow() - timedelta(hours=2)
    )
    db.session.add(kyc1)
    
    # Pending case
    kyc2 = KYCRequest(
        case_ref='KYC-2026-0002',
        user_id=end_user2.id,
        company_id=company2.id,
        verification_type='kyc',
        document_type='national_id',
        full_name='Gita Rai',
        date_of_birth='1995-11-22',
        id_number='9876543210987',
        address='Pokhara, Nepal',
        ocr_confidence=78.3,
        face_match_score=72.1,
        overall_score=75.2,
        status='pending',
        is_flagged=False,
        created_at=datetime.utcnow() - timedelta(minutes=15)
    )
    db.session.add(kyc2)
    
    # Rejected case
    kyc3 = KYCRequest(
        case_ref='KYC-2026-0003',
        user_id=end_user1.id,
        company_id=company1.id,
        verification_type='kyc',
        document_type='national_id',
        full_name='Unknown',
        date_of_birth='',
        id_number='',
        address='',
        ocr_confidence=12.5,
        face_match_score=5.3,
        overall_score=8.9,
        status='rejected',
        is_flagged=True,
        flag_reason='Document could not be verified',
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    db.session.add(kyc3)
    
    # Student verification case
    kyc4 = KYCRequest(
        case_ref='KYC-2026-0004',
        user_id=end_user2.id,
        company_id=company2.id,
        verification_type='student',
        document_type='national_id',
        full_name='Gita Rai',
        date_of_birth='1995-11-22',
        id_number='9876543210987',
        institution_name='Tribhuvan University',
        student_id='TU-2022-05432',
        program='BSc Computer Science',
        enrollment_year='2022',
        ocr_confidence=91.8,
        face_match_score=85.6,
        overall_score=88.7,
        status='verified',
        is_flagged=False,
        created_at=datetime.utcnow() - timedelta(days=2)
    )
    db.session.add(kyc4)
    
    # Manual review case
    kyc5 = KYCRequest(
        case_ref='KYC-2026-0005',
        user_id=end_user1.id,
        company_id=company1.id,
        verification_type='kyc',
        document_type='national_id',
        full_name='Ram Bahadur',
        date_of_birth='1990-05-15',
        id_number='1234567890123',
        address='Kathmandu, Nepal',
        ocr_confidence=65.4,
        face_match_score=68.9,
        overall_score=67.1,
        status='manual_review',
        is_flagged=True,
        flag_reason='Low confidence score',
        created_at=datetime.utcnow() - timedelta(hours=5)
    )
    db.session.add(kyc5)
    
    # Create audit logs
    log1 = AuditLog(
        case_id=kyc1.id,
        user_id=admin.id,
        action='case.verified',
        detail='Case KYC-2026-0001 verified successfully',
        ip_address='192.168.1.100',
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    db.session.add(log1)
    
    log2 = AuditLog(
        case_id=kyc4.id,
        user_id=company_admin2.id,
        action='case.verified',
        detail='Student verification KYC-2026-0004 verified',
        ip_address='10.0.0.5',
        created_at=datetime.utcnow() - timedelta(days=1, hours=23)
    )
    db.session.add(log2)
    
    log3 = AuditLog(
        case_id=kyc3.id,
        user_id=admin.id,
        action='case.rejected',
        detail='Case KYC-2026-0003 rejected due to invalid document',
        ip_address='192.168.1.101',
        created_at=datetime.utcnow() - timedelta(days=1, hours=12)
    )
    db.session.add(log3)

    db.session.commit()
