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

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if not texts:
        return {
            "success": False,
            "error": "No text detected in image",
            "confidence": 0.0,
        }

    # Full raw text
    full_text = texts[0].description
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]

    # Extract fields using regex patterns for Nepal National ID
    result = {
        "success": True,
        "raw_text": full_text,
        "full_name": None,
        "date_of_birth": None,
        "id_number": None,
        "address": None,
        "citizenship_no": None,
        "issue_date": None,
        "issue_district": None,
        "confidence": 0.0,
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
        r'(?:Citizenship No|नागరికತા నं|ID No|ID Number)[.:\s]*([0-9\-\/]+)',
        re.IGNORECASE
    )
    for line in lines:
        m = cit_pattern.search(line)
        if m:
            result["citizenship_no"] = m.group(1).strip()
            result["id_number"] = result["citizenship_no"]
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

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if not texts:
        return {"success": False, "error": "No text detected", "confidence": 0.0}

    full_text = texts[0].description
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]

    result = {
        "success": True,
        "raw_text": full_text,
        "institution_name": None,
        "student_name": None,
        "student_id": None,
        "program": None,
        "enrollment_year": None,
        "confidence": 0.0,
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
