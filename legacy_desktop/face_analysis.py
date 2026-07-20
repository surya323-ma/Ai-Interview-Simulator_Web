"""
Face Analysis Module - Tracks face position, eye contact, and stability
"""

import cv2
import numpy as np
import time

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("Warning: MediaPipe not available. Face analysis will be limited.")

from utils import COLORS

class FaceAnalyzer:
    """Analyzes face position, eye contact, and stability."""
    
    def __init__(self):
        """Initialize the face analyzer."""
        self.mp_face_mesh = None
        self.mp_drawing = None
        self.face_mesh = None
        
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_drawing = mp.solutions.drawing_utils
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        
        # Tracking data
        self.face_detected = False
        self.face_position = None
        self.face_positions = []  # History for stability calculation
        self.eye_contact_score = 0
        self.stability_score = 0
        self.head_pose = {'yaw': 0, 'pitch': 0, 'roll': 0}
        
        # Stats accumulation
        self.total_frames = 0
        self.face_detected_frames = 0
        self.eye_contact_frames = 0
        self.position_history = []
        
        # Configuration
        self.history_size = 30  # frames
        self.center_threshold = 0.15  # How close to center counts as eye contact
        
    def process_frame(self, frame):
        """Process a frame and return analysis results."""
        self.total_frames += 1
        
        if not MEDIAPIPE_AVAILABLE or self.face_mesh is None:
            return self._fallback_detection(frame)
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        h, w, _ = frame.shape
        
        if results.multi_face_landmarks:
            self.face_detected = True
            self.face_detected_frames += 1
            
            landmarks = results.multi_face_landmarks[0]
            
            # Calculate face bounding box
            x_coords = [lm.x for lm in landmarks.landmark]
            y_coords = [lm.y for lm in landmarks.landmark]
            
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            
            # Face center position (normalized 0-1)
            face_center_x = (x_min + x_max) / 2
            face_center_y = (y_min + y_max) / 2
            
            self.face_position = (face_center_x, face_center_y)
            self.position_history.append(self.face_position)
            
            # Keep history limited
            if len(self.position_history) > self.history_size:
                self.position_history.pop(0)
            
            # Calculate head pose estimation using key landmarks
            self._estimate_head_pose(landmarks, w, h)
            
            # Calculate eye contact score based on face position and head pose
            self._calculate_eye_contact()
            
            # Calculate stability score
            self._calculate_stability()
            
            # Draw face mesh and indicators
            self._draw_face_indicators(frame, landmarks, w, h)
            
        else:
            self.face_detected = False
            self.face_position = None
            self.eye_contact_score = 0
        
        return {
            'face_detected': self.face_detected,
            'eye_contact': self.eye_contact_score,
            'stability': self.stability_score,
            'head_pose': self.head_pose,
            'position': self.face_position
        }
    
    def _fallback_detection(self, frame):
        """Simple face detection fallback using Haar cascades."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Use OpenCV's built-in cascade classifier
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        h, w = frame.shape[:2]
        
        if len(faces) > 0:
            self.face_detected = True
            self.face_detected_frames += 1
            
            # Get the largest face
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x + fw, y + fh), COLORS['green'], 2)
            
            # Calculate normalized position
            face_center_x = (x + fw / 2) / w
            face_center_y = (y + fh / 2) / h
            
            self.face_position = (face_center_x, face_center_y)
            self.position_history.append(self.face_position)
            
            if len(self.position_history) > self.history_size:
                self.position_history.pop(0)
            
            # Simple eye contact estimation
            dist_from_center = ((face_center_x - 0.5) ** 2 + (face_center_y - 0.5) ** 2) ** 0.5
            self.eye_contact_score = max(0, 100 - dist_from_center * 200)
            
            self._calculate_stability()
            
        else:
            self.face_detected = False
            self.eye_contact_score = 0
        
        return {
            'face_detected': self.face_detected,
            'eye_contact': self.eye_contact_score,
            'stability': self.stability_score,
            'head_pose': self.head_pose,
            'position': self.face_position
        }
    
    def _estimate_head_pose(self, landmarks, w, h):
        """Estimate head pose from facial landmarks."""
        # Key landmarks for pose estimation
        nose_tip = landmarks.landmark[4]  # Nose tip
        chin = landmarks.landmark[152]  # Chin
        left_eye = landmarks.landmark[33]  # Left eye inner corner
        right_eye = landmarks.landmark[263]  # Right eye inner corner
        left_mouth = landmarks.landmark[61]  # Left mouth corner
        right_mouth = landmarks.landmark[291]  # Right mouth corner
        
        # Estimate yaw (left-right rotation)
        eye_center_x = (left_eye.x + right_eye.x) / 2
        nose_offset = nose_tip.x - eye_center_x
        self.head_pose['yaw'] = nose_offset * 100  # Simplified estimation
        
        # Estimate pitch (up-down rotation)
        vertical_ratio = (nose_tip.y - (left_eye.y + right_eye.y) / 2) / (chin.y - (left_eye.y + right_eye.y) / 2)
        self.head_pose['pitch'] = (vertical_ratio - 0.4) * 100
        
        # Estimate roll (tilt)
        eye_dy = right_eye.y - left_eye.y
        eye_dx = right_eye.x - left_eye.x
        self.head_pose['roll'] = np.degrees(np.arctan2(eye_dy, eye_dx))
    
    def _calculate_eye_contact(self):
        """Calculate eye contact score based on face position and head pose."""
        if self.face_position is None:
            self.eye_contact_score = 0
            return
        
        # Distance from center (0.5, 0.5)
        dx = self.face_position[0] - 0.5
        dy = self.face_position[1] - 0.5
        dist_from_center = (dx ** 2 + dy ** 2) ** 0.5
        
        # Position score (closer to center = better)
        position_score = max(0, 100 - dist_from_center * 150)
        
        # Head pose score (more frontal = better)
        yaw_penalty = abs(self.head_pose['yaw']) * 2
        pitch_penalty = abs(self.head_pose['pitch']) * 1.5
        roll_penalty = abs(self.head_pose['roll']) * 0.5
        
        pose_score = max(0, 100 - yaw_penalty - pitch_penalty - roll_penalty)
        
        # Combined score
        self.eye_contact_score = (position_score * 0.4 + pose_score * 0.6)
        
        if self.eye_contact_score > 60:
            self.eye_contact_frames += 1
    
    def _calculate_stability(self):
        """Calculate stability score based on position history."""
        if len(self.position_history) < 5:
            self.stability_score = 50  # Not enough data
            return
        
        # Calculate variance in position
        x_positions = [p[0] for p in self.position_history]
        y_positions = [p[1] for p in self.position_history]
        
        x_variance = np.var(x_positions)
        y_variance = np.var(y_positions)
        
        total_variance = x_variance + y_variance
        
        # Convert to score (less movement = higher score)
        # Scale factor tuned for typical webcam view
        self.stability_score = max(0, min(100, 100 - total_variance * 5000))
    
    def _draw_face_indicators(self, frame, landmarks, w, h):
        """Draw face mesh and analysis indicators on frame."""
        # Draw a simplified face outline
        face_outline_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                                 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                                 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
        
        # Draw face outline
        outline_points = []
        for idx in face_outline_indices:
            if idx < len(landmarks.landmark):
                lm = landmarks.landmark[idx]
                outline_points.append((int(lm.x * w), int(lm.y * h)))
        
        if len(outline_points) > 2:
            pts = np.array(outline_points, np.int32)
            
            # Color based on eye contact score
            if self.eye_contact_score > 70:
                color = COLORS['green']
            elif self.eye_contact_score > 40:
                color = COLORS['yellow']
            else:
                color = COLORS['red']
            
            cv2.polylines(frame, [pts], True, color, 2)
        
        # Draw eye contact indicator
        nose = landmarks.landmark[4]
        nose_x, nose_y = int(nose.x * w), int(nose.y * h)
        
        # Small indicator above nose
        indicator_text = "Looking" if self.eye_contact_score > 60 else "Look here"
        cv2.putText(frame, indicator_text, (nose_x - 30, nose_y - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['white'], 1)
    
    def get_session_stats(self):
        """Get statistics for the entire session."""
        if self.total_frames == 0:
            return {
                'face_detection_rate': 0,
                'eye_contact_rate': 0,
                'average_stability': 0
            }
        
        return {
            'face_detection_rate': (self.face_detected_frames / self.total_frames) * 100,
            'eye_contact_rate': (self.eye_contact_frames / self.total_frames) * 100,
            'average_stability': self.stability_score
        }
    
    def reset_stats(self):
        """Reset session statistics."""
        self.total_frames = 0
        self.face_detected_frames = 0
        self.eye_contact_frames = 0
        self.position_history = []
    
    def release(self):
        """Release resources."""
        if self.face_mesh:
            self.face_mesh.close()
