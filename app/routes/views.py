from flask import render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.routes import main
from app.models import KYCRequest, User, Company
from app.database import ping_database


@main.route('/')
def index():
    return render_template('pages/index.html')


@main.route('/about')
def about():
    return render_template('pages/about.html')


@main.route('/solutions')
def solutions():
    return render_template('pages/solutions.html')


@main.route('/pricing')
def pricing():
    return render_template('pages/pricing.html')


@main.route('/docs')
def docs():
    return render_template('pages/docs.html')


@main.route('/contact')
def contact():
    return render_template('pages/contact.html')


@main.route('/blog')
def blog():
    return render_template('pages/blog.html')


@main.route('/careers')
def careers():
    return render_template('pages/careers.html')


@main.route('/status')
def status():
    db_connected, ping_ok, db_error = ping_database()
    status_snapshot = {
        'app_name': current_app.name,
        'debug': bool(current_app.debug),
        'database_connected': db_connected,
        'database_ping_ok': ping_ok,
        'database_error': db_error,
        'database_host': current_app.config.get('MYSQL_HOST'),
        'database_port': current_app.config.get('MYSQL_PORT'),
        'database_name': current_app.config.get('MYSQL_DATABASE'),
        'database_ssl': bool(current_app.config.get('MYSQL_SSL_CA')),
    }
    return render_template('pages/status.html', status=status_snapshot)


# Dashboards
@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    elif current_user.role == 'company_admin':
        return redirect(url_for('main.company_dashboard'))
    return render_template('pages/dashboards/user.html')


@main.route('/dashboard/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    stats = {
        'total_users': User.query.count(),
        'total_companies': Company.query.count(),
        'total_requests': KYCRequest.query.count()
    }
    return render_template('pages/dashboards/admin.html', stats=stats)


@main.route('/dashboard/company')
@login_required
def company_dashboard():
    if current_user.role not in ['company_admin', 'admin']:
        return redirect(url_for('main.dashboard'))
    company = Company.query.get(current_user.company_id) if current_user.company_id else None
    requests = KYCRequest.query.filter_by(company_id=current_user.company_id).all() if current_user.company_id else []
    return render_template('pages/dashboards/company.html', company=company, requests=requests)


# API
@main.route('/api/demo-request', methods=['POST'])
def demo_request():
    try:
        payload = request.get_json(silent=True) or request.form or {}
        email = str(payload.get('email', '')).strip()
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        return jsonify({'success': True, 'message': 'Request received'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
