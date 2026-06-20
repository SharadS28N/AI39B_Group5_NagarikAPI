"""
Webhook Example for NagarikAPI

This example demonstrates how to set up a webhook server to receive
verification results from NagarikAPI.
"""

from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Webhook secret (get this from your NagarikAPI dashboard)
WEBHOOK_SECRET = os.getenv("NAGARIK_WEBHOOK_SECRET", "your-webhook-secret-here")


@app.route("/webhook/nagarikapi", methods=["POST"])
def nagarikapi_webhook():
    """
    Handle webhook events from NagarikAPI.
    """
    # Verify the webhook signature (optional but recommended)
    signature = request.headers.get("X-NagarikAPI-Signature")
    if signature:
        # TODO: Implement signature verification
        pass
    
    # Get the event data
    event_data = request.json
    
    if not event_data:
        return jsonify({"error": "Invalid request"}), 400
    
    # Process the event
    event_type = event_data.get("event_type")
    
    print(f"Received event: {event_type}")
    print(f"Data: {event_data}")
    
    if event_type == "kyc.verified":
        # Handle KYC verification success
        case_ref = event_data["data"]["case_ref"]
        print(f"✅ KYC verified: {case_ref}")
        
    elif event_type == "kyc.failed":
        # Handle KYC verification failure
        case_ref = event_data["data"]["case_ref"]
        print(f"❌ KYC failed: {case_ref}")
        
    elif event_type == "student.verified":
        # Handle student verification success
        case_ref = event_data["data"]["case_ref"]
        print(f"✅ Student verified: {case_ref}")
        
    elif event_type == "student.failed":
        # Handle student verification failure
        case_ref = event_data["data"]["case_ref"]
        print(f"❌ Student verification failed: {case_ref}")
        
    else:
        # Handle other event types
        print(f"Unhandled event: {event_type}")
    
    # Return a success response
    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    print("NagarikAPI Webhook Server")
    print("=" * 50)
    print(f"Listening for webhook events at: http://localhost:5001/webhook/nagarikapi")
    print("\n⚠️  For production, use a proper WSGI server like Gunicorn or uWSGI")
    print("⚠️  Make sure to set up your webhook URL in your NagarikAPI dashboard\n")
    
    # Run on port 5001 to avoid conflict with main NagarikAPI server
    app.run(port=5001, debug=True)
