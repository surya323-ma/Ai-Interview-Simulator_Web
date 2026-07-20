"""
Face Analysis Module (Web) - Server-side analysis of webcam frames posted
from the browser. Uses the MediaPipe Tasks FaceLandmarker (face_landmarker.task)
instead of the legacy mp.solutions.face_mesh used by the desktop version, and
is stateless per call: per-session accumulation (history, running stats) is
kept by the caller in a small dict so it works safely across concurrent users.

The scoring math (eye contact, stability) mirrors the original desktop
face_analysis.py so results stay consistent with the rest of the project.
"""

import base64
import threading

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

MODEL_PATH = "static/models/face_landmarker.task"

# Landmark indices (same as the desktop version)
NOSE_TIP = 4
CHIN = 152
LEFT_EYE = 33
RIGHT_EYE = 263

HISTORY_SIZE = 30

_lock = threading.Lock()
_landmarker = None


def _get_landmarker():
    """Lazily create a single FaceLandmarker instance for this process."""
    global _landmarker
    if _landmarker is None:
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
        )
        _landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    return _landmarker


def decode_data_url(data_url):
    """Decode a `data:image/jpeg;base64,...` string into a BGR numpy frame."""
    if not data_url:
        return None
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(data_url)
    except Exception:
        return None
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


def new_face_stats():
    """A fresh per-question accumulator, mirrors the desktop version's dict."""
    return {
        'total_frames': 0,
        'face_detected_frames': 0,
        'eye_contact_frames': 0,
        'position_history': [],
        'last_stability': 50,
    }


def analyze_frame(frame, stats):
    """
    Run face analysis on a single BGR frame and fold the result into `stats`
    (mutated in place). Returns a small dict suitable for a live overlay.
    """
    result = {
        'face_detected': False,
        'eye_contact': 0,
        'stability': stats.get('last_stability', 50),
        'head_pose': {'yaw': 0, 'pitch': 0, 'roll': 0},
    }

    stats['total_frames'] += 1

    if frame is None:
        return result

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    with _lock:
        landmarker = _get_landmarker()
        detection = landmarker.detect(mp_image)

    if not detection.face_landmarks:
        return result

    landmarks = detection.face_landmarks[0]
    result['face_detected'] = True
    stats['face_detected_frames'] += 1

    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    face_center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)

    position_history = stats['position_history']
    position_history.append(face_center)
    if len(position_history) > HISTORY_SIZE:
        position_history.pop(0)

    # Head pose (simplified estimation, matches the desktop version)
    nose = landmarks[NOSE_TIP]
    chin = landmarks[CHIN]
    left_eye = landmarks[LEFT_EYE]
    right_eye = landmarks[RIGHT_EYE]

    eye_center_x = (left_eye.x + right_eye.x) / 2
    yaw = (nose.x - eye_center_x) * 100

    eye_center_y = (left_eye.y + right_eye.y) / 2
    denom = (chin.y - eye_center_y) or 1e-6
    vertical_ratio = (nose.y - eye_center_y) / denom
    pitch = (vertical_ratio - 0.4) * 100

    roll = float(np.degrees(np.arctan2(right_eye.y - left_eye.y, right_eye.x - left_eye.x)))

    result['head_pose'] = {'yaw': float(yaw), 'pitch': float(pitch), 'roll': roll}

    # Eye contact score: blend of centered-ness and how frontal the pose is
    dx = face_center[0] - 0.5
    dy = face_center[1] - 0.5
    dist_from_center = (dx ** 2 + dy ** 2) ** 0.5
    position_score = max(0, 100 - dist_from_center * 150)

    yaw_penalty = abs(yaw) * 2
    pitch_penalty = abs(pitch) * 1.5
    roll_penalty = abs(roll) * 0.5
    pose_score = max(0, 100 - yaw_penalty - pitch_penalty - roll_penalty)

    eye_contact = position_score * 0.4 + pose_score * 0.6
    result['eye_contact'] = eye_contact
    if eye_contact > 60:
        stats['eye_contact_frames'] += 1

    # Stability from variance of recent positions
    if len(position_history) >= 5:
        xs_h = [p[0] for p in position_history]
        ys_h = [p[1] for p in position_history]
        variance = float(np.var(xs_h) + np.var(ys_h))
        stability = max(0.0, min(100.0, 100 - variance * 5000))
        stats['last_stability'] = stability
        result['stability'] = stability

    return result


def get_session_stats(stats):
    """Aggregate stats for the question, same shape as the desktop version."""
    total = stats.get('total_frames', 0)
    if total == 0:
        return {
            'face_detection_rate': 0,
            'eye_contact_rate': 0,
            'average_stability': 0,
        }
    return {
        'face_detection_rate': (stats['face_detected_frames'] / total) * 100,
        'eye_contact_rate': (stats['eye_contact_frames'] / total) * 100,
        'average_stability': stats.get('last_stability', 50),
    }
