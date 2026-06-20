# NagarikAPI — Complete Build Guide
## KYC + Student Verification SaaS Platform
### Production-Ready Implementation from Scratch

---

> **What this builds:** A Persona + SheerID alternative for Nepal — OCR-based National ID verification,
> student status verification, face matching, institutional API access, and a full admin SaaS dashboard.
> Stack: Python · Flask · Jinja2 · MySQL (Aiven) · Google Cloud Vision · Bootstrap 5

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT INSTITUTIONS                       │
│         Banks · Fintechs · Universities · Insurance         │
└──────────────────────┬──────────────────────────────────────┘
                       │ API Key (X-API-Key header)
┌──────────────────────▼──────────────────────────────────────┐
│                     NAGARIKAPI CORE                         │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │   Auth   │  │  OCR     │  │  Face    │  │   Admin   │  │
│  │  System  │  │ Engine   │  │  Match   │  │ Dashboard │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Student  │  │  Audit   │  │ Webhook  │  │  API Key  │  │
│  │ Verify   │  │   Log    │  │  System  │  │  Manager  │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Aiven MySQL   Google Vision   File Storage
```

---

## PART 1 — PROJECT STRUCTURE

Create this exact folder structure:

```
NagarikAPI/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models/
│   │   └── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── views.py
│   │   ├── kyc.py
│   │   ├── student.py
│   │   ├── dashboard.py
│   │   └── api.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py
│   │   ├── face_service.py
│   │   └── webhook_service.py
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css
│   │   ├── js/
│   │   │   └── main.js
│   │   └── uploads/
│   └── templates/
│       ├── layouts/
│       │   └── base.html
│       ├── pages/
│       │   ├── index.html
│       │   ├── auth/
│       │   │   ├── login.html
│       │   │   └── register.html
│       │   ├── kyc/
│       │   │   ├── upload.html
│       │   │   └── result.html
│       │   ├── student/
│       │   │   ├── verify.html
│       │   │   └── result.html
│       │   └── dashboards/
│       │       ├── admin.html
│       │       ├── company.html
│       │       └── user.html
├── config.py
├── run.py
├── requirements.txt
├── .env
├── .gitignore
├── google_vision.json
└── ca.pem
```

---

## PART 2 — DEPENDENCIES

### requirements.txt
```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-Migrate==4.0.7
Flask-Bcrypt==1.0.1
Flask-WTF==1.2.1
PyMySQL==1.1.1
python-dotenv==1.0.1
google-cloud-vision==3.7.2
Pillow==10.4.0
requests==2.32.3
cryptography==42.0.8
Werkzeug==3.0.3
face-recognition==1.3.0
numpy==1.26.4
opencv-python-headless==4.9.0.80
```

Install all:
```bash
pip install -r requirements.txt
```

> **Note:** `face-recognition` requires `dlib`. On Windows run:
> `pip install cmake` then `pip install dlib` then `pip install face-recognition`
> If dlib fails, use the simpler face comparison fallback in Part 6.

---

## PART 3 — ENVIRONMENT CONFIG

### .env
```env
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=nagarikapi-super-secret-key-change-in-production-2025

# Aiven MySQL
DB_HOST=your-host.aivencloud.com
DB_PORT=12398
DB_NAME=defaultdb
DB_USER=avnadmin
DB_PASSWORD=your_password_here
SSL_CA=ca.pem

# Google Vision
GOOGLE_APPLICATION_CREDENTIALS=google_vision.json

# Upload settings
UPLOAD_FOLDER=app/static/uploads
MAX_CONTENT_LENGTH=10485760

# App URL (for webhooks)
APP_URL=http://localhost:5000
```

### config.py
```python
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'ssl': {'ca': os.getenv('SSL_CA', 'ca.pem')}}
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'app/static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 10485760))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    APP_URL = os.getenv('APP_URL', 'http://localhost:5000')
    WTF_CSRF_ENABLED = True
```

---

## PART 4 — DATABASE MODELS

### app/models/__init__.py
```python
import secrets
import hashlib
from datetime import datetime
from app.extensions import db, bcrypt
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name     = db.Column(db.String(100), nullable=False)
    role          = db.Column(db.String(20), default='user')
    # roles: 'admin', 'company_admin', 'user'
    company_id    = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    kyc_requests  = db.relationship('KYCRequest', backref='submitter', lazy=True,
                                     foreign_keys='KYCRequest.user_id')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Company(db.Model):
    __tablename__ = 'companies'
    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(100), nullable=False)
    type                = db.Column(db.String(30), default='bank')
    # types: bank, fintech, insurance, university, mfi
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    webhook_url         = db.Column(db.String(500), nullable=True)
    is_active           = db.Column(db.Boolean, default=True)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    users    = db.relationship('User', backref='company', lazy=True)
    api_keys = db.relationship('APIKey', backref='company', lazy=True)
    requests = db.relationship('KYCRequest', backref='institution', lazy=True,
                                foreign_keys='KYCRequest.company_id')


