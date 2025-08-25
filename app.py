# Backend server for the computer vision web app
from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import os
import base64

app = Flask(__name__)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_frame', methods=['POST'])
def process_frame():
    data = request.get_json()
    image_data = data['image'].split(',')[1]
    target_image_data = data.get('target_image')

    img_bytes = base64.b64decode(image_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    processed_image, count = process_image(img, target_image_data)

    _, buffer = cv2.imencode('.jpg', processed_image)
    processed_image_b64 = base64.b64encode(buffer).decode('utf-8')

    return jsonify({'image': processed_image_b64, 'count': count})

def process_image(main_img, target_img_data=None):
    # First, find all potential objects (contours) in the main image.
    gray = cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if 100 < cv2.contourArea(c) < 20000]

    # If no target is provided, this is a "Count All" request.
    if target_img_data is None:
        for contour in contours:
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(main_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return main_img, len(contours)

    # --- If a target is provided, filter contours by color ---

    # Decode the target image and find its average color
    target_bytes = base64.b64decode(target_img_data)
    target_nparr = np.frombuffer(target_bytes, np.uint8)
    target_img = cv2.imdecode(target_nparr, cv2.IMREAD_COLOR)
    if target_img is None: return main_img, 0

    target_hsv = cv2.cvtColor(target_img, cv2.COLOR_BGR2HSV)
    # Calculate the average color of the non-black pixels in the target
    # This is more robust if the cropped target has black padding
    mask = cv2.inRange(target_hsv, (0, 1, 1), (180, 255, 255))
    target_avg_color = cv2.mean(target_hsv, mask=mask)[:3]

    main_hsv = cv2.cvtColor(main_img, cv2.COLOR_BGR2HSV)
    matched_contours = []

    for contour in contours:
        # Create a mask for the current contour and find its average color
        mask = np.zeros(gray.shape, dtype="uint8")
        cv2.drawContours(mask, [contour], -1, 255, -1)
        roi_avg_color = cv2.mean(main_hsv, mask=mask)[:3]

        # Calculate the distance between the target color and the ROI color
        # We give Hue more weight as it's the most important for color identity
        hue_diff = min(abs(target_avg_color[0] - roi_avg_color[0]), 180 - abs(target_avg_color[0] - roi_avg_color[0]))
        sat_diff = abs(target_avg_color[1] - roi_avg_color[1])

        # This is a simple distance metric. Thresholds can be tuned.
        # Lower score is a better match.
        color_distance = (hue_diff * 2) + (sat_diff * 0.1)

        if color_distance < 25: # Color distance threshold
            matched_contours.append(contour)

    # Draw boxes on the final matched contours
    for contour in matched_contours:
        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(main_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return main_img, len(matched_contours)

if __name__ == '__main__':
    app.run(debug=True)
