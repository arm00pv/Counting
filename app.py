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

    # Decode the base64 image
    img_bytes = base64.b64decode(image_data)

    # Save the captured frame to a file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'capture.jpg')
    with open(filepath, 'wb') as f:
        f.write(img_bytes)

    # Process the image for object counting
    processed_image, count = process_image(filepath)

    # Encode the processed image to base64
    _, buffer = cv2.imencode('.jpg', processed_image)
    processed_image_b64 = base64.b64encode(buffer).decode('utf-8')

    return jsonify({'image': processed_image_b64, 'count': count})


def process_image(filepath):
    # Read the image
    img = cv2.imread(filepath)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply thresholding to get a binary image
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw contours and count objects
    for contour in contours:
        # Filter out small contours
        if cv2.contourArea(contour) > 100:
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    count = len(contours)

    return img, count

if __name__ == '__main__':
    app.run(debug=True)
