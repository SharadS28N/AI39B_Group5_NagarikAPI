import os
import secrets
from functools import wraps
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.models import APIKey, KYCRequest, AuditLog, Company, StudentRecord, GovernmentCitizenRecord, DataAccessPermission, DataAccessLog
from app.extensions import db
from app.services.ocr_service import extract_national_id, extract_student_id
from app.services.face_service import compare_faces_simple

api_bp = Blueprint('api', __name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}


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


@api_bp.route('/kyc/verify', methods=['POST'])
@require_api_key
def verify_kyc():
    if 'nid_image' not in request.files:
        return jsonify({'error': 'No nid_image file provided'}), 400
    
    nid_file = request.files['nid_image']
    selfie_file = request.files.get('selfie')
    
    if nid_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(nid_file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Create upload directories
    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    ids_dir = os.path.join(upload_dir, 'ids')
    selfies_dir = os.path.join(upload_dir, 'selfies')
    os.makedirs(ids_dir, exist_ok=True)
    os.makedirs(selfies_dir, exist_ok=True)
    
    # Save NID image
    nid_filename = f"nid_{secrets.token_hex(8)}.{nid_file.filename.rsplit('.', 1)[1].lower()}"
    nid_path = os.path.join(ids_dir, nid_filename)
    nid_file.save(nid_path)
    
    # Save selfie if provided
    selfie_path = None
    if selfie_file and allowed_file(selfie_file.filename):
        selfie_filename = f"selfie_{secrets.token_hex(8)}.{selfie_file.filename.rsplit('.', 1)[1].lower()}"
        selfie_path = os.path.join(selfies_dir, selfie_filename)
        selfie_file.save(selfie_path)
    
    # Create KYC request
    kyc_request = KYCRequest(
        company_id=request.api_key.company_id,
        verification_type='kyc',
        document_type='national_id',
        id_image_path=nid_path,
        selfie_path=selfie_path,
        status='processing'
    )
    db.session.add(kyc_request)
    db.session.flush()
    
    # Run OCR
    ocr_result = extract_national_id(nid_path)
    if ocr_result.get('success'):
        kyc_request.full_name = ocr_result.get('full_name')
        kyc_request.date_of_birth = ocr_result.get('date_of_birth')
        kyc_request.id_number = ocr_result.get('id_number')
        kyc_request.address = ocr_result.get('address')
        kyc_request.citizenship_no = ocr_result.get('citizenship_no')
        kyc_request.issue_date = ocr_result.get('issue_date')
        kyc_request.issue_district = ocr_result.get('issue_district')
        kyc_request.ocr_confidence = ocr_result.get('confidence', 0.0)
        kyc_request.raw_ocr_data = {'raw_text': ocr_result.get('raw_text', '')}
    
    # Check government database
    government_match_found = False
    government_record = None
    if kyc_request.id_number:
        government_record = GovernmentCitizenRecord.query.filter_by(id_number=kyc_request.id_number).first()
        if not government_record and kyc_request.citizenship_no:
            government_record = GovernmentCitizenRecord.query.filter_by(citizenship_no=kyc_request.citizenship_no).first()
        if government_record and government_record.is_active:
            government_match_found = True
    
    # Run face match
    face_score = 0.0
    if selfie_path:
        face_result = compare_faces_simple(nid_path, selfie_path)
        face_score = face_result.get('score', 0.0)
        kyc_request.face_match_score = face_score
    
    # Calculate overall score - government match is a big factor!
    ocr_weight = 0.3
    face_weight = 0.2
    government_match_weight = 0.5
    base_score = (kyc_request.ocr_confidence * ocr_weight) + (face_score * face_weight)
    government_bonus = 1.0 if government_match_found else 0.0
    kyc_request.overall_score = round(
        base_score + (government_bonus * government_match_weight), 3
    )
    
    # Auto-decide status - government match makes it verified!
    if government_match_found and kyc_request.ocr_confidence >= 0.5:
        kyc_request.status = 'verified'
        # Create data access permission
        permission = DataAccessPermission(
            company_id=request.api_key.company_id,
            citizen_id=government_record.id,
            access_type='full',
            is_active=True
        )
        db.session.add(permission)
        # Create data access log
        data_log = DataAccessLog(
            company_id=request.api_key.company_id,
            api_key_id=request.api_key.id,
            citizen_id=government_record.id,
            access_type='verify',
            data_accessed={
                'full_name': government_record.full_name,
                'id_number': government_record.id_number
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(data_log)
    elif kyc_request.overall_score >= 0.7:
        kyc_request.status = 'manual_review'
    else:
        kyc_request.status = 'rejected'
    
    db.session.commit()
    
    # Log audit
    log = AuditLog(
        case_id=kyc_request.id,
        action='kyc_submitted_api',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'case_ref': kyc_request.case_ref,
        'status': kyc_request.status,
        'extracted_data': {
            'full_name': kyc_request.full_name,
            'date_of_birth': kyc_request.date_of_birth,
            'id_number': kyc_request.id_number,
            'address': kyc_request.address,
            'citizenship_no': kyc_request.citizenship_no
        },
        'scores': {
            'ocr_confidence': kyc_request.ocr_confidence,
            'face_match_score': kyc_request.face_match_score,
            'overall_score': kyc_request.overall_score
        }
    }), 200


@api_bp.route('/student/verify', methods=['POST'])
@require_api_key
def verify_student():
    if 'nid_image' not in request.files or 'student_id' not in request.files:
        return jsonify({'error': 'Both nid_image and student_id files are required'}), 400
    
    nid_file = request.files['nid_image']
    student_id_file = request.files['student_id']
    selfie_file = request.files.get('selfie')
    
    if nid_file.filename == '' or student_id_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(nid_file.filename) or not allowed_file(student_id_file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Create upload directories
    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    ids_dir = os.path.join(upload_dir, 'ids')
    selfies_dir = os.path.join(upload_dir, 'selfies')
    os.makedirs(ids_dir, exist_ok=True)
    os.makedirs(selfies_dir, exist_ok=True)
    
    # Save images
    nid_filename = f"nid_{secrets.token_hex(8)}.{nid_file.filename.rsplit('.', 1)[1].lower()}"
    nid_path = os.path.join(ids_dir, nid_filename)
    nid_file.save(nid_path)
    
    student_id_filename = f"sid_{secrets.token_hex(8)}.{student_id_file.filename.rsplit('.', 1)[1].lower()}"
    student_id_path = os.path.join(ids_dir, student_id_filename)
    student_id_file.save(student_id_path)
    
    selfie_path = None
    if selfie_file and allowed_file(selfie_file.filename):
        selfie_filename = f"selfie_{secrets.token_hex(8)}.{selfie_file.filename.rsplit('.', 1)[1].lower()}"
        selfie_path = os.path.join(selfies_dir, selfie_filename)
        selfie_file.save(selfie_path)
    
    # Create KYC request
    kyc_request = KYCRequest(
        company_id=request.api_key.company_id,
        verification_type='student',
        document_type='national_id',
        id_image_path=nid_path,
        selfie_path=selfie_path,
        status='processing'
    )
    db.session.add(kyc_request)
    db.session.flush()
    
    # Run OCR on NID
    nid_ocr_result = extract_national_id(nid_path)
    if nid_ocr_result.get('success'):
        kyc_request.full_name = nid_ocr_result.get('full_name')
        kyc_request.date_of_birth = nid_ocr_result.get('date_of_birth')
        kyc_request.id_number = nid_ocr_result.get('id_number')
        kyc_request.address = nid_ocr_result.get('address')
        kyc_request.citizenship_no = nid_ocr_result.get('citizenship_no')
        kyc_request.ocr_confidence = nid_ocr_result.get('confidence', 0.0)
    
    # Run OCR on student ID
    student_ocr_result = extract_student_id(student_id_path)
    if student_ocr_result.get('success'):
        kyc_request.institution_name = student_ocr_result.get('institution_name')
        kyc_request.student_id = student_ocr_result.get('student_id')
        kyc_request.program = student_ocr_result.get('program')
        kyc_request.enrollment_year = student_ocr_result.get('enrollment_year')
    
    # Run face match
    face_score = 0.0
    if selfie_path:
        face_result = compare_faces_simple(nid_path, selfie_path)
        face_score = face_result.get('score', 0.0)
        kyc_request.face_match_score = face_score
    
    # Calculate overall score
    ocr_weight = 0.5
    face_weight = 0.5
    kyc_request.overall_score = round(
        (kyc_request.ocr_confidence * ocr_weight) + (face_score * face_weight), 3
    )
    
    # Auto-decide status
    if kyc_request.overall_score >= 0.65:
        kyc_request.status = 'verified'
    elif kyc_request.overall_score >= 0.4:
        kyc_request.status = 'manual_review'
    else:
        kyc_request.status = 'rejected'
    
    # Create student record
    student_record = StudentRecord(
        kyc_request_id=kyc_request.id,
        institution_name=kyc_request.institution_name,
        student_id=kyc_request.student_id,
        program=kyc_request.program,
        enrollment_year=kyc_request.enrollment_year,
        verified=(kyc_request.status == 'verified')
    )
    db.session.add(student_record)
    
    db.session.commit()
    
    # Log audit
    log = AuditLog(
        case_id=kyc_request.id,
        action='student_submitted_api',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'case_ref': kyc_request.case_ref,
        'status': kyc_request.status,
        'extracted_data': {
            'full_name': kyc_request.full_name,
            'date_of_birth': kyc_request.date_of_birth,
            'id_number': kyc_request.id_number
        },
        'student_data': {
            'institution_name': kyc_request.institution_name,
            'student_id': kyc_request.student_id,
            'program': kyc_request.program,
            'enrollment_year': kyc_request.enrollment_year
        },
        'scores': {
            'ocr_confidence': kyc_request.ocr_confidence,
            'face_match_score': kyc_request.face_match_score,
            'overall_score': kyc_request.overall_score
        }
    }), 200


@api_bp.route('/kyc/case/<case_ref>', methods=['GET'])
@require_api_key
def get_case_by_ref(case_ref):
    company_id = request.api_key.company_id
    kyc_request = KYCRequest.query.filter_by(case_ref=case_ref, company_id=company_id).first_or_404()
    return jsonify(kyc_request.to_dict()), 200


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
