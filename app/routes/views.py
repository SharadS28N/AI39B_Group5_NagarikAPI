from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from app.models import KYCRequest, User, Company
from app.extensions import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('pages/index.html')


@main_bp.route('/about')
def about():
    return render_template('pages/about.html')


@main_bp.route('/solutions')
def solutions():
    return render_template('pages/solutions.html')


@main_bp.route('/pricing')
def pricing():
    return render_template('pages/pricing.html')


@main_bp.route('/docs')
def docs():
    return render_template('pages/docs.html')


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Handle form submission
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('pages/contact.html')


@main_bp.route('/blog')
def blog():
    return render_template('pages/blog.html')


@main_bp.route('/careers')
def careers():
    return render_template('pages/careers.html')


@main_bp.route('/status')
def status():
    return render_template('pages/status.html')


# Dashboards
@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('dashboard.admin'))
    elif current_user.role == 'company_admin':
        return redirect(url_for('dashboard.company'))
    return redirect(url_for('dashboard.user_dashboard'))


# API
@main_bp.route('/api/demo-request', methods=['POST'])
def demo_request():
    try:
        payload = request.get_json(silent=True) or request.form or {}
        email = str(payload.get('email', '')).strip()
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        return jsonify({'success': True, 'message': 'Request received'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
