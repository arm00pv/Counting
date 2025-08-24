import unittest
import os
import cv2
import numpy as np
import base64
import json
from app import app

class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Create a dummy image for testing
        self.test_image_path = "test_image.jpg"
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(self.test_image_path, dummy_image)

    def tearDown(self):
        os.remove(self.test_image_path)
        # Clean up uploaded files
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))

    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Object Counter', response.data)

    def test_process_frame(self):
        # Read the dummy image and encode it to base64
        with open(self.test_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        response = self.app.post('/process_frame',
                                 data=json.dumps({'image': 'data:image/jpeg;base64,' + image_data}),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertIn('count', data)
        self.assertIsInstance(data['image'], str)
        self.assertIsInstance(data['count'], int)

if __name__ == '__main__':
    unittest.main()
