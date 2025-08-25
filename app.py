# Backend server for the computer vision web app
from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import os
import base64

import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import torch.nn as nn

# --- Feature Extractor Class ---
class FeatureExtractor:
    def __init__(self):
        # Use a pre-trained ResNet-18 model
        # Using weights instead of pretrained=True for newer torchvision versions
        self.model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        # Remove the final classification layer
        self.model = nn.Sequential(*list(self.model.children())[:-1])
        # Set to evaluation mode
        self.model.eval()

        # Define the image transformations
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def extract_features(self, img):
        # Convert OpenCV image (BGR) to PIL image (RGB)
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
        except cv2.error:
            return None # Handle cases where the image is invalid

        # Apply transformations and get the feature vector
        img_t = self.transform(pil_img)
        batch_t = torch.unsqueeze(img_t, 0)

        with torch.no_grad():
            features = self.model(batch_t)

        # Flatten the features to a 1D vector and convert to numpy
        return features.squeeze().numpy()

# Instantiate the feature extractor once when the app starts
feature_extractor = FeatureExtractor()

# --- Flask App ---
app = Flask(__name__)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    data = request.get_json()
    image_data = data['image'].split(',')[1]
    target_image_data = data.get('target_image')
    threshold = data.get('threshold', 0.8)

    img_bytes = base64.b64decode(image_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    processed_image, count = process_image(img, target_image_data, threshold)

    _, buffer = cv2.imencode('.jpg', processed_image)
    processed_image_b64 = base64.b64encode(buffer).decode('utf-8')

    return jsonify({'image': processed_image_b64, 'count': count})

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def process_image(main_img, target_img_data=None, threshold=0.8):
    # If no target, perform a general count
    if target_img_data is None:
        gray = cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [c for c in contours if cv2.contourArea(c) > 100]
        for contour in contours:
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(main_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return main_img, len(contours)

    # --- If a target is provided, perform Deep Learning Feature Matching ---

    # Decode the target image and extract its features
    target_bytes = base64.b64decode(target_img_data)
    target_nparr = np.frombuffer(target_bytes, np.uint8)
    target_img = cv2.imdecode(target_nparr, cv2.IMREAD_COLOR)
    if target_img is None: return main_img, 0

    target_features = feature_extractor.extract_features(target_img)
    if target_features is None: return main_img, 0

    # Find all contours in the main image
    gray = cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > 100]

    match_count = 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Crop the region of interest (ROI) from the main image
        roi = main_img[y:y+h, x:x+w]

        # Extract features from the ROI
        roi_features = feature_extractor.extract_features(roi)
        if roi_features is None: continue

        # Compare feature vectors using cosine similarity
        similarity = cosine_similarity(target_features, roi_features)

        if similarity > threshold:
            match_count += 1
            cv2.rectangle(main_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return main_img, match_count

if __name__ == '__main__':
    app.run(debug=True)