class APIKey(db.Model):
    __tablename__ = 'api_keys'
    id             = db.Column(db.Integer, primary_key=True)
    key            = db.Column(db.String(64), unique=True, nullable=False,
                               default=lambda: secrets.token_hex(32))
    company_id     = db.Column(db.Integer, db.ForeignKey('companies.id'))
    name           = db.Column(db.String(100), default='Default Key')
    is_active      = db.Column(db.Boolean, default=True)
    requests_count = db.Column(db.Integer, default=0)
    last_used      = db.Column(db.DateTime, nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def mask(self):
        return f"{self.key[:8]}...{self.key[-4:]}"


class KYCRequest(db.Model):
    __tablename__ = 'kyc_requests'
    id               = db.Column(db.Integer, primary_key=True)
    case_ref         = db.Column(db.String(20), unique=True, nullable=False,
                                 default=lambda: f"KYC-{secrets.token_hex(4).upper()}")
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    company_id       = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    # Verification type
    verification_type = db.Column(db.String(20), default='kyc')
    # types: kyc, student

    # Document info
    document_type    = db.Column(db.String(20), default='national_id')
    id_image_path    = db.Column(db.String(500), nullable=True)
    selfie_path      = db.Column(db.String(500), nullable=True)

    # OCR extracted data
    full_name        = db.Column(db.String(200), nullable=True)
    date_of_birth    = db.Column(db.String(30), nullable=True)
    id_number        = db.Column(db.String(50), nullable=True)
    address          = db.Column(db.Text, nullable=True)
    citizenship_no   = db.Column(db.String(50), nullable=True)
    issue_date       = db.Column(db.String(30), nullable=True)
    issue_district   = db.Column(db.String(100), nullable=True)

    # Student verification extra fields
    institution_name = db.Column(db.String(200), nullable=True)
    student_id       = db.Column(db.String(50), nullable=True)
    enrollment_year  = db.Column(db.String(10), nullable=True)
    program          = db.Column(db.String(200), nullable=True)

    # Scores
    ocr_confidence   = db.Column(db.Float, default=0.0)
    face_match_score = db.Column(db.Float, default=0.0)
    overall_score    = db.Column(db.Float, default=0.0)

    # Status
    status           = db.Column(db.String(20), default='pending')
    # pending | processing | verified | rejected | manual_review

    is_flagged       = db.Column(db.Flag, default=False)
    flag_reason      = db.Column(db.Text, nullable=True)

    # Raw OCR data
    raw_ocr_data     = db.Column(db.JSON, nullable=True)

    reviewed_by      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow)

    audit_logs       = db.relationship('AuditLog', backref='case', lazy=True)

    def to_dict(self):
        return {
            'case_ref':        self.case_ref,
            'status':          self.status,
            'verification_type': self.verification_type,
            'full_name':       self.full_name,
            'date_of_birth':   self.date_of_birth,
            'id_number':       self.id_number,
            'address':         self.address,
            'citizenship_no':  self.citizenship_no,
            'ocr_confidence':  round(self.ocr_confidence or 0, 3),
            'face_match_score':round(self.face_match_score or 0, 3),
            'overall_score':   round(self.overall_score or 0, 3),
            'is_flagged':      self.is_flagged,
            'created_at':      self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id         = db.Column(db.Integer, primary_key=True)
    case_id    = db.Column(db.Integer, db.ForeignKey('kyc_requests.id'), nullable=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action     = db.Column(db.String(100), nullable=False)
    detail     = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentRecord(db.Model):
    __tablename__ = 'student_records'
    id               = db.Column(db.Integer, primary_key=True)
    kyc_request_id   = db.Column(db.Integer, db.ForeignKey('kyc_requests.id'))
    institution_name = db.Column(db.String(200))
    student_id       = db.Column(db.String(50))
    program          = db.Column(db.String(200))
    enrollment_year  = db.Column(db.String(10))
    expected_grad    = db.Column(db.String(10))
    verified         = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## PART 5 — APP FACTORY

### app/extensions.py
```python
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
bcrypt = Bcrypt()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
```

### app/__init__.py
```python
import os
from flask import Flask
from config import Config
from app.extensions import db, login_manager, migrate, bcrypt, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(f"{app.config['UPLOAD_FOLDER']}/ids", exist_ok=True)
    os.makedirs(f"{app.config['UPLOAD_FOLDER']}/selfies", exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.views import main_bp
    from app.routes.kyc import kyc_bp
    from app.routes.student import student_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(kyc_bp, url_prefix='/kyc')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('pages/errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('pages/errors/500.html'), 500

    return app
```

### run.py
```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

---

## PART 6 — OCR SERVICE (CORE ENGINE)

### app/services/ocr_service.py
```python
import os
import re
from google.cloud import vision


def extract_national_id(image_path: str) -> dict:
    """
    Extract all fields from Nepal National ID card using Google Vision OCR.
    Returns structured dict with confidence score.
    """
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", "google_vision.json"
    )

    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image    = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts    = response.text_annotations

    if not texts:
        return {
            "success":     False,
            "error":       "No text detected in image",
            "confidence":  0.0,
        }

    # Full raw text
    full_text = texts[0].description
    lines     = [line.strip() for line in full_text.split('\n') if line.strip()]

    # Extract fields using regex patterns for Nepal National ID
    result = {
        "success":        True,
        "raw_text":       full_text,
        "full_name":      None,
        "date_of_birth":  None,
        "id_number":      None,
        "address":        None,
        "citizenship_no": None,
        "issue_date":     None,
        "issue_district": None,
        "confidence":     0.0,
    }

    # Name — usually after "Name:" or "नाम:" or all caps line
    name_pattern = re.compile(r'(?:Name|नाम)[:\s]+([A-Za-z\s]+)', re.IGNORECASE)
    for line in lines:
        m = name_pattern.search(line)
        if m:
            result["full_name"] = m.group(1).strip()
            break

    # Fallback: look for all-caps English name line
    if not result["full_name"]:
        for line in lines:
            if re.match(r'^[A-Z][A-Z\s]{5,40}$', line):
                result["full_name"] = line.strip()
                break

    # DOB — various formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
    dob_pattern = re.compile(
        r'(?:DOB|D\.O\.B|Date of Birth|जन्म मिति)[:\s]*'
        r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})',
        re.IGNORECASE
    )
    for line in lines:
        m = dob_pattern.search(line)
        if m:
            result["date_of_birth"] = m.group(1).strip()
            break

    # Fallback: any date-like pattern
    if not result["date_of_birth"]:
        date_re = re.compile(r'\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b')
        for line in lines:
            m = date_re.search(line)
            if m:
                result["date_of_birth"] = m.group(1)
                break

    # Citizenship / ID Number
    cit_pattern = re.compile(
        r'(?:Citizenship No|नागरिकता न|ID No|ID Number)[.:\s]*([0-9\-\/]+)',
        re.IGNORECASE
    )
    for line in lines:
        m = cit_pattern.search(line)
        if m:
            result["citizenship_no"] = m.group(1).strip()
            result["id_number"]      = result["citizenship_no"]
            break

    # Fallback: numeric pattern like 12-34-567890
    if not result["id_number"]:
        id_re = re.compile(r'\b(\d{2}[-/]\d{2}[-/]\d{5,8})\b')
        for line in lines:
            m = id_re.search(line)
            if m:
                result["id_number"] = m.group(1)
                break

    # Address
    addr_pattern = re.compile(
        r'(?:Address|ठेगाना|Permanent Address)[:\s]+(.+)',
        re.IGNORECASE
    )
    for line in lines:
        m = addr_pattern.search(line)
        if m:
            result["address"] = m.group(1).strip()
            break

    # Issue district
    district_pattern = re.compile(
        r'(?:Issued by|Issue District|जिल्ला)[:\s]+([A-Za-z\s]+)',
        re.IGNORECASE
    )
    for line in lines:
        m = district_pattern.search(line)
        if m:
            result["issue_district"] = m.group(1).strip()
            break

    # Issue date
    issue_pattern = re.compile(
        r'(?:Issue Date|जारी मिति)[:\s]*(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})',
        re.IGNORECASE
    )
    for line in lines:
        m = issue_pattern.search(line)
        if m:
            result["issue_date"] = m.group(1).strip()
            break

    # Confidence score — based on how many fields extracted
    extracted = sum(1 for k in ["full_name","date_of_birth","id_number","address"]
                    if result.get(k))
    result["confidence"] = round(extracted / 4, 2)

    return result


