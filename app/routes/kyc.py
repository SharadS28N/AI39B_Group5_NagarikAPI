import os
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import KYCRequest, AuditLog, GovernmentCitizenRecord, DataAccessPermission
from app.extensions import db
from app.services.ocr_service import extract_national_id
from app.services.face_service import compare_faces_simple

kyc_bp = Blueprint('kyc', __name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png','jpg','jpeg'}


@kyc_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        id_file = request.files.get('id_image')
        selfie = request.files.get('selfie')

        if not id_file or not allowed_file(id_file.filename):
            flash('Please upload a valid National ID image (JPG/PNG).', 'danger')
            return render_template('pages/kyc/upload.html')

        # Create case
    case = KYCRequest(
        user_id=current_user.id,
        company_id=current_user.company_id,
        status='processing',
        verification_type='kyc'
    )
    db.session.add(case)
    db.session.flush()

    # Save ID image
    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    id_dir = os.path.join(upload_dir, 'ids')
    selfie_dir = os.path.join(upload_dir, 'selfies')
    os.makedirs(id_dir, exist_ok=True)
    os.makedirs(selfie_dir, exist_ok=True)

    id_filename = f"id_{case.id}_{secrets.token_hex(4)}.jpg"
    id_path = os.path.join(id_dir, id_filename)
    id_file.save(id_path)
    case.id_image_path = id_path

    # Save selfie if provided
    selfie_path = None
    if selfie and allowed_file(selfie.filename):
        selfie_filename = f"selfie_{case.id}_{secrets.token_hex(4)}.jpg"
        selfie_path = os.path.join(selfie_dir, selfie_filename)
        selfie.save(selfie_path)
        case.selfie_path = selfie_path

        # Run OCR
    ocr_result = extract_national_id(id_path)

    # Check against fake government database
    government_match_found = False
    government_record = None
    if ocr_result.get('success'):
        case.full_name = ocr_result.get('full_name')
        case.date_of_birth = ocr_result.get('date_of_birth')
        case.id_number = ocr_result.get('id_number')
        case.address = ocr_result.get('address')
        case.citizenship_no = ocr_result.get('citizenship_no')
        case.issue_date = ocr_result.get('issue_date')
        case.issue_district = ocr_result.get('issue_district')
        case.ocr_confidence = ocr_result.get('confidence', 0.0)
        case.raw_ocr_data = {'raw_text': ocr_result.get('raw_text', '')}
        
        # Check government database
        if case.id_number:
            government_record = GovernmentCitizenRecord.query.filter_by(id_number=case.id_number).first()
            if not government_record and case.citizenship_no:
                government_record = GovernmentCitizenRecord.query.filter_by(citizenship_no=case.citizenship_no).first()
            
            if government_record and government_record.is_active:
                government_match_found = True

    # Run face match if selfie provided
    face_score = 0.0
    if selfie_path:
        face_result = compare_faces_simple(id_path, selfie_path)
        face_score = face_result.get('score', 0.0)
        case.face_match_score = face_score

    # Calculate overall score - government match is a big factor!
    ocr_weight = 0.3
    face_weight = 0.2
    government_match_weight = 0.5
    base_score = (case.ocr_confidence * ocr_weight) + (face_score * face_weight)
    government_bonus = 1.0 if government_match_found else 0.0
    case.overall_score = round(
        base_score + (government_bonus * government_match_weight), 3
    )

    # Auto-decide status - government match makes it verified!
    if government_match_found and case.ocr_confidence >= 0.5:
        case.status = 'verified'
        # Create data access permission for the company
        if current_user.company_id:
            permission = DataAccessPermission(
                company_id=current_user.company_id,
                citizen_id=government_record.id,
                user_id=current_user.id,
                granted_by=current_user.id,
                access_type='full',
                is_active=True
            )
            db.session.add(permission)
    elif case.overall_score >= 0.7:
        case.status = 'manual_review'
    else:
        case.status = 'rejected'

        db.session.commit()

        # Audit log
        log = AuditLog(
            case_id=case.id,
            user_id=current_user.id,
            action='kyc_submitted',
            detail=f'OCR confidence: {case.ocr_confidence}, Face: {face_score}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        flash(f'Verification complete — Case {case.case_ref}', 'success')
        return redirect(url_for('kyc.result', case_id=case.id))

    return render_template('pages/kyc/upload.html')


@kyc_bp.route('/result/<int:case_id>')
@login_required
def result(case_id):
    case = KYCRequest.query.get_or_404(case_id)
    return render_template('pages/kyc/result.html', case=case)


@kyc_bp.route('/cases')
@login_required
def cases():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query = KYCRequest.query
    if current_user.role not in ['admin']:
        query = query.filter_by(company_id=current_user.company_id)
    if status:
        query = query.filter_by(status=status)
    cases = query.order_by(KYCRequest.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('pages/kyc/cases.html', cases=cases, status=status)


@kyc_bp.route('/case/<int:case_id>/flag', methods=['POST'])
@login_required
def flag_case(case_id):
    case = KYCRequest.query.get_or_404(case_id)
    reason = request.form.get('reason', '')
    case.is_flagged = not case.is_flagged
    case.flag_reason = reason if case.is_flagged else None
    log = AuditLog(case_id=case.id, user_id=current_user.id,
                   action='flagged' if case.is_flagged else 'unflagged',
                   detail=reason, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    flash(f'Case {case.case_ref} {"flagged" if case.is_flagged else "unflagged"}.', 'warning')
    return redirect(url_for('kyc.result', case_id=case.id))
