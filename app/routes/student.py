import os
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import KYCRequest, StudentRecord, AuditLog
from app.services.ocr_service import extract_student_id, extract_national_id
from app.services.face_service import compare_faces_simple

student_bp = Blueprint('student', __name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png','jpg','jpeg'}


@student_bp.route('/verify', methods=['GET', 'POST'])
@login_required
def verify():
    if request.method == 'POST':
        national_id = request.files.get('national_id')
        student_id = request.files.get('student_id')
        selfie = request.files.get('selfie')

        if not national_id or not student_id:
            flash('Please upload both National ID and Student ID.', 'danger')
            return render_template('pages/student/verify.html')

        case = KYCRequest(
            user_id=current_user.id,
            company_id=current_user.company_id,
            status='processing',
            verification_type='student'
        )
        db.session.add(case)
        db.session.flush()

        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')

        # Save national ID
        nid_path = os.path.join(upload_dir, 'ids', f"nid_{case.id}.jpg")
        national_id.save(nid_path)
        case.id_image_path = nid_path

        # Save student ID
        sid_path = os.path.join(upload_dir, 'ids', f"sid_{case.id}.jpg")
        student_id.save(sid_path)

        # Save selfie
        selfie_path = None
        if selfie and allowed_file(selfie.filename):
            selfie_path = os.path.join(upload_dir, 'selfies', f"selfie_{case.id}.jpg")
            selfie.save(selfie_path)
            case.selfie_path = selfie_path

        # OCR national ID
        nid_result = extract_national_id(nid_path)
        if nid_result.get('success'):
            case.full_name = nid_result.get('full_name')
            case.date_of_birth = nid_result.get('date_of_birth')
            case.id_number = nid_result.get('id_number')
            case.address = nid_result.get('address')
            case.ocr_confidence = nid_result.get('confidence', 0.0)

        # OCR student ID
        sid_result = extract_student_id(sid_path)
        if sid_result.get('success'):
            case.institution_name = sid_result.get('institution_name')
            case.student_id = sid_result.get('student_id')
            case.program = sid_result.get('program')
            case.enrollment_year = sid_result.get('enrollment_year')

        # Face match
        face_score = 0.0
        if selfie_path:
            face_result = compare_faces_simple(nid_path, selfie_path)
            face_score = face_result.get('score', 0.0)
            case.face_match_score = face_score

        case.overall_score = round(
            (case.ocr_confidence * 0.5) + (face_score * 0.5), 3
        )

        case.status = 'verified' if case.overall_score >= 0.65 else (
            'manual_review' if case.overall_score >= 0.4 else 'rejected'
        )

        # Save student record
        student = StudentRecord(
            kyc_request_id=case.id,
            institution_name=case.institution_name,
            student_id=case.student_id,
            program=case.program,
            enrollment_year=case.enrollment_year,
            verified=(case.status == 'verified')
        )
        db.session.add(student)
        db.session.commit()

        log = AuditLog(case_id=case.id, user_id=current_user.id,
                       action='student_verify_submitted',
                       ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()

        flash(f'Student verification complete — Case {case.case_ref}', 'success')
        return redirect(url_for('student.result', case_id=case.id))

    return render_template('pages/student/verify.html')


@student_bp.route('/result/<int:case_id>')
@login_required
def result(case_id):
    case = KYCRequest.query.get_or_404(case_id)
    student = StudentRecord.query.filter_by(kyc_request_id=case_id).first()
    return render_template('pages/student/result.html', case=case, student=student)
