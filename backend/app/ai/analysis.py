"""Pure mathematical and computer-vision analysis functions for driver monitoring.

Contains no camera hardware code or persistent state; all functions are
pure, deterministic, and easily unit-testable.

Algorithms:
1. Eye Aspect Ratio (EAR) - Soukupová and Čech formula for eye closure / drowsiness.
2. Mouth Aspect Ratio (MAR) - 3-vertical-pair lip ratio for yawn vs speech detection.
3. 3D Head Pose (Yaw, Pitch, Roll) - Perspective-n-Point / geometric analysis for distraction.
4. Driver Face Selection - Spatial heuristic selecting primary driver when passengers are visible.
"""

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

try:
    import cv2
    import numpy as np
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False


# Standard MediaPipe FaceMesh Landmark Indices
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

# Mouth landmark indices (inner and outer lips)
# 61: left corner, 291: right corner
# 13, 14: upper and lower inner lip center
# 312, 317: upper and lower inner right
# 82, 87: upper and lower inner left
MOUTH_CORNER_LEFT = 61
MOUTH_CORNER_RIGHT = 291
MOUTH_VERTICAL_PAIRS = [
    (13, 14),   # center inner
    (312, 317), # right inner
    (82, 87),   # left inner
]

# 3D Generic Anthropometric Head Model Points (in millimeters)
# Centered at nose bridge / tip
HEAD_MODEL_3D = [
    (0.0, 0.0, 0.0),          # Nose tip (landmark 1)
    (0.0, -330.0, -65.0),     # Chin (landmark 152)
    (-225.0, 170.0, -135.0),  # Left eye outer corner (landmark 33)
    (225.0, 170.0, -135.0),   # Right eye outer corner (landmark 263)
    (-150.0, -150.0, -125.0), # Left mouth corner (landmark 61)
    (150.0, -150.0, -125.0),  # Right mouth corner (landmark 291)
]

HEAD_POSE_LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]


@dataclass
class Point2D:
    x: float
    y: float
    z: float = 0.0


@dataclass
class FrameFeatures:
    ear: float
    left_ear: float
    right_ear: float
    mar: float
    head_yaw: float      # Degrees: positive = looking right, negative = looking left
    head_pitch: float    # Degrees: positive = looking up, negative = looking down
    head_roll: float     # Degrees: tilt
    face_detected: bool


def _euclidean_distance_2d(p1: Any, p2: Any) -> float:
    """Calculates 2D Euclidean distance between two points with .x and .y attributes."""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return math.sqrt(dx * dx + dy * dy)


def calculate_eye_aspect_ratio(landmarks: Sequence[Any], eye_indices: Sequence[int]) -> float:
    """Calculates EAR for a single eye given 6 landmark points [p0, p1, p2, p3, p4, p5].

    Formula:
        EAR = (||p1 - p5|| + ||p2 - p4||) / (2 * ||p0 - p3||)
    """
    if len(eye_indices) != 6:
        raise ValueError("eye_indices must contain exactly 6 landmark indices")

    pts = [landmarks[i] for i in eye_indices]
    vert1 = _euclidean_distance_2d(pts[1], pts[5])
    vert2 = _euclidean_distance_2d(pts[2], pts[4])
    horiz = _euclidean_distance_2d(pts[0], pts[3])

    if horiz <= 1e-6:
        return 0.0

    return (vert1 + vert2) / (2.0 * horiz)


def calculate_ear(landmarks: Sequence[Any]) -> Tuple[float, float, float]:
    """Calculates left EAR, right EAR, and their average for a face."""
    left_ear = calculate_eye_aspect_ratio(landmarks, LEFT_EYE_INDICES)
    right_ear = calculate_eye_aspect_ratio(landmarks, RIGHT_EYE_INDICES)
    avg_ear = (left_ear + right_ear) / 2.0
    return avg_ear, left_ear, right_ear


def calculate_mar(landmarks: Sequence[Any]) -> float:
    """Calculates Mouth Aspect Ratio (MAR) using 3 vertical pairs divided by horizontal mouth width.

    Formula:
        MAR = (||p13 - p14|| + ||p312 - p317|| + ||p82 - p87||) / (2 * ||p61 - p291||)
    """
    p_left = landmarks[MOUTH_CORNER_LEFT]
    p_right = landmarks[MOUTH_CORNER_RIGHT]
    horiz = _euclidean_distance_2d(p_left, p_right)

    if horiz <= 1e-6:
        return 0.0

    vert_sum = sum(
        _euclidean_distance_2d(landmarks[top], landmarks[bottom])
        for top, bottom in MOUTH_VERTICAL_PAIRS
    )

    return vert_sum / (2.0 * horiz)


