from functools import wraps
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models import APIKey, KYCRequest, AuditLog
from app.extensions import db

api_bp = Blueprint('api', __name__)


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = (request.headers.get('X-API-Key') or
               request.args.get('api_key'))
        if not key:
            return jsonify({'error': 'API key required',
                            'hint': 'Pass X-API-Key header'}), 401
        api_key = APIKey.query.filter_by(key=key, is_active=True).first()
        if not api_key:
            return jsonify({'error': 'Invalid or revoked API key'}), 403
        api_key.requests_count += 1
        api_key.last_used = datetime.utcnow()
        db.session.commit()
        request.api_key = api_key
        return f(*args, **kwargs)
    return decorated


@api_bp.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'operational',
        'service': 'NagarikAPI',
        'version': '1.0.0'
    }), 200


@api_bp.route('/kyc/requests', methods=['GET'])
@require_api_key
def get_kyc_requests():
    company_id = request.api_key.company_id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status')

    query = KYCRequest.query.filter_by(company_id=company_id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    pagination = query.order_by(KYCRequest.created_at.desc()).paginate(page=page, per_page=per_page)
    requests_data = [
        {
            'id': req.id,
            'case_ref': req.case_ref,
            'status': req.status,
            'full_name': req.full_name,
            'created_at': req.created_at.isoformat() if req.created_at else None
        }
        for req in pagination.items
    ]

    return jsonify({
        'requests': requests_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@api_bp.route('/kyc/requests/<int:request_id>', methods=['GET'])
@require_api_key
def get_kyc_request(request_id):
    company_id = request.api_key.company_id
    kyc_request = KYCRequest.query.filter_by(id=request_id, company_id=company_id).first_or_404()

    return jsonify(kyc_request.to_dict()), 200
