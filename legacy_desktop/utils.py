"""
Utility functions for the AI Interview Simulator
"""

import time
import cv2
import numpy as np

# Colors (BGR format for OpenCV)
COLORS = {
    'white': (255, 255, 255),
    'black': (0, 0, 0),
    'green': (0, 255, 0),
    'red': (0, 0, 255),
    'blue': (255, 0, 0),
    'yellow': (0, 255, 255),
    'cyan': (255, 255, 0),
    'orange': (0, 165, 255),
    'purple': (255, 0, 255),
    'gray': (128, 128, 128),
    'dark_gray': (50, 50, 50),
    'light_gray': (200, 200, 200),
}

def draw_text_with_background(frame, text, position, font_scale=0.7, 
                               color=COLORS['white'], bg_color=COLORS['dark_gray'],
                               thickness=2, padding=10):
    """Draw text with a background rectangle."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    x, y = position
    # Draw background rectangle
    cv2.rectangle(frame, 
                  (x - padding, y - text_height - padding),
                  (x + text_width + padding, y + baseline + padding),
                  bg_color, -1)
    # Draw text
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)
    
    return text_height + baseline + 2 * padding

def draw_multiline_text(frame, text, position, max_width, font_scale=0.6,
                        color=COLORS['white'], bg_color=COLORS['dark_gray'],
                        thickness=1, line_spacing=10, padding=15):
    """Draw multi-line text that wraps within max_width."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    words = text.split(' ')
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        (width, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
        if width <= max_width - 2 * padding:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    x, y = position
    total_height = 0
    max_line_width = 0
    
    # Calculate dimensions
    for line in lines:
        (w, h), baseline = cv2.getTextSize(line, font, font_scale, thickness)
        total_height += h + line_spacing
        max_line_width = max(max_line_width, w)
    
    # Draw background
    cv2.rectangle(frame,
                  (x - padding, y - padding),
                  (x + max_line_width + padding, y + total_height + padding),
                  bg_color, -1)
    
    # Draw border
    cv2.rectangle(frame,
                  (x - padding, y - padding),
                  (x + max_line_width + padding, y + total_height + padding),
                  COLORS['cyan'], 2)
    
    # Draw text lines
    current_y = y
    for line in lines:
        (_, h), baseline = cv2.getTextSize(line, font, font_scale, thickness)
        current_y += h
        cv2.putText(frame, line, (x, current_y), font, font_scale, color, thickness)
        current_y += line_spacing
    
    return total_height + 2 * padding

def draw_progress_bar(frame, position, size, progress, color=COLORS['green'], 
                      bg_color=COLORS['dark_gray'], border_color=COLORS['white']):
    """Draw a progress bar."""
    x, y = position
    width, height = size
    
    # Background
    cv2.rectangle(frame, (x, y), (x + width, y + height), bg_color, -1)
    
    # Progress
    progress_width = int(width * min(1.0, max(0.0, progress)))
    if progress_width > 0:
        cv2.rectangle(frame, (x, y), (x + progress_width, y + height), color, -1)
    
    # Border
    cv2.rectangle(frame, (x, y), (x + width, y + height), border_color, 2)

def draw_timer(frame, position, time_left, total_time):
    """Draw a countdown timer with visual indicator."""
    x, y = position
    progress = time_left / total_time if total_time > 0 else 0
    
    # Color changes based on time left
    if progress > 0.5:
        color = COLORS['green']
    elif progress > 0.25:
        color = COLORS['yellow']
    else:
        color = COLORS['red']
    
    # Draw circular progress indicator
    radius = 40
    thickness = 8
    angle = int(360 * progress)
    
    # Background circle
    cv2.circle(frame, (x, y), radius, COLORS['dark_gray'], -1)
    
    # Progress arc
    if angle > 0:
        cv2.ellipse(frame, (x, y), (radius - 4, radius - 4), -90, 0, angle, color, thickness)
    
    # Time text
    time_text = f"{int(time_left)}s"
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(time_text, font, 0.7, 2)
    cv2.putText(frame, time_text, (x - tw // 2, y + th // 2), font, 0.7, COLORS['white'], 2)

def draw_score_indicator(frame, position, score, label, max_score=100):
    """Draw a score indicator with label."""
    x, y = position
    
    # Determine color based on score
    if score >= 70:
        color = COLORS['green']
    elif score >= 40:
        color = COLORS['yellow']
    else:
        color = COLORS['red']
    
    # Draw label
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, label, (x, y), font, 0.5, COLORS['white'], 1)
    
    # Draw progress bar
    bar_y = y + 10
    draw_progress_bar(frame, (x, bar_y), (120, 15), score / max_score, color)
    
    # Draw score text
    score_text = f"{int(score)}%"
    cv2.putText(frame, score_text, (x + 130, bar_y + 12), font, 0.5, color, 1)

def format_time(seconds):
    """Format seconds to MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

class FPSCounter:
    """Simple FPS counter for performance monitoring."""
    
    def __init__(self, avg_frames=30):
        self.avg_frames = avg_frames
        self.times = []
        self.last_time = time.time()
    
    def update(self):
        current_time = time.time()
        self.times.append(current_time - self.last_time)
        self.last_time = current_time
        
        if len(self.times) > self.avg_frames:
            self.times.pop(0)
    
    def get_fps(self):
        if not self.times:
            return 0
        avg_time = sum(self.times) / len(self.times)
        return 1.0 / avg_time if avg_time > 0 else 0
