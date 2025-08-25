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

    # --- If a target is provided, perform Color Histogram Matching ---

    # Decode the target image and calculate its histogram
    target_bytes = base64.b64decode(target_img_data)
    target_nparr = np.frombuffer(target_bytes, np.uint8)
    target_img = cv2.imdecode(target_nparr, cv2.IMREAD_COLOR)
    if target_img is None: return main_img, 0

    target_hsv = cv2.cvtColor(target_img, cv2.COLOR_BGR2HSV)
    # Create a mask for the target image to ignore black/transparent pixels from the lasso crop
    target_mask = cv2.inRange(target_hsv, (0, 1, 1), (180, 255, 255))
    target_hist = cv2.calcHist([target_hsv], [0, 1], target_mask, [32, 32], [0, 180, 0, 256])
    cv2.normalize(target_hist, target_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    # Find all contours in the main image
    main_hsv = cv2.cvtColor(main_img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > 100]

    match_count = 0
    for contour in contours:
        # Create a mask for the current contour
        mask = np.zeros(gray.shape, dtype="uint8")
        cv2.drawContours(mask, [contour], -1, 255, -1)

        # Calculate histogram for the masked region of interest
        roi_hist = cv2.calcHist([main_hsv], [0, 1], mask, [32, 32], [0, 180, 0, 256])
        cv2.normalize(roi_hist, roi_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

        # Compare histograms
        color_similarity = cv2.compareHist(target_hist, roi_hist, cv2.HISTCMP_CORREL)

        if color_similarity > 0.5: # Lowered threshold for more lenient real-world matching
            match_count += 1
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(main_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return main_img, match_count

if __name__ == '__main__':
    app.run(debug=True)
