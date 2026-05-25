from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.routes import main
from app.models import KYCRequest, User, Company

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
    company = Company.query.get(current_user.company_id)
    requests = KYCRequest.query.filter_by(company_id=current_user.company_id).all()
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
    except Exception:
        return jsonify({'error': 'Unable to process request at the moment'}), 500
