"""
Simple KYC Verification Example with NagarikAPI

This example demonstrates how to perform KYC verification using the NagarikAPI.
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api/v1")
API_KEY = os.getenv("NAGARIK_API_KEY", "your-api-key-here")


def verify_kyc(nid_image_path: str, selfie_image_path: str = None) -> dict:
    """
    Perform KYC verification using NagarikAPI.
    
    Args:
        nid_image_path: Path to the National ID image file
        selfie_image_path: Path to the selfie image file (optional)
        
    Returns:
        Verification result as a dictionary
    """
    url = f"{API_BASE_URL}/kyc/verify"
    
    # Prepare the files for upload
    files = {
        "nid_image": open(nid_image_path, "rb")
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
        raise Exception(f"KYC verification failed: {str(e)}")


def get_verification_status(case_ref: str) -> dict:
    """
    Get the status of a KYC verification case.
    
    Args:
        case_ref: Case reference ID
        
    Returns:
        Case status as a dictionary
    """
    url = f"{API_BASE_URL}/kyc/case/{case_ref}"
    
    headers = {
        "X-API-Key": API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get verification status: {str(e)}")


if __name__ == "__main__":
    # Example usage
    print("NagarikAPI KYC Verification Example")
    print("=" * 50)
    
    # Replace these with actual image paths
    NID_IMAGE_PATH = "path/to/nid_image.jpg"
    SELFIE_IMAGE_PATH = "path/to/selfie.jpg"  # Optional
    
    try:
        # Perform KYC verification
        print("\n1. Performing KYC verification...")
        result = verify_kyc(NID_IMAGE_PATH, SELFIE_IMAGE_PATH)
        
        print("\nVerification Result:")
        print(f"Case Reference: {result['case_ref']}")
        print(f"Status: {result['status']}")
        
        if result.get('extracted_data'):
            print("\nExtracted Data:")
            data = result['extracted_data']
            if data.get('full_name'):
                print(f"Name: {data['full_name']}")
            if data.get('id_number'):
                print(f"NID Number: {data['id_number']}")
            if data.get('date_of_birth'):
                print(f"Date of Birth: {data['date_of_birth']}")
        
        print("\n✅ KYC verification initiated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
