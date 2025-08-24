import unittest
import os
import cv2
import numpy as np
from app import app, process_image

class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Create a dummy image file for testing
        self.test_image_path = "test_image.jpg"
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(self.test_image_path, dummy_image)

    def tearDown(self):
        os.remove(self.test_image_path)
        # Clean up uploaded files
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            # Check if the path is a file before attempting to remove it
            if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))


    def test_upload_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Object Counter', response.data)

    def test_upload_file(self):
        with open(self.test_image_path, "rb") as f:
            response = self.app.post('/', data={'file': f}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Processed Image', response.data)

    def test_process_image(self):
        processed_filename, count = process_image(self.test_image_path)
        self.assertIsInstance(processed_filename, str)
        self.assertIsInstance(count, int)
        # Check that the processed file was created
        self.assertTrue(os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)))


if __name__ == '__main__':
    unittest.main()
