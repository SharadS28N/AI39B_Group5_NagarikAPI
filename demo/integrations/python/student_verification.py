"""
Student Verification Example with NagarikAPI

This example demonstrates how to verify student status using the NagarikAPI.
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")
API_KEY = os.getenv("NAGARIK_API_KEY", "your-api-key-here")


def verify_student(nid_image_path: str, student_id_image_path: str, selfie_image_path: str = None) -> dict:
    """
    Perform student verification using NagarikAPI.
    
    Args:
        nid_image_path: Path to the National ID image file
        student_id_image_path: Path to the Student ID image file
        selfie_image_path: Path to the selfie image file (optional)
        
    Returns:
        Verification result as a dictionary
    """
    url = f"{API_BASE_URL}/student/verify"
    
    # Prepare the files for upload
    files = {
        "nid_image": open(nid_image_path, "rb"),
        "student_id": open(student_id_image_path, "rb")
    }
    
    if selfie_image_path:
        files["selfie"] = open(selfie_image_path, "rb")
    
    # Set up headers - use X-API-Key as per our API implementation
    headers = {
        "X-API-Key": API_KEY
    }
    
    try:
        # Send the request
        response = requests.post(url, files=files, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Close the files
        for file in files.values():
            file.close()
            
        return response.json()
    except requests.exceptions.RequestException as e:
        # Close the files before raising
        for file in files.values():
            file.close()
        raise Exception(f"Student verification failed: {str(e)}")


if __name__ == "__main__":
    # Example usage
    print("NagarikAPI Student Verification Example")
    print("=" * 50)
    
    # Replace these with actual image paths
    NID_IMAGE_PATH = "path/to/nid_image.jpg"
    STUDENT_ID_PATH = "path/to/student_id.jpg"
    SELFIE_IMAGE_PATH = "path/to/selfie.jpg"  # Optional
    
    try:
        # Perform student verification
        print("\n1. Performing student verification...")
        result = verify_student(NID_IMAGE_PATH, STUDENT_ID_PATH, SELFIE_IMAGE_PATH)
        
        print("\nVerification Result:")
        print(f"Case Reference: {result['case_ref']}")
        print(f"Status: {result['status']}")
        
        if result.get('student_data'):
            print("\nStudent Data:")
            student = result['student_data']
            if student.get('institution_name'):
                print(f"Institution: {student['institution_name']}")
            if student.get('student_id'):
                print(f"Student ID: {student['student_id']}")
            if student.get('program'):
                print(f"Program: {student['program']}")
            if student.get('enrollment_year'):
                print(f"Enrollment Year: {student['enrollment_year']}")
        
        print("\n✅ Student verification initiated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
