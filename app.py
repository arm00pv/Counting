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

    # Get selection coordinates if they exist
    x = data.get('x')
    y = data.get('y')

    # Decode the base64 image
    img_bytes = base64.b64decode(image_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Process the image for object counting
    processed_image, count = process_image(img, x, y)

    # Encode the processed image to base64
    _, buffer = cv2.imencode('.jpg', processed_image)
    processed_image_b64 = base64.b64encode(buffer).decode('utf-8')

    return jsonify({'image': processed_image_b64, 'count': count})


def process_image(img, sel_x=None, sel_y=None):
    # Basic image processing to find contours
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, \
                                   cv2.THRESH_BINARY_INV, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter out small contours to reduce noise
    contours = [c for c in contours if cv2.contourArea(c) > 100]

    # If no selection, just count all filtered contours
    if sel_x is None or sel_y is None:
        for contour in contours:
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return img, len(contours)

    # --- If there is a selection, perform matching ---

    # Convert relative selection coordinates to absolute
    abs_x = int(sel_x * img.shape[1])
    abs_y = int(sel_y * img.shape[0])

    # Find the selected contour
    target_contour = None
    for contour in contours:
        if cv2.pointPolygonTest(contour, (abs_x, abs_y), False) >= 0:
            target_contour = contour
            break

    if target_contour is None:
        return img, 0 # Click was not on any detected object

    # Convert image to HSV for better color analysis
    hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Calculate histogram of the target object
    target_mask = np.zeros(img.shape[:2], np.uint8)
    cv2.drawContours(target_mask, [target_contour], -1, 255, -1)
    target_hist = cv2.calcHist([hsv_img], [0, 1], target_mask, [180, 256], [0, 180, 0, 256])
    cv2.normalize(target_hist, target_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    matched_contours = []
    # Compare target histogram with all other objects
    for contour in contours:
        current_mask = np.zeros(img.shape[:2], np.uint8)
        cv2.drawContours(current_mask, [contour], -1, 255, -1)
        current_hist = cv2.calcHist([hsv_img], [0, 1], current_mask, [180, 256], [0, 180, 0, 256])
        cv2.normalize(current_hist, current_hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

        similarity = cv2.compareHist(target_hist, current_hist, cv2.HISTCMP_CORREL)

        if similarity > 0.85: # Similarity threshold
            matched_contours.append(contour)

    # Draw rectangles on the matched objects
    for c in matched_contours:
        (x, y, w, h) = cv2.boundingRect(c)
        if np.array_equal(c, target_contour):
             cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 3) # Blue, thicker
        else:
             cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2) # Green

    return img, len(matched_contours)

if __name__ == '__main__':
    app.run(debug=True)
