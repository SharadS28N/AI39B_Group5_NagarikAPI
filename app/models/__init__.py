import json
from datetime import datetime

from flask_login import UserMixin

from app import bcrypt
from app.database import execute, fetch_all, fetch_one


def _parse_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


def _parse_json(value):
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


class Company:
    def __init__(self, id=None, name='', registration_number='', api_key=None, created_at=None):
        self.id = id
        self.name = name
        self.registration_number = registration_number
        self.api_key = api_key
        self.created_at = created_at

    @classmethod
    def from_row(cls, row, prefix=''):
        if not row:
            return None
        return cls(
            id=row.get(f'{prefix}id'),
            name=row.get(f'{prefix}name', ''),
            registration_number=row.get(f'{prefix}registration_number', ''),
            api_key=row.get(f'{prefix}api_key'),
            created_at=_parse_datetime(row.get(f'{prefix}created_at')),
        )

    @classmethod
    def get_by_id(cls, company_id):
        row = fetch_one(
            'SELECT id, name, registration_number, api_key, created_at FROM companies WHERE id = %s',
            (company_id,),
        )
        return cls.from_row(row)

    @classmethod
    def count(cls):
        row = fetch_one('SELECT COUNT(*) AS total FROM companies')
        return int(row['total']) if row else 0

    @classmethod
    def create(cls, name, registration_number, api_key=None):
        existing = fetch_one(
            'SELECT id, name, registration_number, api_key, created_at FROM companies WHERE registration_number = %s',
            (registration_number,),
        )
        if existing:
            return cls.from_row(existing)

        company_id = execute(
            'INSERT INTO companies (name, registration_number, api_key) VALUES (%s, %s, %s)',
            (name, registration_number, api_key),
        )
        return cls.get_by_id(company_id)