def estimate_head_pose_geometric(landmarks: Sequence[Any]) -> Tuple[float, float, float]:
    """Pure geometric head pose approximation (fallback when OpenCV solvePnP is unavailable).

    Calculates yaw via relative nose-to-eye horizontal distance ratio.
    """
    nose = landmarks[1]
    left_eye = landmarks[33]
    right_eye = landmarks[263]
    chin = landmarks[152]

    # Horizontal span from nose to eyes
    dist_to_left = abs(nose.x - left_eye.x)
    dist_to_right = abs(nose.x - right_eye.x)
    total_span = dist_to_left + dist_to_right

    if total_span > 1e-6:
        # Negative = turned left, Positive = turned right
        yaw = ((dist_to_left - dist_to_right) / total_span) * 90.0
    else:
        yaw = 0.0

    # Vertical span for pitch approximation (nose height relative to eye-chin axis)
    eye_y = (left_eye.y + right_eye.y) / 2.0
    chin_y = chin.y
    face_height = chin_y - eye_y
    if face_height > 1e-6:
        nose_ratio = (nose.y - eye_y) / face_height
        # Normal nose center is roughly 0.35-0.40 down the face
        pitch = (nose_ratio - 0.38) * 90.0
    else:
        pitch = 0.0

    # Eye tilt for roll
    dx = right_eye.x - left_eye.x
    dy = right_eye.y - left_eye.y
    roll = math.degrees(math.atan2(dy, dx)) if dx != 0 else 0.0

    return yaw, pitch, roll


def estimate_head_pose(
    landmarks: Sequence[Any], image_width: int = 640, image_height: int = 480
) -> Tuple[float, float, float]:
    """Estimates head pose (yaw, pitch, roll) in degrees.

    Uses OpenCV solvePnP when available; falls back cleanly to geometric estimation.
    """
    if not CV_AVAILABLE:
        return estimate_head_pose_geometric(landmarks)

    try:
        image_points = np.array(
            [
                (landmarks[idx].x * image_width, landmarks[idx].y * image_height)
                for idx in HEAD_POSE_LANDMARK_INDICES
            ],
            dtype=np.float64,
        )

        model_points = np.array(HEAD_MODEL_3D, dtype=np.float64)

        focal_length = image_width
        center = (image_width / 2.0, image_height / 2.0)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return estimate_head_pose_geometric(landmarks)

        rotation_matrix, _ = cv2.Rodrigues(rvec)

        # Extract Euler angles from rotation matrix
        sy = math.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            pitch = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            yaw = math.atan2(-rotation_matrix[2, 0], sy)
            roll = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            pitch = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            yaw = math.atan2(-rotation_matrix[2, 0], sy)
            roll = 0.0

        yaw_deg = math.degrees(yaw)
        pitch_deg = math.degrees(pitch)
        roll_deg = math.degrees(roll)

        return yaw_deg, pitch_deg, roll_deg
    except Exception:
        return estimate_head_pose_geometric(landmarks)


def select_driver_face(
    multi_face_landmarks: Sequence[Any], image_width: int = 640, image_height: int = 480
) -> Optional[Any]:
    """Heuristic to select the primary driver face when multiple faces are detected.

    Prioritizes:
    1. Larger bounding box area (driver sits closest to front dashboard camera).
    2. Proximity to horizontal center of driver seat view.
    """
    if not multi_face_landmarks:
        return None

    if len(multi_face_landmarks) == 1:
        return multi_face_landmarks[0]

    best_face = None
    best_score = -1.0

    for face in multi_face_landmarks:
        pts = face.landmark if hasattr(face, 'landmark') else face
        xs = [pt.x for pt in pts]
        ys = [pt.y for pt in pts]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        area = (max_x - min_x) * (max_y - min_y)
        center_x = (min_x + max_x) / 2.0
        center_dist = abs(center_x - 0.5)

        # Score formula: larger area weighted against excessive edge displacement
        score = area * max(0.1, 1.0 - 0.5 * center_dist)

        if score > best_score:
            best_score = score
            best_face = face

    return best_face


def extract_features_from_landmarks(
    landmarks: Sequence[Any], image_width: int = 640, image_height: int = 480
) -> FrameFeatures:
    """Extracts all core monitoring features from a set of face landmarks."""
    avg_ear, left_ear, right_ear = calculate_ear(landmarks)
    mar = calculate_mar(landmarks)
    yaw, pitch, roll = estimate_head_pose(landmarks, image_width, image_height)

    return FrameFeatures(
        ear=round(avg_ear, 3),
        left_ear=round(left_ear, 3),
        right_ear=round(right_ear, 3),
        mar=round(mar, 3),
        head_yaw=round(yaw, 1),
        head_pitch=round(pitch, 1),
        head_roll=round(roll, 1),
        face_detected=True,
    )


def extract_face_bbox(
    landmarks: Sequence[Any], image_width: int, image_height: int
) -> Tuple[int, int, int, int]:
    """Calculates integer pixel bounding box (x1, y1, x2, y2) from landmarks."""
    xs = [pt.x for pt in landmarks]
    ys = [pt.y for pt in landmarks]
    x1 = max(0, int(min(xs) * image_width))
    y1 = max(0, int(min(ys) * image_height))
    x2 = min(image_width, int(max(xs) * image_width))
    y2 = min(image_height, int(max(ys) * image_height))
    return (x1, y1, x2, y2)