def extract_student_id(image_path: str) -> dict:
    """
    Extract fields from a student ID card.
    """
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", "google_vision.json"
    )

    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image    = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts    = response.text_annotations

    if not texts:
        return {"success": False, "error": "No text detected", "confidence": 0.0}

    full_text = texts[0].description
    lines     = [l.strip() for l in full_text.split('\n') if l.strip()]

    result = {
        "success":          True,
        "raw_text":         full_text,
        "institution_name": None,
        "student_name":     None,
        "student_id":       None,
        "program":          None,
        "enrollment_year":  None,
        "confidence":       0.0,
    }

    # Institution name — usually first large text
    if lines:
        result["institution_name"] = lines[0]

    # Student ID
    sid_re = re.compile(r'(?:Student ID|Roll No|ID)[:\s]*([A-Z0-9\/\-]+)', re.IGNORECASE)
    for line in lines:
        m = sid_re.search(line)
        if m:
            result["student_id"] = m.group(1).strip()
            break

    # Name
    name_re = re.compile(r'(?:Name|Student Name)[:\s]+([A-Za-z\s]+)', re.IGNORECASE)
    for line in lines:
        m = name_re.search(line)
        if m:
            result["student_name"] = m.group(1).strip()
            break

    # Program
    prog_re = re.compile(r'(?:Program|Course|Faculty)[:\s]+(.+)', re.IGNORECASE)
    for line in lines:
        m = prog_re.search(line)
        if m:
            result["program"] = m.group(1).strip()
            break

    extracted = sum(1 for k in ["institution_name","student_name","student_id","program"]
                    if result.get(k))
    result["confidence"] = round(extracted / 4, 2)
    return result
