"""Unit tests for pure computer-vision analysis functions (EAR, MAR, Head Pose, Face Selection).

All tests are deterministic and do not require camera hardware or live video streams.
"""

import math
import unittest
from dataclasses import dataclass

from app.ai.analysis import (
    Point2D,
    calculate_ear,
    calculate_eye_aspect_ratio,
    calculate_mar,
    estimate_head_pose_geometric,
    extract_features_from_landmarks,
    select_driver_face,
    LEFT_EYE_INDICES,
    RIGHT_EYE_INDICES,
    MOUTH_CORNER_LEFT,
    MOUTH_CORNER_RIGHT,
    MOUTH_VERTICAL_PAIRS,
)


@dataclass
class MockFace:
    landmark: list


class TestAnalysisMath(unittest.TestCase):
    def setUp(self):
        # Create a blank landmark array with 468 points
        self.landmarks = [Point2D(x=0.5, y=0.5, z=0.0) for _ in range(468)]

    def _setup_eye(self, indices, p0, p1, p2, p3, p4, p5):
        """Helper to populate the 6 eye points: [p0, p1, p2, p3, p4, p5]."""
        pts = [p0, p1, p2, p3, p4, p5]
        for idx, pt in zip(indices, pts):
            self.landmarks[idx] = Point2D(x=pt[0], y=pt[1])

    def test_ear_wide_open_eyes(self):
        """Wide open eyes should produce an EAR around 0.35 - 0.40."""
        # Horiz width = 0.10 (p0 to p3)
        # Vertical 1 = 0.035 (p1 to p5)
        # Vertical 2 = 0.035 (p2 to p4)
        # EAR = (0.035 + 0.035) / (2 * 0.10) = 0.35
        left_pts = [
            (0.30, 0.40),  # p0: outer corner
            (0.33, 0.38),  # p1: upper outer
            (0.37, 0.38),  # p2: upper inner
            (0.40, 0.40),  # p3: inner corner
            (0.37, 0.415), # p4: lower inner
            (0.33, 0.415), # p5: lower outer
        ]
        self._setup_eye(LEFT_EYE_INDICES, *left_pts)
        self._setup_eye(RIGHT_EYE_INDICES, *left_pts)

        avg_ear, left_ear, right_ear = calculate_ear(self.landmarks)
        self.assertAlmostEqual(left_ear, 0.35, places=2)
        self.assertAlmostEqual(right_ear, 0.35, places=2)
        self.assertAlmostEqual(avg_ear, 0.35, places=2)

    def test_ear_closed_eyes(self):
        """Closed eyes should produce an EAR well below the 0.21 threshold."""
        # Horiz width = 0.10
        # Verticals collapsed to 0.010
        # EAR = (0.010 + 0.010) / (2 * 0.10) = 0.10
        left_pts = [
            (0.30, 0.40),
            (0.33, 0.395),
            (0.37, 0.395),
            (0.40, 0.40),
            (0.37, 0.405),
            (0.33, 0.405),
        ]
        self._setup_eye(LEFT_EYE_INDICES, *left_pts)
        self._setup_eye(RIGHT_EYE_INDICES, *left_pts)

        avg_ear, left_ear, right_ear = calculate_ear(self.landmarks)
        self.assertLess(avg_ear, 0.15)
        self.assertLess(avg_ear, 0.21)

    def test_mar_closed_mouth(self):
        """Closed mouth should produce a low MAR (approx 0.15 - 0.25)."""
        # Corners: x=0.40 and x=0.60 -> width = 0.20
        # Verticals: 0.03 each -> sum = 0.09
        # MAR = 0.09 / (2 * 0.20) = 0.225
        self.landmarks[MOUTH_CORNER_LEFT] = Point2D(x=0.40, y=0.65)
        self.landmarks[MOUTH_CORNER_RIGHT] = Point2D(x=0.60, y=0.65)

        for top, bottom in MOUTH_VERTICAL_PAIRS:
            self.landmarks[top] = Point2D(x=0.50, y=0.635)
            self.landmarks[bottom] = Point2D(x=0.50, y=0.665)

        mar = calculate_mar(self.landmarks)
        self.assertAlmostEqual(mar, 0.225, places=2)
        self.assertLess(mar, 0.40)

    def test_mar_yawn_open_mouth(self):
        """A wide open yawning mouth should produce a high MAR (> 0.60)."""
        # Corners: width = 0.20
        # Verticals: 0.10 each -> sum = 0.30
        # MAR = 0.30 / (2 * 0.20) = 0.75
        self.landmarks[MOUTH_CORNER_LEFT] = Point2D(x=0.40, y=0.65)
        self.landmarks[MOUTH_CORNER_RIGHT] = Point2D(x=0.60, y=0.65)

        for top, bottom in MOUTH_VERTICAL_PAIRS:
            self.landmarks[top] = Point2D(x=0.50, y=0.60)
            self.landmarks[bottom] = Point2D(x=0.50, y=0.70)

        mar = calculate_mar(self.landmarks)
        self.assertAlmostEqual(mar, 0.75, places=2)
        self.assertGreater(mar, 0.60)

    def test_head_pose_facing_forward(self):
        """When face is centered and symmetric, yaw should be near 0 degrees."""
        # Nose centered between eyes
        self.landmarks[1] = Point2D(x=0.50, y=0.50)    # Nose
        self.landmarks[152] = Point2D(x=0.50, y=0.75)  # Chin
        self.landmarks[33] = Point2D(x=0.35, y=0.45)   # Left eye outer
        self.landmarks[263] = Point2D(x=0.65, y=0.45)  # Right eye outer

        yaw, pitch, roll = estimate_head_pose_geometric(self.landmarks)
        self.assertAlmostEqual(yaw, 0.0, delta=2.0)

    def test_head_pose_turned_right(self):
        """When head turns right, nose shifts closer to right eye, resulting in positive yaw."""
        # Left eye: x=0.35, Right eye: x=0.65
        # Nose shifted to x=0.60 (looking right)
        self.landmarks[1] = Point2D(x=0.60, y=0.50)
        self.landmarks[152] = Point2D(x=0.60, y=0.75)
        self.landmarks[33] = Point2D(x=0.35, y=0.45)
        self.landmarks[263] = Point2D(x=0.65, y=0.45)

        yaw, pitch, roll = estimate_head_pose_geometric(self.landmarks)
        self.assertGreater(yaw, 25.0)

    def test_head_pose_turned_left(self):
        """When head turns left, nose shifts closer to left eye, resulting in negative yaw."""
        # Nose shifted to x=0.40 (looking left)
        self.landmarks[1] = Point2D(x=0.40, y=0.50)
        self.landmarks[152] = Point2D(x=0.40, y=0.75)
        self.landmarks[33] = Point2D(x=0.35, y=0.45)
        self.landmarks[263] = Point2D(x=0.65, y=0.45)

        yaw, pitch, roll = estimate_head_pose_geometric(self.landmarks)
        self.assertLess(yaw, -25.0)

    def test_select_driver_face_single(self):
        """When one face is present, select_driver_face returns it."""
        face = MockFace(landmark=self.landmarks)
        selected = select_driver_face([face])
        self.assertIs(selected, face)

    def test_select_driver_face_prefers_larger_closest_face(self):
        """When driver and passenger are visible, chooses the larger centered driver face."""
        # Driver face: centered, bounding box span 0.40 x 0.40
        driver_pts = [Point2D(x=0.3 + (i % 5) * 0.08, y=0.3 + (i // 5) * 0.08) for i in range(25)]
        driver_face = MockFace(landmark=driver_pts)

        # Passenger face: smaller, off in corner, span 0.15 x 0.15
        passenger_pts = [Point2D(x=0.8 + (i % 5) * 0.03, y=0.2 + (i // 5) * 0.03) for i in range(25)]
        passenger_face = MockFace(landmark=passenger_pts)

        selected = select_driver_face([passenger_face, driver_face])
        self.assertIs(selected, driver_face)


if __name__ == "__main__":
    unittest.main()
