"""
KYC (Know Your Customer) data model and operations.
Handles user verification, document management, and compliance tracking.
"""

from datetime import datetime
from enum import Enum
from flask import current_app

from app.database import get_connection
import json


def _parse_datetime(value):
    if value is None or hasattr(value, 'isoformat'):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


class KYCStatus(Enum):
    """KYC verification status states"""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DocumentType(Enum):
    """Supported KYC document types"""
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    PROOF_OF_ADDRESS = "proof_of_address"
    BANK_STATEMENT = "bank_statement"


class KYC:
    """KYC user verification model"""

    @staticmethod
    def _using_mysql():
        return bool(current_app.config.get('MYSQL_HOST'))

    @staticmethod
    def _now_sql():
        return 'NOW()' if KYC._using_mysql() else "datetime('now')"
    
    @staticmethod
    def create_table():
        """Create KYC tables if they don't exist"""
        with get_connection() as conn:
            cursor = conn.cursor()

            if KYC._using_mysql():
                kyc_verifications_sql = """
                CREATE TABLE IF NOT EXISTS kyc_verifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    status VARCHAR(50) NOT NULL DEFAULT 'not_started',
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    phone VARCHAR(20),
                    date_of_birth DATE,
                    nationality VARCHAR(100),
                    address_line1 VARCHAR(255),
                    address_line2 VARCHAR(255),
                    city VARCHAR(100),
                    state VARCHAR(100),
                    postal_code VARCHAR(20),
                    country VARCHAR(100),
                    verification_date DATETIME,
                    rejection_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_status (status),
                    INDEX idx_user_id (user_id)
                )
                """
                kyc_documents_sql = """
                CREATE TABLE IF NOT EXISTS kyc_documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    kyc_id INT NOT NULL,
                    document_type VARCHAR(50) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_size INT,
                    mime_type VARCHAR(100),
                    verification_status VARCHAR(50) DEFAULT 'pending',
                    verified_at DATETIME,
                    expiry_date DATE,
                    document_number VARCHAR(100),
                    issuing_country VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (kyc_id) REFERENCES kyc_verifications(id) ON DELETE CASCADE,
                    INDEX idx_kyc_id (kyc_id),
                    INDEX idx_document_type (document_type)
                )
                """
                kyc_audit_sql = """
                CREATE TABLE IF NOT EXISTS kyc_audit_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    kyc_id INT NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    old_status VARCHAR(50),
                    new_status VARCHAR(50),
                    changed_by INT,
                    change_reason TEXT,
                    ip_address VARCHAR(45),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (kyc_id) REFERENCES kyc_verifications(id) ON DELETE CASCADE,
                    INDEX idx_kyc_id (kyc_id),
                    INDEX idx_action (action)
                )
                """
            else:
                kyc_verifications_sql = """
                CREATE TABLE IF NOT EXISTS kyc_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'not_started',
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT,
                    date_of_birth TEXT,
                    nationality TEXT,
                    address_line1 TEXT,
                    address_line2 TEXT,
                    city TEXT,
                    state TEXT,
                    postal_code TEXT,
                    country TEXT,
                    verification_date TEXT,
                    rejection_reason TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    expires_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
                kyc_documents_sql = """
                CREATE TABLE IF NOT EXISTS kyc_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kyc_id INTEGER NOT NULL,
                    document_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    mime_type TEXT,
                    verification_status TEXT DEFAULT 'pending',
                    verified_at TEXT,
                    expiry_date TEXT,
                    document_number TEXT,
                    issuing_country TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (kyc_id) REFERENCES kyc_verifications(id) ON DELETE CASCADE
                )
                """
                kyc_audit_sql = """
                CREATE TABLE IF NOT EXISTS kyc_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kyc_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT,
                    changed_by INTEGER,
                    change_reason TEXT,
                    ip_address TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (kyc_id) REFERENCES kyc_verifications(id) ON DELETE CASCADE
                )
                """
            
            cursor.execute(kyc_verifications_sql)
            cursor.execute(kyc_documents_sql)
            cursor.execute(kyc_audit_sql)
            
            return True
    
    @staticmethod
    def submit_kyc(user_id: int, data: dict) -> dict:
        """
        Submit or update KYC information for a user
        
        Args:
            user_id: User ID
            data: Dictionary containing KYC fields
                - first_name, last_name, email, phone
                - date_of_birth, nationality, country
                - address_line1, address_line2, city, state, postal_code
        
        Returns:
            KYC record dict with status and ID
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if KYC already exists
            cursor.execute("SELECT id, status FROM kyc_verifications WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                if isinstance(existing, dict):
                    kyc_id = existing.get('id')
                    current_status = existing.get('status')
                else:
                    kyc_id, current_status = existing
                # Update existing KYC
                cursor.execute("""
                        UPDATE kyc_verifications 
                        SET first_name = %s, last_name = %s, email = %s, phone = %s,
                            date_of_birth = %s, nationality = %s, country = %s,
                            address_line1 = %s, address_line2 = %s, city = %s,
                            state = %s, postal_code = %s, status = 'pending', updated_at = %s
                        WHERE user_id = %s
                    """, (
                    data.get('first_name'),
                    data.get('last_name'),
                    data.get('email'),
                    data.get('phone'),
                    data.get('date_of_birth'),
                    data.get('nationality'),
                    data.get('country'),
                    data.get('address_line1'),
                    data.get('address_line2'),
                    data.get('city'),
                    data.get('state'),
                    data.get('postal_code'),
                    datetime.utcnow().isoformat(sep=' '),
                    user_id
                ))
                
                # Log the update
                if current_status != 'pending':
                    cursor.execute("""
                        INSERT INTO kyc_audit_log (kyc_id, action, old_status, new_status)
                        VALUES (%s, 'status_change', %s, 'pending')
                    """, (kyc_id, current_status))
            else:
                # Create new KYC
                cursor.execute("""
                    INSERT INTO kyc_verifications 
                    (user_id, first_name, last_name, email, phone, date_of_birth,
                     nationality, country, address_line1, address_line2, city, state, postal_code, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """, (
                    user_id,
                    data.get('first_name'),
                    data.get('last_name'),
                    data.get('email'),
                    data.get('phone'),
                    data.get('date_of_birth'),
                    data.get('nationality'),
                    data.get('country'),
                    data.get('address_line1'),
                    data.get('address_line2'),
                    data.get('city'),
                    data.get('state'),
                    data.get('postal_code')
                ))
                kyc_id = cursor.lastrowid
                
                # Log the creation
                cursor.execute("""
                    INSERT INTO kyc_audit_log (kyc_id, action, new_status)
                    VALUES (%s, 'created', 'pending')
                """, (kyc_id,))
        
        return {
            'kyc_id': kyc_id,
            'user_id': user_id,
            'status': 'pending',
            'message': 'KYC information submitted for verification'
        }
    
    @staticmethod
    def get_kyc_status(user_id: int) -> dict:
        """Get KYC status and details for a user"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, status, first_name, last_name, email, 
                       verification_date, rejection_reason, created_at, expires_at
                FROM kyc_verifications
                WHERE user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return {'status': 'not_started', 'message': 'No KYC record found'}
            
            if isinstance(result, dict):
                kyc_id = result.get('id')
                uid = result.get('user_id')
                status = result.get('status')
                first_name = result.get('first_name')
                last_name = result.get('last_name')
                email = result.get('email')
                ver_date = result.get('verification_date')
                rej_reason = result.get('rejection_reason')
                created = result.get('created_at')
                expires = result.get('expires_at')
            else:
                kyc_id, uid, status, first_name, last_name, email, ver_date, rej_reason, created, expires = result
            parsed_verification_date = _parse_datetime(ver_date)
            parsed_created_at = _parse_datetime(created)
            parsed_expires_at = _parse_datetime(expires)
            
            # Get documents
            cursor.execute("""
                SELECT id, document_type, verification_status, expiry_date
                FROM kyc_documents
                WHERE kyc_id = %s
            """, (kyc_id,))
            
            documents = []
            for document in cursor.fetchall():
                if isinstance(document, dict):
                    parsed_expiry = _parse_datetime(document.get('expiry_date'))
                    documents.append({
                        'id': document.get('id'),
                        'type': document.get('document_type'),
                        'status': document.get('verification_status'),
                        'expiry_date': parsed_expiry.isoformat() if parsed_expiry else None
                    })
                else:
                    doc_id, doc_type, doc_status, expiry = document
                    parsed_expiry = _parse_datetime(expiry)
                    documents.append({
                        'id': doc_id,
                        'type': doc_type,
                        'status': doc_status,
                        'expiry_date': parsed_expiry.isoformat() if parsed_expiry else None
                    })
            
            return {
                'kyc_id': kyc_id,
                'user_id': uid,
                'status': status,
                'name': f"{first_name} {last_name}",
                'email': email,
                'verification_date': parsed_verification_date.isoformat() if parsed_verification_date else None,
                'rejection_reason': rej_reason,
                'created_at': parsed_created_at.isoformat() if parsed_created_at else None,
                'expires_at': parsed_expires_at.isoformat() if parsed_expires_at else None,
                'documents': documents
            }
    
    @staticmethod
    def upload_document(kyc_id: int, document_type: str, file_path: str, 
                       file_name: str, file_size: int, mime_type: str,
                       document_number: str = None, issuing_country: str = None) -> dict:
        """Upload a KYC document"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO kyc_documents 
                (kyc_id, document_type, file_path, file_name, file_size, mime_type,
                 document_number, issuing_country, verification_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (
                kyc_id, document_type, file_path, file_name, 
                file_size, mime_type, document_number, issuing_country
            ))
            
            doc_id = cursor.lastrowid
            
            # Log the upload
            cursor.execute("""
                INSERT INTO kyc_audit_log (kyc_id, action)
                VALUES (%s, 'document_uploaded')
            """, (kyc_id,))
            
            return {
                'document_id': doc_id,
                'kyc_id': kyc_id,
                'status': 'pending',
                'message': 'Document uploaded successfully'
            }
    
    @staticmethod
    def approve_kyc(kyc_id: int, verified_by: int = None) -> dict:
        """Approve KYC verification"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE kyc_verifications
                SET status = 'approved', verification_date = %s, updated_at = %s
                WHERE id = %s
            """, (datetime.utcnow().isoformat(sep=' '), datetime.utcnow().isoformat(sep=' '), kyc_id))
            
            cursor.execute("""
                INSERT INTO kyc_audit_log (kyc_id, action, old_status, new_status, changed_by)
                VALUES (%s, 'approved', 'pending', 'approved', %s)
            """, (kyc_id, verified_by))
            
            return {'message': 'KYC approved', 'kyc_id': kyc_id, 'status': 'approved'}
    
    @staticmethod
    def reject_kyc(kyc_id: int, reason: str, rejected_by: int = None) -> dict:
        """Reject KYC verification"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE kyc_verifications
                SET status = 'rejected', rejection_reason = %s, updated_at = %s
                WHERE id = %s
            """, (reason, datetime.utcnow().isoformat(sep=' '), kyc_id))
            
            cursor.execute("""
                INSERT INTO kyc_audit_log (kyc_id, action, old_status, new_status, changed_by, change_reason)
                VALUES (%s, 'rejected', 'pending', 'rejected', %s, %s)
            """, (kyc_id, rejected_by, reason))
            
            return {'message': 'KYC rejected', 'kyc_id': kyc_id, 'status': 'rejected'}