```

---

## PART 7 — FACE MATCHING SERVICE

### app/services/face_service.py
```python
import os
import cv2
import numpy as np
from PIL import Image


def compare_faces_simple(id_image_path: str, selfie_path: str) -> dict:
    """
    Simple face comparison using OpenCV histogram method.
    No dlib required. Returns match score 0.0 to 1.0.
    """
    try:
        img1 = cv2.imread(id_image_path)
        img2 = cv2.imread(selfie_path)

        if img1 is None or img2 is None:
            return {"success": False, "score": 0.0, "error": "Could not read image"}

        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Detect faces using OpenCV Haar Cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        faces1 = face_cascade.detectMultiScale(gray1, 1.1, 4)
        faces2 = face_cascade.detectMultiScale(gray2, 1.1, 4)

        if len(faces1) == 0 or len(faces2) == 0:
            return {
                "success": True,
                "score":   0.3,
                "message": "Face not clearly detected — manual review recommended"
            }

        # Crop first face from each
        x1,y1,w1,h1 = faces1[0]
        x2,y2,w2,h2 = faces2[0]

        face1 = cv2.resize(gray1[y1:y1+h1, x1:x1+w1], (100,100))
        face2 = cv2.resize(gray2[y2:y2+h2, x2:x2+w2], (100,100))

        # Compare histograms
        hist1 = cv2.calcHist([face1],[0],None,[256],[0,256])
        hist2 = cv2.calcHist([face2],[0],None,[256],[0,256])
        cv2.normalize(hist1,hist1); cv2.normalize(hist2,hist2)

        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        score = max(0.0, min(1.0, float(score)))

        return {
            "success": True,
            "score":   round(score, 3),
            "message": "Match successful" if score > 0.6 else "Low confidence match"
        }

    except Exception as e:
        return {"success": False, "score": 0.0, "error": str(e)}
```

---

## PART 8 — KYC ROUTES

### app/routes/kyc.py
```python
import os
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import KYCRequest, AuditLog
from app.services.ocr_service import extract_national_id
from app.services.face_service import compare_faces_simple

