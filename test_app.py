import unittest
import os
import cv2
import numpy as np
import base64
import json
from app import app, process_image

class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Create a dummy image for testing (black bg with a red and blue square)
        self.test_image_path = "test_image.png"
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.rectangle(img, (20, 20), (80, 80), (0, 0, 255), -1) # Red square
        cv2.rectangle(img, (120, 120), (180, 180), (255, 0, 0), -1) # Blue square
        cv2.imwrite(self.test_image_path, img)

    def tearDown(self):
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)

    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Object Counter', response.data)

    def test_process_frame(self):
        # Test general processing without selection
        with open(self.test_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        response = self.app.post('/process_frame',
                                 data=json.dumps({'image': 'data:image/png;base64,' + image_data}),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 2) # Should find 2 objects

    def test_process_image(self):
        # Test the image processing function directly (general count)
        img = cv2.imread(self.test_image_path)
        processed_image, count = process_image(img)
        self.assertIsInstance(processed_image, np.ndarray)
        self.assertEqual(count, 2)

    def test_process_frame_with_selection(self):
        # Test processing with selection
        with open(self.test_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Coordinates for the red square (50,50) -> (0.25, 0.25)
        payload = {
            'image': 'data:image/png;base64,' + image_data,
            'x': 0.25,
            'y': 0.25
        }

        response = self.app.post('/process_frame',
                                 data=json.dumps(payload),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 1) # Should only find the red square


if __name__ == '__main__':
    unittest.main()
