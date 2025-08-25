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
        # Create a test image: black bg, two red squares, one blue square
        self.test_image_path = "test_image.png"
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        # Red squares
        cv2.rectangle(img, (20, 20), (60, 60), (0, 0, 255), -1)
        cv2.rectangle(img, (20, 120), (60, 160), (0, 0, 255), -1)
        # Blue square
        cv2.rectangle(img, (120, 20), (160, 60), (255, 0, 0), -1)
        cv2.imwrite(self.test_image_path, img)

    def tearDown(self):
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)

    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_get_target_at_coords(self):
        with open(self.test_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Coords for the first red square
        payload = {'image': 'data:image/png;base64,' + image_data, 'x': 0.2, 'y': 0.2}
        response = self.app.post('/get_target_at_coords', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('target_image', data)
        self.assertIsNotNone(data['target_image'])

    def test_process_frame_count_all(self):
        with open(self.test_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        payload = {'image': 'data:image/png;base64,' + image_data}
        response = self.app.post('/process_frame', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['count'], 3) # Should find all 3 squares

    def test_process_frame_count_matches(self):
        # 1. Get the target image data first (the first red square)
        with open(self.test_image_path, "rb") as f:
            image_data_b64 = base64.b64encode(f.read()).decode('utf-8')

        get_target_payload = {'image': 'data:image/png;base64,' + image_data_b64, 'x': 0.2, 'y': 0.2}
        response = self.app.post('/get_target_at_coords', data=json.dumps(get_target_payload), content_type='application/json')
        target_data = json.loads(response.data)
        red_square_target_b64 = target_data['target_image']
        self.assertIsNotNone(red_square_target_b64)

        # 2. Now, process the full frame using the obtained target
        process_payload = {
            'image': 'data:image/png;base64,' + image_data_b64,
            'target_image': red_square_target_b64
        }
        response = self.app.post('/process_frame', data=json.dumps(process_payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('count', data)
        # This is the crucial test: it should find the two red squares
        self.assertEqual(data['count'], 2)

if __name__ == '__main__':
    unittest.main()