class User(UserMixin):
    def __init__(
        self,
        id=None,
        email='',
        password_hash='',
        full_name='',
        role='user',
        created_at=None,
        company_id=None,
        company=None,
    ):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.role = role
        self.created_at = created_at
        self.company_id = company_id
        self.company = company

    @classmethod
    def from_row(cls, row, prefix=''):
        if not row:
            return None

        company = None
        if row.get('company_id') is not None and row.get('company_name') is not None:
            company = Company(
                id=row.get('company_id'),
                name=row.get('company_name', ''),
                registration_number=row.get('company_registration_number', ''),
                api_key=row.get('company_api_key'),
                created_at=_parse_datetime(row.get('company_created_at')),
            )

        return cls(
            id=row.get(f'{prefix}id'),
            email=row.get(f'{prefix}email', ''),
            password_hash=row.get(f'{prefix}password_hash', ''),
            full_name=row.get(f'{prefix}full_name', ''),
            role=row.get(f'{prefix}role', 'user') or 'user',
            created_at=_parse_datetime(row.get(f'{prefix}created_at')),
            company_id=row.get(f'{prefix}company_id'),
            company=company,
        )

    @classmethod
    def get_by_id(cls, user_id):
        row = fetch_one(
            '''
            SELECT
                u.id AS user_id,
                u.email AS user_email,
                u.password_hash AS user_password_hash,
                u.full_name AS user_full_name,
                u.role AS user_role,
                u.created_at AS user_created_at,
                u.company_id AS user_company_id,
                c.id AS company_id,
                c.name AS company_name,
                c.registration_number AS company_registration_number,
                c.api_key AS company_api_key,
                c.created_at AS company_created_at
            FROM users u
            LEFT JOIN companies c ON c.id = u.company_id
            WHERE u.id = %s
            ''',
            (user_id,),
        )
        return cls.from_row(row, prefix='user_')

    @classmethod
    def find_by_email(cls, email):
        row = fetch_one(
            '''
            SELECT
                u.id AS user_id,
                u.email AS user_email,
                u.password_hash AS user_password_hash,
                u.full_name AS user_full_name,
                u.role AS user_role,
                u.created_at AS user_created_at,
                u.company_id AS user_company_id,
                c.id AS company_id,
                c.name AS company_name,
                c.registration_number AS company_registration_number,
                c.api_key AS company_api_key,
                c.created_at AS company_created_at
            FROM users u
            LEFT JOIN companies c ON c.id = u.company_id
            WHERE u.email = %s
            ''',
            (email,),
        )
        return cls.from_row(row, prefix='user_')

    @classmethod
    def count(cls):
        row = fetch_one('SELECT COUNT(*) AS total FROM users')
        return int(row['total']) if row else 0

    @classmethod
    def create(cls, full_name, email, password, role='user', company_id=None):
        existing = cls.find_by_email(email)
        if existing:
            return existing

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user_id = execute(
            '''
            INSERT INTO users (email, password_hash, full_name, role, company_id)
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (email, password_hash, full_name, role, company_id),
        )
        return cls.get_by_id(user_id)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def kyc_requests(self):
        return KYCRequest.for_user(self.id)


class KYCRequest:
    def __init__(
        self,
        id=None,
        user_id=None,
        company_id=None,
        document_type='national_id',
        status='pending',
        ocr_data=None,
        verification_date=None,
        created_at=None,
        user=None,
        organization=None,
    ):
        self.id = id
        self.user_id = user_id
        self.company_id = company_id
        self.document_type = document_type
        self.status = status
        self.ocr_data = ocr_data
        self.verification_date = verification_date
        self.created_at = created_at
        self.user = user
        self.organization = organization

    @classmethod
    def from_row(cls, row, prefix=''):
        if not row:
            return None

        user = None
        if row.get('user_id') is not None and row.get('user_email') is not None:
            user = User(
                id=row.get('user_id'),
                email=row.get('user_email', ''),
                password_hash=row.get('user_password_hash', ''),
                full_name=row.get('user_full_name', ''),
                role=row.get('user_role', 'user') or 'user',
                created_at=_parse_datetime(row.get('user_created_at')),
                company_id=row.get('user_company_id'),
            )

        organization = None
        if row.get('company_id') is not None and row.get('company_name') is not None:
            organization = Company(
                id=row.get('company_id'),
                name=row.get('company_name', ''),
                registration_number=row.get('company_registration_number', ''),
                api_key=row.get('company_api_key'),
                created_at=_parse_datetime(row.get('company_created_at')),
            )

        return cls(
            id=row.get(f'{prefix}id'),
            user_id=row.get(f'{prefix}user_id'),
            company_id=row.get(f'{prefix}company_id'),
            document_type=row.get(f'{prefix}document_type', 'national_id'),
            status=row.get(f'{prefix}status', 'pending') or 'pending',
            ocr_data=_parse_json(row.get(f'{prefix}ocr_data')),
            verification_date=_parse_datetime(row.get(f'{prefix}verification_date')),
            created_at=_parse_datetime(row.get(f'{prefix}created_at')),
            user=user,
            organization=organization,
        )

    @classmethod
    def count(cls):
        row = fetch_one('SELECT COUNT(*) AS total FROM kyc_requests')
        return int(row['total']) if row else 0

    @classmethod
    def for_user(cls, user_id):
        rows = fetch_all(
            '''
            SELECT
                kr.id AS request_id,
                kr.user_id AS request_user_id,
                kr.company_id AS request_company_id,
                kr.document_type AS request_document_type,
                kr.status AS request_status,
                kr.ocr_data AS request_ocr_data,
                kr.verification_date AS request_verification_date,
                kr.created_at AS request_created_at,
                u.id AS user_id,
                u.email AS user_email,
                u.password_hash AS user_password_hash,
                u.full_name AS user_full_name,
                u.role AS user_role,
                u.created_at AS user_created_at,
                u.company_id AS user_company_id,
                c.id AS company_id,
                c.name AS company_name,
                c.registration_number AS company_registration_number,
                c.api_key AS company_api_key,
                c.created_at AS company_created_at
            FROM kyc_requests kr
            LEFT JOIN users u ON u.id = kr.user_id
            LEFT JOIN companies c ON c.id = kr.company_id
            WHERE kr.user_id = %s
            ORDER BY kr.created_at DESC
            ''',
            (user_id,),
        )
        return [cls.from_row(row, prefix='request_') for row in rows]

    @classmethod
    def for_company(cls, company_id):
        rows = fetch_all(
            '''
            SELECT
                kr.id AS request_id,
                kr.user_id AS request_user_id,
                kr.company_id AS request_company_id,
                kr.document_type AS request_document_type,
                kr.status AS request_status,
                kr.ocr_data AS request_ocr_data,
                kr.verification_date AS request_verification_date,
                kr.created_at AS request_created_at,
                u.id AS user_id,
                u.email AS user_email,
                u.password_hash AS user_password_hash,
                u.full_name AS user_full_name,
                u.role AS user_role,
                u.created_at AS user_created_at,
                u.company_id AS user_company_id,
                c.id AS company_id,
                c.name AS company_name,
                c.registration_number AS company_registration_number,
                c.api_key AS company_api_key,
                c.created_at AS company_created_at
            FROM kyc_requests kr
            LEFT JOIN users u ON u.id = kr.user_id
            LEFT JOIN companies c ON c.id = kr.company_id
            WHERE kr.company_id = %s
            ORDER BY kr.created_at DESC
            ''',
            (company_id,),
        )
        return [cls.from_row(row, prefix='request_') for row in rows]

    @classmethod
    def create(cls, user_id, document_type, company_id=None, status='pending', ocr_data=None, verification_date=None):
        request_id = execute(
            '''
            INSERT INTO kyc_requests (user_id, company_id, document_type, status, ocr_data, verification_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (user_id, company_id, document_type, status, json.dumps(ocr_data) if isinstance(ocr_data, (dict, list)) else ocr_data, verification_date),
        )
        row = fetch_one(
            '''
            SELECT
                kr.id AS request_id,
                kr.user_id AS request_user_id,
                kr.company_id AS request_company_id,
                kr.document_type AS request_document_type,
                kr.status AS request_status,
                kr.ocr_data AS request_ocr_data,
                kr.verification_date AS request_verification_date,
                kr.created_at AS request_created_at,
                u.id AS user_id,
                u.email AS user_email,
                u.password_hash AS user_password_hash,
                u.full_name AS user_full_name,
                u.role AS user_role,
                u.created_at AS user_created_at,
                u.company_id AS user_company_id,
                c.id AS company_id,
                c.name AS company_name,
                c.registration_number AS company_registration_number,
                c.api_key AS company_api_key,
                c.created_at AS company_created_at
            FROM kyc_requests kr
            LEFT JOIN users u ON u.id = kr.user_id
            LEFT JOIN companies c ON c.id = kr.company_id
            WHERE kr.id = %s
            ''',
            (request_id,),
        )
        return cls.from_row(row, prefix='request_')


def seed_demo_data():
    if User.count() > 0:
        return

    company = Company.create(
        name='Bank Nepal',
        registration_number='BN-001',
        api_key='demo-bank-nepal',
    )

    _admin = User.create(
        full_name='Superuser Admin',
        email='admin@nagarikapi.com',
        password='Admin123',
        role='admin',
    )

    company_admin = User.create(
        full_name='Company Admin',
        email='hr@banknepal.com',
        password='CompanyAdmin123',
        role='company_admin',
        company_id=company.id,
    )

    end_user = User.create(
        full_name='End User',
        email='user@example.com',
        password='User123',
        role='user',
        company_id=company.id,
    )

    KYCRequest.create(
        user_id=end_user.id,
        company_id=company.id,
        document_type='national_id',
        status='approved',
    )

