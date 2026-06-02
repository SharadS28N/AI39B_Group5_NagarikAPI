"""
KYC and Token API Routes
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from app.models.kyc import KYC
from app.models.token import TokenManager
from app.models.api_key import APIKeyManager
from datetime import datetime

api = Blueprint('api', __name__, url_prefix='/api')


def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        payload = TokenManager.verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Store in request context for use in handler
        request.user_id = payload.get('user_id')
        request.token_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated


def api_key_required(f):
    """Require a valid X-API-Key header for company integrations."""
    @wraps(f)
    def decorated(*args, **kwargs):
        raw_key = request.headers.get('X-API-Key')
        if not raw_key:
            return jsonify({'error': 'X-API-Key header is missing'}), 401

        api_key = APIKeyManager.validate_key(raw_key)
        if not api_key:
            return jsonify({'error': 'Invalid or expired API key'}), 401

        request.api_key = api_key
        return f(*args, **kwargs)

    return decorated


# ============================================================================
# TOKEN GENERATION ENDPOINTS
# ============================================================================

@api.route('/token/generate', methods=['POST'])
def generate_token():
    """
    Generate new JWT token pair for user
    
    Request body:
    {
        "user_id": 123,
        "kyc_status": "approved" (optional)
    }
    
    Returns:
    {
        "access_token": "eyJ0...",
        "refresh_token": "eyJ0...",
        "token_type": "Bearer",
        "expires_in": 1800
    }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        kyc_status = data.get('kyc_status')
        extra_claims = data.get('claims') or {}
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        tokens = TokenManager.generate_token_pair(user_id, kyc_status, extra_claims)
        access_jti = TokenManager.get_token_jti(tokens['access_token'])
        
        # Log token generation
        TokenManager.log_token_usage(
            user_id, 
            access_jti or tokens['access_token'],
            'token_issued',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify(tokens), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/token/refresh', methods=['POST'])
def refresh_token():
    """
    Generate new access token from refresh token
    
    Request body:
    {
        "refresh_token": "eyJ0..."
    }
    
    Returns:
    {
        "access_token": "eyJ0...",
        "token_type": "Bearer",
        "expires_in": 1800
    }
    """
    try:
        data = request.get_json() or {}
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'refresh_token is required'}), 400
        
        tokens = TokenManager.refresh_access_token(refresh_token)
        if not tokens:
            return jsonify({'error': 'Invalid refresh token'}), 401
        return jsonify(tokens), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/token/verify', methods=['POST'])
