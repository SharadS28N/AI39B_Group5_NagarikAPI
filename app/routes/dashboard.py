from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import KYCRequest, User, Company, APIKey, AuditLog, DataAccessPermission, DataAccessLog, GovernmentCitizenRecord
from app.extensions import db
from sqlalchemy import func
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        return redirect(url_for('dashboard.admin'))
    elif current_user.role == 'company_admin':
        return redirect(url_for('dashboard.company'))
    return redirect(url_for('dashboard.user_dashboard'))


@dashboard_bp.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        return render_template('pages/errors/403.html'), 403

    total_cases = KYCRequest.query.count()
    verified_cases = KYCRequest.query.filter_by(status='verified').count()
    pending_cases = KYCRequest.query.filter_by(status='pending').count()
    rejected_cases = KYCRequest.query.filter_by(status='rejected').count()
    flagged_cases = KYCRequest.query.filter_by(is_flagged=True).count()
    total_users = User.query.count()
    total_companies = Company.query.count()

    # Last 7 days trend
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_trend = db.session.query(
        func.date(KYCRequest.created_at).label('date'),
        func.count(KYCRequest.id).label('count')
    ).filter(KYCRequest.created_at >= seven_days_ago)\
     .group_by(func.date(KYCRequest.created_at))\
     .all()

    trend_data = {str(row.date): row.count for row in daily_trend}

    recent_cases = KYCRequest.query.order_by(
        KYCRequest.created_at.desc()
    ).limit(15).all()

    recent_logs = AuditLog.query.order_by(
        AuditLog.created_at.desc()
    ).limit(10).all()

    stats = {
        'total_cases': total_cases,
        'verified_cases': verified_cases,
        'pending_cases': pending_cases,
        'rejected_cases': rejected_cases,
        'flagged_cases': flagged_cases,
        'total_users': total_users,
        'total_companies': total_companies,
        'success_rate': round((verified_cases / total_cases * 100), 1) if total_cases > 0 else 0,
        'trend_data': trend_data,
    }

    return render_template('pages/dashboards/admin.html',
                           stats=stats,
                           recent_cases=recent_cases,
                           recent_logs=recent_logs)


@dashboard_bp.route('/company')
@login_required
def company():
    if current_user.role not in ['company_admin', 'admin']:
        return render_template('pages/errors/403.html'), 403

    company = Company.query.get(current_user.company_id)
    api_keys = APIKey.query.filter_by(
        company_id=current_user.company_id, is_active=True
    ).all()

    cases = KYCRequest.query.filter_by(
        company_id=current_user.company_id
    ).order_by(KYCRequest.created_at.desc()).limit(20).all()

    total = KYCRequest.query.filter_by(company_id=current_user.company_id).count()
    verified = KYCRequest.query.filter_by(
        company_id=current_user.company_id, status='verified'
    ).count()

    # Get data access permissions
    data_permissions = DataAccessPermission.query.filter_by(
        company_id=current_user.company_id, is_active=True
    ).order_by(DataAccessPermission.created_at.desc()).limit(20).all()

    # Get data access logs
    data_access_logs = DataAccessLog.query.filter_by(
        company_id=current_user.company_id
    ).order_by(DataAccessLog.created_at.desc()).limit(20).all()

    stats = {
        'total': total,
        'verified': verified,
        'success_rate': round((verified / total * 100), 1) if total > 0 else 0,
    }

    return render_template('pages/dashboards/company.html',
                           company=company,
                           api_keys=api_keys,
                           cases=cases,
                           stats=stats,
                           data_permissions=data_permissions,
                           data_access_logs=data_access_logs)


@dashboard_bp.route('/user')
@login_required
def user_dashboard():
    cases = KYCRequest.query.filter_by(
        user_id=current_user.id
    ).order_by(KYCRequest.created_at.desc()).all()
    return render_template('pages/dashboards/user.html', cases=cases)


@dashboard_bp.route('/api-keys/generate', methods=['POST'])
@login_required
def generate_api_key():
    if current_user.role not in ['company_admin', 'admin']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard.company'))

    key = APIKey(
        company_id=current_user.company_id,
        name=request.form.get('name', 'API Key')
    )
    db.session.add(key)
    db.session.commit()
    flash('API key generated successfully!', 'success')
    return redirect(url_for('dashboard.company'))


@dashboard_bp.route('/api-keys/<int:key_id>/revoke', methods=['POST'])
@login_required
def revoke_api_key(key_id):
    key = APIKey.query.get_or_404(key_id)
    if key.company_id != current_user.company_id and current_user.role != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard.company'))
    key.is_active = False
    db.session.commit()
    flash('API key revoked!', 'warning')
    return redirect(url_for('dashboard.company'))


@dashboard_bp.route('/data-access/<int:perm_id>/revoke', methods=['POST'])
@login_required
def revoke_data_access(perm_id):
    perm = DataAccessPermission.query.get_or_404(perm_id)
    if perm.company_id != current_user.company_id and current_user.role != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard.company'))
    perm.is_active = False
    db.session.commit()
    flash('Data access revoked!', 'warning')
    return redirect(url_for('dashboard.company'))