kyc_bp = Blueprint('kyc', __name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@kyc_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        id_file = request.files.get('id_image')
        selfie  = request.files.get('selfie')

        if not id_file or not allowed_file(id_file.filename):
            flash('Please upload a valid National ID image (JPG/PNG).', 'danger')
            return render_template('pages/kyc/upload.html')

        # Create case
        case = KYCRequest(
            user_id    = current_user.id,
            company_id = current_user.company_id,
            status     = 'processing',
            verification_type = 'kyc'
        )
        db.session.add(case)
        db.session.flush()

        # Save ID image
        upload_dir = current_app.config['UPLOAD_FOLDER']
        id_dir     = os.path.join(upload_dir, 'ids')
        os.makedirs(id_dir, exist_ok=True)

        id_filename = f"id_{case.id}_{secrets.token_hex(4)}.jpg"
        id_path     = os.path.join(id_dir, id_filename)
        id_file.save(id_path)
        case.id_image_path = id_path

        # Save selfie if provided
        selfie_path = None
        if selfie and allowed_file(selfie.filename):
            selfie_dir      = os.path.join(upload_dir, 'selfies')
            os.makedirs(selfie_dir, exist_ok=True)
            selfie_filename = f"selfie_{case.id}_{secrets.token_hex(4)}.jpg"
            selfie_path     = os.path.join(selfie_dir, selfie_filename)
            selfie.save(selfie_path)
            case.selfie_path = selfie_path

        # Run OCR
        ocr_result = extract_national_id(id_path)

        if ocr_result.get('success'):
            case.full_name      = ocr_result.get('full_name')
            case.date_of_birth  = ocr_result.get('date_of_birth')
            case.id_number      = ocr_result.get('id_number')
            case.address        = ocr_result.get('address')
            case.citizenship_no = ocr_result.get('citizenship_no')
            case.issue_date     = ocr_result.get('issue_date')
            case.issue_district = ocr_result.get('issue_district')
            case.ocr_confidence = ocr_result.get('confidence', 0.0)
            case.raw_ocr_data   = {'raw_text': ocr_result.get('raw_text', '')}

        # Run face match if selfie provided
        face_score = 0.0
        if selfie_path:
            face_result = compare_faces_simple(id_path, selfie_path)
            face_score  = face_result.get('score', 0.0)
            case.face_match_score = face_score

        # Calculate overall score
        ocr_weight  = 0.6
        face_weight = 0.4
        case.overall_score = round(
            (case.ocr_confidence * ocr_weight) + (face_score * face_weight), 3
        )

        # Auto-decide status
        if case.overall_score >= 0.75:
            case.status = 'verified'
        elif case.overall_score >= 0.5:
            case.status = 'manual_review'
        else:
            case.status = 'rejected'

        db.session.commit()

        # Audit log
        log = AuditLog(
            case_id    = case.id,
            user_id    = current_user.id,
            action     = 'kyc_submitted',
            detail     = f'OCR confidence: {case.ocr_confidence}, Face: {face_score}',
            ip_address = request.remote_addr
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
    page   = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query  = KYCRequest.query
    if current_user.role not in ['admin']:
        query = query.filter_by(company_id=current_user.company_id)
    if status:
        query = query.filter_by(status=status)
    cases = query.order_by(KYCRequest.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('pages/kyc/cases.html', cases=cases, status=status)


@kyc_bp.route('/case/<int:case_id>/flag', methods=['POST'])
@login_required
def flag_case(case_id):
    case   = KYCRequest.query.get_or_404(case_id)
    reason = request.form.get('reason', '')
    case.is_flagged  = not case.is_flagged
    case.flag_reason = reason if case.is_flagged else None
    log = AuditLog(case_id=case.id, user_id=current_user.id,
                   action='flagged' if case.is_flagged else 'unflagged',
                   detail=reason, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    flash(f'Case {case.case_ref} {"flagged" if case.is_flagged else "unflagged"}.', 'warning')
    return redirect(url_for('kyc.result', case_id=case.id))
```

---

## PART 9 — STUDENT VERIFICATION ROUTES

### app/routes/student.py
```python
import os
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
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
        student_id  = request.files.get('student_id')
        selfie      = request.files.get('selfie')

        if not national_id or not student_id:
            flash('Please upload both National ID and Student ID.', 'danger')
            return render_template('pages/student/verify.html')

        case = KYCRequest(
            user_id    = current_user.id,
            company_id = current_user.company_id,
            status     = 'processing',
            verification_type = 'student'
        )
        db.session.add(case)
        db.session.flush()

        upload_dir = current_app.config['UPLOAD_FOLDER']

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
            case.full_name     = nid_result.get('full_name')
            case.date_of_birth = nid_result.get('date_of_birth')
            case.id_number     = nid_result.get('id_number')
            case.address       = nid_result.get('address')
            case.ocr_confidence = nid_result.get('confidence', 0.0)

        # OCR student ID
        sid_result = extract_student_id(sid_path)
        if sid_result.get('success'):
            case.institution_name = sid_result.get('institution_name')
            case.student_id       = sid_result.get('student_id')
            case.program          = sid_result.get('program')
            case.enrollment_year  = sid_result.get('enrollment_year')

        # Face match
        face_score = 0.0
        if selfie_path:
            face_result   = compare_faces_simple(nid_path, selfie_path)
            face_score    = face_result.get('score', 0.0)
            case.face_match_score = face_score

        case.overall_score = round(
            (case.ocr_confidence * 0.5) + (face_score * 0.5), 3
        )

        case.status = 'verified' if case.overall_score >= 0.65 else (
            'manual_review' if case.overall_score >= 0.4 else 'rejected'
        )

        # Save student record
        student = StudentRecord(
            kyc_request_id   = case.id,
            institution_name = case.institution_name,
            student_id       = case.student_id,
            program          = case.program,
            enrollment_year  = case.enrollment_year,
            verified         = (case.status == 'verified')
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
```

---

## PART 10 — DASHBOARD ROUTES (REAL DATA)

### app/routes/dashboard.py
```python
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import KYCRequest, User, Company, APIKey, AuditLog
from app.extensions import db
from sqlalchemy import func
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        return admin()
    elif current_user.role == 'company_admin':
        return company()
    return user_dashboard()


@dashboard_bp.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        return render_template('pages/errors/403.html'), 403

    total_cases     = KYCRequest.query.count()
    verified_cases  = KYCRequest.query.filter_by(status='verified').count()
    pending_cases   = KYCRequest.query.filter_by(status='pending').count()
    rejected_cases  = KYCRequest.query.filter_by(status='rejected').count()
    flagged_cases   = KYCRequest.query.filter_by(is_flagged=True).count()
    total_users     = User.query.count()
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
        'total_cases':     total_cases,
        'verified_cases':  verified_cases,
        'pending_cases':   pending_cases,
        'rejected_cases':  rejected_cases,
        'flagged_cases':   flagged_cases,
        'total_users':     total_users,
        'total_companies': total_companies,
        'success_rate':    round((verified_cases / total_cases * 100), 1) if total_cases > 0 else 0,
        'trend_data':      trend_data,
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

    total   = KYCRequest.query.filter_by(company_id=current_user.company_id).count()
    verified = KYCRequest.query.filter_by(
        company_id=current_user.company_id, status='verified'
    ).count()

    stats = {
        'total':    total,
        'verified': verified,
        'success_rate': round((verified / total * 100), 1) if total > 0 else 0,
    }

    return render_template('pages/dashboards/company.html',
                           company=company,
                           api_keys=api_keys,
                           cases=cases,
                           stats=stats)


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
        return jsonify({'error': 'Unauthorized'}), 403

    key = APIKey(
        company_id = current_user.company_id,
        name       = request.form.get('name', 'API Key')
    )
    db.session.add(key)
    db.session.commit()
    return jsonify({'key': key.key, 'name': key.name, 'id': key.id})


@dashboard_bp.route('/api-keys/<int:key_id>/revoke', methods=['POST'])
@login_required
def revoke_api_key(key_id):
    key = APIKey.query.get_or_404(key_id)
    if key.company_id != current_user.company_id and current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    key.is_active = False
    db.session.commit()
    return jsonify({'success': True})
```

---

## PART 11 — REST API ROUTES

### app/routes/api.py
```python
from functools import wraps
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models import APIKey, KYCRequest, Company
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
        'status':  'operational',
        'service': 'NagarikAPI',
        'version': '1.0.0',
        'endpoints': {
            'kyc_submit':    'POST /api/v1/kyc',
            'kyc_retrieve':  'GET  /api/v1/kyc/<case_ref>',
            'kyc_list':      'GET  /api/v1/kyc',
            'student_verify':'POST /api/v1/student',
        }
    })


@api_bp.route('/kyc', methods=['POST'])
@require_api_key
def submit_kyc():
    """Submit KYC via API — multipart form with id_image and selfie files"""
    from flask import current_app
    from werkzeug.utils import secure_filename
    from app.services.ocr_service import extract_national_id
    from app.services.face_service import compare_faces_simple
    import os, secrets

    id_file = request.files.get('id_image')
    selfie  = request.files.get('selfie')

    if not id_file:
        return jsonify({'error': 'id_image file is required'}), 400

    case = KYCRequest(
        company_id        = request.api_key.company_id,
        status            = 'processing',
        verification_type = 'kyc'
    )
    db.session.add(case); db.session.flush()

    upload_dir = current_app.config['UPLOAD_FOLDER']
    id_path    = os.path.join(upload_dir, 'ids', f"api_id_{case.id}.jpg")
    os.makedirs(os.path.dirname(id_path), exist_ok=True)
    id_file.save(id_path)
    case.id_image_path = id_path

    selfie_path = None
    if selfie:
        selfie_path = os.path.join(upload_dir, 'selfies', f"api_selfie_{case.id}.jpg")
        os.makedirs(os.path.dirname(selfie_path), exist_ok=True)
        selfie.save(selfie_path)
        case.selfie_path = selfie_path

    ocr = extract_national_id(id_path)
    if ocr.get('success'):
        case.full_name      = ocr.get('full_name')
        case.date_of_birth  = ocr.get('date_of_birth')
        case.id_number      = ocr.get('id_number')
        case.address        = ocr.get('address')
        case.citizenship_no = ocr.get('citizenship_no')
        case.ocr_confidence = ocr.get('confidence', 0.0)

    face_score = 0.0
    if selfie_path:
        face_result = compare_faces_simple(id_path, selfie_path)
        face_score  = face_result.get('score', 0.0)
        case.face_match_score = face_score

    case.overall_score = round((case.ocr_confidence * 0.6) + (face_score * 0.4), 3)
    case.status = (
        'verified'      if case.overall_score >= 0.75 else
        'manual_review' if case.overall_score >= 0.5  else
        'rejected'
    )
    db.session.commit()

    return jsonify({
        'success':  True,
        'case_ref': case.case_ref,
        'status':   case.status,
        'data':     case.to_dict()
    }), 201


@api_bp.route('/kyc/<case_ref>', methods=['GET'])
@require_api_key
def get_kyc(case_ref):
    case = KYCRequest.query.filter_by(case_ref=case_ref).first()
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    if (case.company_id != request.api_key.company_id and
            current_user.role != 'admin' if hasattr(request,'user') else False):
        return jsonify({'error': 'Access denied'}), 403
    return jsonify(case.to_dict())


@api_bp.route('/kyc', methods=['GET'])
@require_api_key
def list_kyc():
    page   = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    query  = KYCRequest.query.filter_by(company_id=request.api_key.company_id)
    if status:
        query = query.filter_by(status=status)
    cases = query.order_by(KYCRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return jsonify({
        'cases': [c.to_dict() for c in cases.items],
        'total': cases.total,
        'page':  cases.page,
        'pages': cases.pages,
    })


@api_bp.route('/student', methods=['POST'])
@require_api_key
def submit_student():
    """Submit student verification via API"""
    from flask import current_app
    from app.services.ocr_service import extract_student_id, extract_national_id
    from app.services.face_service import compare_faces_simple
    from app.models import StudentRecord
    import os

    national_id = request.files.get('national_id')
    student_id  = request.files.get('student_id')

    if not national_id or not student_id:
        return jsonify({'error': 'national_id and student_id files required'}), 400

    case = KYCRequest(
        company_id=request.api_key.company_id,
        status='processing',
        verification_type='student'
    )
    db.session.add(case); db.session.flush()

    upload_dir = current_app.config['UPLOAD_FOLDER']
    nid_path = os.path.join(upload_dir,'ids',f"api_nid_{case.id}.jpg")
    sid_path = os.path.join(upload_dir,'ids',f"api_sid_{case.id}.jpg")
    os.makedirs(os.path.dirname(nid_path), exist_ok=True)

    national_id.save(nid_path); student_id.save(sid_path)
    case.id_image_path = nid_path

    nid_ocr = extract_national_id(nid_path)
    sid_ocr = extract_student_id(sid_path)

    if nid_ocr.get('success'):
        case.full_name      = nid_ocr.get('full_name')
        case.id_number      = nid_ocr.get('id_number')
        case.ocr_confidence = nid_ocr.get('confidence', 0.0)

    if sid_ocr.get('success'):
        case.institution_name = sid_ocr.get('institution_name')
        case.student_id       = sid_ocr.get('student_id')
        case.program          = sid_ocr.get('program')

    case.overall_score = round(
        ((nid_ocr.get('confidence',0) + sid_ocr.get('confidence',0)) / 2), 3
    )
    case.status = 'verified' if case.overall_score >= 0.6 else 'manual_review'

    student = StudentRecord(
        kyc_request_id=case.id,
        institution_name=case.institution_name,
        student_id=case.student_id,
        program=case.program,
        verified=(case.status=='verified')
    )
    db.session.add(student)
    db.session.commit()

    return jsonify({'success':True,'case_ref':case.case_ref,
                    'status':case.status,'data':case.to_dict()}), 201
```

---

## PART 12 — AUTH ROUTES

### app/routes/auth.py
```python
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        email    = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        remember = bool(request.form.get('remember'))
        user     = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        flash('Invalid email or password.', 'danger')
    return render_template('pages/auth/login.html')


@auth_bp.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        full_name = request.form.get('full_name','').strip()
        email     = request.form.get('email','').strip().lower()
        password  = request.form.get('password','')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('pages/auth/register.html')
        user = User(full_name=full_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('pages/auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
```

---

## PART 13 — DATABASE SETUP

Run this once to create all tables:

```python
# create_tables.py — run once, then delete
from app import create_app
from app.extensions import db
from app.models import User, Company, APIKey, KYCRequest, AuditLog, StudentRecord

app = create_app()
with app.app_context():
    db.create_all()
    print("All tables created.")

    # Create default admin user
    admin = User.query.filter_by(email='admin@nagarikapi.com').first()
    if not admin:
        admin = User(
            full_name = 'System Admin',
            email     = 'admin@nagarikapi.com',
            role      = 'admin'
        )
        admin.set_password('Admin@2025!')
        db.session.add(admin)

    # Create demo company
    demo_company = Company.query.filter_by(
        registration_number='NRB-DEMO-001'
    ).first()
    if not demo_company:
        demo_company = Company(
            name                = 'Demo Bank Nepal',
            type                = 'bank',
            registration_number = 'NRB-DEMO-001'
        )
        db.session.add(demo_company)
        db.session.flush()

        # Create API key for demo company
        api_key = APIKey(
            company_id = demo_company.id,
            name       = 'Demo Key'
        )
        db.session.add(api_key)

    db.session.commit()
    print(f"Admin: admin@nagarikapi.com / Admin@2025!")
    if demo_company:
        key = APIKey.query.filter_by(company_id=demo_company.id).first()
        if key:
            print(f"Demo API Key: {key.key}")
```

Run it:
```bash
python create_tables.py
```

---

## PART 14 — API INTEGRATION GUIDE FOR INSTITUTIONS

### How to integrate NagarikAPI

#### Step 1 — Get your API Key
Contact NagarikAPI or register your institution at `/auth/register`.
Your API key will be available in your company dashboard.

#### Step 2 — KYC Verification Request
```bash
curl -X POST https://your-domain.com/api/v1/kyc \
  -H "X-API-Key: your_api_key_here" \
  -F "id_image=@/path/to/national_id.jpg" \
  -F "selfie=@/path/to/selfie.jpg"
```

**Response:**
```json
{
  "success": true,
  "case_ref": "KYC-A3F2B1",
  "status": "verified",
  "data": {
    "full_name": "Ram Bahadur Thapa",
    "date_of_birth": "1990-05-15",
    "id_number": "12-34-567890",
    "address": "Kathmandu, Bagmati",
    "ocr_confidence": 0.85,
    "face_match_score": 0.78,
    "overall_score": 0.82
  }
}
```

#### Step 3 — Retrieve a Case
```bash
curl -X GET https://your-domain.com/api/v1/kyc/KYC-A3F2B1 \
  -H "X-API-Key: your_api_key_here"
```

#### Step 4 — Student Verification
```bash
curl -X POST https://your-domain.com/api/v1/student \
  -H "X-API-Key: your_api_key_here" \
  -F "national_id=@national_id.jpg" \
  -F "student_id=@student_card.jpg"
```

#### Status Codes
| Status | Meaning |
|---|---|
| `verified` | Score ≥ 75% — auto-approved |
| `manual_review` | Score 50–74% — human review needed |
| `rejected` | Score < 50% — failed verification |
| `pending` | Not yet processed |

---

## PART 15 — RUN THE APP

```bash
# Activate venv
venv\Scripts\activate

# Run
python run.py
```

Visit:
- `http://localhost:5000` — Landing page
- `http://localhost:5000/auth/login` — Login
- `http://localhost:5000/kyc/upload` — KYC upload
- `http://localhost:5000/student/verify` — Student verification
- `http://localhost:5000/dashboard` — Dashboard
- `http://localhost:5000/api/v1/status` — API status

**Default admin login:**
- Email: `admin@nagarikapi.com`
- Password: `Admin@2025!`

---

## PART 16 — QUICK CHECKLIST

- [ ] All files created as per structure
- [ ] `pip install -r requirements.txt` done
- [ ] `.env` filled with real credentials
- [ ] `google_vision.json` in project root
- [ ] `python create_tables.py` run — tables created + admin user created
- [ ] `python run.py` — app starts with no errors
- [ ] Visit `/api/v1/status` — returns operational JSON
- [ ] Login as admin — dashboard loads with real DB data
- [ ] Upload a National ID — OCR extracts fields
- [ ] API key generated from dashboard — test with curl
- [ ] Student verification flow works end to end

---

*NagarikAPI — Built for Nepal's identity infrastructure.*
*Coventry University · Softwarica College · AI39B Group 5*