def verify_token():
    """
    Verify if a token is valid
    
    Request body:
    {
        "token": "eyJ0..."
    }
    
    Returns:
    {
        "valid": true,
        "user_id": 123,
        "expired_at": "2026-05-26T17:30:00Z"
    }
    """
    try:
        data = request.get_json() or {}
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'token is required'}), 400
        
        payload = TokenManager.verify_token(token)
        if not payload:
            return jsonify({'valid': False}), 200
        
        return jsonify({
            'valid': True,
            'user_id': payload.get('user_id'),
            'token_type': payload.get('token_type'),
            'expires_at': datetime.fromtimestamp(payload.get('exp')).isoformat() + 'Z'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API KEY ENDPOINTS (for company-type clients)
# ============================================================================


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Minimal admin check: token payload must have is_admin=True
        payload = getattr(request, 'token_payload', {})
        if not payload or not payload.get('is_admin'):
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)

    return decorated


@api.route('/apikey/create', methods=['POST'])
@token_required
@admin_required
def create_api_key():
    """Create an API key for a given company type (admin only)

    Request body:
    {
        "name": "Integration for X",
        "company_type": "bank",
        "expires_in_days": 365,
        "scopes": "kyc:read,kyc:write"
    }

    Returns raw key only once.
    """
    try:
        data = request.get_json() or {}
        name = data.get('name', 'unnamed')
        company_type = data.get('company_type')
        expires_in_days = data.get('expires_in_days')
        scopes = data.get('scopes')

        if not company_type:
            return jsonify({'error': 'company_type is required'}), 400

        created_by = request.user_id
        APIKeyManager.create_table()
        result = APIKeyManager.create_api_key(name, company_type, created_by, expires_in_days, scopes)

        # Return raw key to caller (show only once)
        return jsonify({'id': result['id'], 'name': result['name'], 'company_type': result['company_type'], 'raw_key': result['raw_key'], 'expires_at': result['expires_at']}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/apikey/list', methods=['GET'])
@token_required
@admin_required
def list_api_keys():
    company_type = request.args.get('company_type')
    include_revoked = request.args.get('include_revoked', 'false').lower() == 'true'
    keys = APIKeyManager.list_keys(company_type, include_revoked)
    return jsonify({'keys': keys}), 200


@api.route('/apikey/revoke', methods=['POST'])
@token_required
@admin_required
def revoke_api_key():
    data = request.get_json() or {}
    api_id = data.get('id')
    reason = data.get('reason')
    if not api_id:
        return jsonify({'error': 'id is required'}), 400
    APIKeyManager.revoke_key(api_id, reason)
    return jsonify({'message': 'revoked', 'id': api_id}), 200


@api.route('/apikey/validate', methods=['GET'])
@api_key_required
def validate_api_key():
    return jsonify({'valid': True, 'api_key': request.api_key}), 200


@api.route('/token/logout', methods=['POST'])
@token_required
def logout():
    """
    Logout user and revoke token
    
    Headers:
    Authorization: Bearer {access_token}
    
    Returns:
    {
        "message": "Successfully logged out"
    }
    """
    try:
        user_id = request.user_id
        token_jti = request.token_payload.get('jti')
        
        TokenManager.revoke_token(token_jti, user_id, "logout")
        
        return jsonify({'message': 'Successfully logged out'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# KYC ENDPOINTS
# ============================================================================

@api.route('/kyc/submit', methods=['POST'])
@token_required
def submit_kyc():
    """
    Submit or update KYC information
    
    Headers:
    Authorization: Bearer {access_token}
    
    Request body:
    {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "date_of_birth": "1990-01-01",
        "nationality": "US",
        "country": "United States",
        "address_line1": "123 Main St",
        "address_line2": "Apt 4B",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001"
    }
    
    Returns:
    {
        "kyc_id": 1,
        "status": "pending",
        "message": "KYC information submitted for verification"
    }
    """
    try:
        user_id = request.user_id
        data = request.get_json()
        
        result = KYC.submit_kyc(user_id, data)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/kyc/status', methods=['GET'])
@token_required
def get_kyc_status():
    """
    Get KYC verification status for authenticated user
    
    Headers:
    Authorization: Bearer {access_token}
    
    Returns:
    {
        "kyc_id": 1,
        "status": "pending|approved|rejected|not_started",
        "name": "John Doe",
        "email": "john@example.com",
        "created_at": "2026-05-26T10:00:00Z",
        "verification_date": "2026-05-26T11:00:00Z",
        "documents": [
            {
                "id": 1,
                "type": "national_id",
                "status": "verified",
                "expiry_date": "2030-01-01"
            }
        ]
    }
    """
    try:
        user_id = request.user_id
        result = KYC.get_kyc_status(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/kyc/upload-document', methods=['POST'])
@token_required
def upload_kyc_document():
    """
    Upload a KYC document
    
    Headers:
    Authorization: Bearer {access_token}
    Content-Type: multipart/form-data
    
    Form parameters:
    - document_type: "national_id|passport|drivers_license|proof_of_address|bank_statement"
    - document_number: (optional) ID/passport number
    - issuing_country: (optional) Country that issued the document
    - file: (required) The document file
    
    Returns:
    {
        "document_id": 1,
        "kyc_id": 1,
        "status": "pending",
        "message": "Document uploaded successfully"
    }
    """
    try:
        user_id = request.user_id
        
        # Get KYC record for user
        status = KYC.get_kyc_status(user_id)
        if status.get('status') == 'not_started':
            return jsonify({'error': 'Please submit KYC information first'}), 400
        
        kyc_id = status.get('kyc_id')
        document_type = request.form.get('document_type')
        document_number = request.form.get('document_number')
        issuing_country = request.form.get('issuing_country')
        
        if not document_type:
            return jsonify({'error': 'document_type is required'}), 400
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # In production, save file to secure storage (S3, etc.)
        # For now, we'll just store metadata
        file_path = f"uploads/kyc/{user_id}/{document_type}/{file.filename}"
        file_size = len(file.read())
        file.seek(0)
        
        result = KYC.upload_document(
            kyc_id,
            document_type,
            file_path,
            file.filename,
            file_size,
            file.content_type,
            document_number,
            issuing_country
        )
        
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/kyc/<int:kyc_id>/approve', methods=['POST'])
@token_required
def approve_kyc(kyc_id):
    """
    Approve KYC verification (admin only)
    
    Headers:
    Authorization: Bearer {admin_access_token}
    
    Returns:
    {
        "message": "KYC approved",
        "kyc_id": 1,
        "status": "approved"
    }
    """
    try:
        user_id = request.user_id
        # In production, verify user has admin role
        
        result = KYC.approve_kyc(kyc_id, verified_by=user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/kyc/<int:kyc_id>/reject', methods=['POST'])
@token_required
def reject_kyc(kyc_id):
    """
    Reject KYC verification (admin only)
    
    Headers:
    Authorization: Bearer {admin_access_token}
    
    Request body:
    {
        "reason": "Invalid document"
    }
    
    Returns:
    {
        "message": "KYC rejected",
        "kyc_id": 1,
        "status": "rejected"
    }
    """
    try:
        user_id = request.user_id
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        # In production, verify user has admin role
        
        result = KYC.reject_kyc(kyc_id, reason, rejected_by=user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/kyc/audit-log', methods=['GET'])
@token_required
def get_kyc_audit_log():
    """
    Get KYC audit log for authenticated user (admin only)
    
    Headers:
    Authorization: Bearer {admin_access_token}
    
    Query parameters:
    - user_id: (optional) Specific user to view
    - limit: (optional) Number of records to return (default: 100)
    - offset: (optional) Pagination offset (default: 0)
    
    Returns:
    {
        "total": 50,
        "logs": [
            {
                "id": 1,
                "kyc_id": 1,
                "action": "created",
                "old_status": null,
                "new_status": "pending",
                "changed_by": null,
                "created_at": "2026-05-26T10:00:00Z"
            }
        ]
    }
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        target_user_id = request.args.get('user_id', None, type=int)
        
        from app.database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if target_user_id:
                cursor.execute("""
                    SELECT COUNT(*) FROM kyc_audit_log kal
                    JOIN kyc_verifications kv ON kal.kyc_id = kv.id
                    WHERE kv.user_id = %s
                """, (target_user_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM kyc_audit_log")
            
            result = cursor.fetchone()
            total = result[0] if isinstance(result, tuple) else result.get('COUNT(*)', 0)
            
            if target_user_id:
                cursor.execute("""
                    SELECT kal.id, kal.kyc_id, kal.action, kal.old_status, 
                           kal.new_status, kal.changed_by, kal.created_at
                    FROM kyc_audit_log kal
                    JOIN kyc_verifications kv ON kal.kyc_id = kv.id
                    WHERE kv.user_id = %s
                    ORDER BY kal.created_at DESC
                    LIMIT %s OFFSET %s
                """, (target_user_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT id, kyc_id, action, old_status, new_status, 
                           changed_by, created_at
                    FROM kyc_audit_log
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))
            
            logs = []
            for record in cursor.fetchall():
                if isinstance(record, dict):
                    logs.append({
                        'id': record['id'],
                        'kyc_id': record['kyc_id'],
                        'action': record['action'],
                        'old_status': record['old_status'],
                        'new_status': record['new_status'],
                        'changed_by': record['changed_by'],
                        'created_at': record['created_at'].isoformat() + 'Z' if record['created_at'] else None
                    })
                else:
                    logs.append({
                        'id': record[0],
                        'kyc_id': record[1],
                        'action': record[2],
                        'old_status': record[3],
                        'new_status': record[4],
                        'changed_by': record[5],
                        'created_at': record[6].isoformat() + 'Z' if record[6] else None
                    })
            
            return jsonify({'total': total, 'logs': logs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Health check endpoint
@api.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat() + 'Z'}), 200
