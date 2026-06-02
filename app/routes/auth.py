from urllib.parse import urlparse, urljoin

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User

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
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.find_by_email(email)
        
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
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.find_by_email(email)
        if user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))
            
        User.create(full_name=full_name, email=email, password=password)
        
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('pages/auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
