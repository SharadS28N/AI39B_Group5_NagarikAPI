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
                "score": 0.3,
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
        cv2.normalize(hist1,hist1)
        cv2.normalize(hist2,hist2)

        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        score = max(0.0, min(1.0, float(score)))

        return {
            "success": True,
            "score": round(score, 3),
            "message": "Match successful" if score > 0.6 else "Low confidence match"
        }

    except Exception as e:
        return {"success": False, "score": 0.0, "error": str(e)}
