const API_BASE_URL = "https://api.nagarikapi.com/v1";

class NIDScanner {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.stream = null;
        this.capturedImage = null;
        
        this.startBtn = document.getElementById('startBtn');
        this.captureBtn = document.getElementById('captureBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.verifyBtn = document.getElementById('verifyBtn');
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        this.startBtn.addEventListener('click', () => this.startCamera());
        this.captureBtn.addEventListener('click', () => this.captureImage());
        this.stopBtn.addEventListener('click', () => this.stopCamera());
        this.verifyBtn.addEventListener('click', () => this.verifyWithAPI());
    }
    
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            this.video.srcObject = this.stream;
            
            // Set canvas size to match video
            this.video.addEventListener('loadedmetadata', () => {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
            });
            
            this.startBtn.disabled = true;
            this.captureBtn.disabled = false;
            this.stopBtn.disabled = false;
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Could not access camera. Please make sure you have granted camera permissions.');
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
            this.video.srcObject = null;
            
            this.startBtn.disabled = false;
            this.captureBtn.disabled = true;
            this.stopBtn.disabled = true;
        }
    }
    
    captureImage() {
        // Draw the current video frame to the canvas
        this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // Convert canvas to blob
        this.canvas.toBlob((blob) => {
            this.capturedImage = blob;
            
            // Simulate OCR extraction (in real use, this would be done via the API)
            this.simulateOCR();
            
            this.verifyBtn.disabled = false;
            
        }, 'image/jpeg', 0.9);
    }
    
    simulateOCR() {
        // This is just a demo - in real use, you'd send the image to NagarikAPI
        // to get actual OCR results
        
        // Fill with dummy data for demo purposes
        document.getElementById('fullName').textContent = 'John Doe';
        document.getElementById('idNumber').textContent = '1234567890123';
        document.getElementById('dob').textContent = '1990-01-15';
        document.getElementById('address').textContent = 'Kathmandu, Nepal';
    }
    
    async verifyWithAPI() {
        if (!this.capturedImage) {
            alert('Please capture an image first');
            return;
        }
        
        // Get API key from user
        const apiKey = prompt('Enter your NagarikAPI key:');
        if (!apiKey) {
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('nid_image', this.capturedImage, 'nid.jpg');
            
            const response = await fetch(`${API_BASE_URL}/kyc/verify`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${apiKey}`
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Verification failed');
            }
            
            const result = await response.json();
            
            alert(`Verification complete!\nCase Reference: ${result.case_ref}\nStatus: ${result.status}`);
            
            // Update the UI with actual API results if available
            if (result.extracted_data) {
                if (result.extracted_data.full_name) {
                    document.getElementById('fullName').textContent = result.extracted_data.full_name;
                }
                if (result.extracted_data.id_number) {
                    document.getElementById('idNumber').textContent = result.extracted_data.id_number;
                }
                if (result.extracted_data.date_of_birth) {
                    document.getElementById('dob').textContent = result.extracted_data.date_of_birth;
                }
                if (result.extracted_data.address) {
                    document.getElementById('address').textContent = result.extracted_data.address;
                }
            }
            
        } catch (error) {
            console.error('Verification error:', error);
            alert('Verification failed: ' + error.message);
        }
    }
}

// Initialize the scanner when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new NIDScanner();
});
