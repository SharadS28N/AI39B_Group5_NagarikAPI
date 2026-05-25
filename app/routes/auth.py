from urllib.parse import urlparse, urljoin

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from app.models import User, db
from app import bcrypt

auth = Blueprint('auth', __name__)


def _is_safe_next_url(target):
    if not target:
        return False

    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in {'http', 'https'} and urlparse(request.host_url).netloc == test_url.netloc

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        remember = True if request.form.get('remember') else False

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('pages/auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if _is_safe_next_url(next_page):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            
    return render_template('pages/auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''

        if not full_name or not email or not password:
            flash('Full name, email, and password are required.', 'danger')
            return render_template('pages/auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('pages/auth/register.html')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))
            
        try:
            new_user = User(full_name=full_name, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash('Unable to create account right now. Please try again.', 'danger')
            return render_template('pages/auth/register.html')
        
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('pages/auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
