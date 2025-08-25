import unittest
from unittest.mock import patch
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
        self.img = np.zeros((200, 200, 3), dtype=np.uint8)
        # Red squares
        cv2.rectangle(self.img, (20, 20), (60, 60), (0, 0, 255), -1)
        cv2.rectangle(self.img, (20, 120), (60, 160), (0, 0, 255), -1)
        # Blue square
        cv2.rectangle(self.img, (120, 20), (160, 60), (255, 0, 0), -1)
        cv2.imwrite(self.test_image_path, self.img)

    def tearDown(self):
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)

    def test_index_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_process_frame_count_all(self):
        with open(self.test_image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        payload = {'image': 'data:image/png;base64,' + image_data}
        response = self.app.post('/process_frame', data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['count'], 3)

    @patch('app.feature_extractor.extract_features')
    def test_process_frame_count_matches_mocked(self, mock_extract_features):
        # Define the mock return values
        # A, B, C are arbitrary feature vectors. A and B are identical.
        vec_A = np.array([1.0, 0.0, 0.0])
        vec_B = np.array([1.0, 0.0, 0.0])
        vec_C = np.array([0.0, 1.0, 0.0])

        # The first call is for the target (a red square).
        # The next three calls are for the ROIs found in the main image.
        mock_extract_features.side_effect = [vec_A, vec_A, vec_B, vec_C]

        # 1. Create the target image data (a crop of the first red square)
        target_crop = self.img[20:60, 20:60]
        _, buffer = cv2.imencode('.png', target_crop)
        red_square_target_b64 = base64.b64encode(buffer).decode('utf-8')

        # 2. Create the main image data
        with open(self.test_image_path, "rb") as f:
            image_data_b64 = base64.b64encode(f.read()).decode('utf-8')

        # 3. Send the payload to the backend
        process_payload = {
            'image': 'data:image/png;base64,' + image_data_b64,
            'target_image': red_square_target_b64,
            'threshold': 0.95 # Use a high threshold, since our mock vectors are perfect
        }
        response = self.app.post('/process_frame', data=json.dumps(process_payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('count', data)
        # The mock should result in the two "red" vectors (A and B) matching.
        self.assertEqual(data['count'], 2)
        # Verify that extract_features was called 4 times (1 for target, 3 for ROIs)
        self.assertEqual(mock_extract_features.call_count, 4)


if __name__ == '__main__':
    unittest.main()
