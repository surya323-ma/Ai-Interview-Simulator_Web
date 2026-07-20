#!/usr/bin/env python3
"""
AI Interview Simulator - Main Application
A real-time interview practice tool with face and voice analysis.
"""

import cv2
import numpy as np
import time
import sys
import threading

# Import modules
from question_engine import QuestionEngine, get_role_selection, get_experience_selection, get_num_questions
from face_analysis import FaceAnalyzer
from voice_analysis import VoiceAnalyzer
from feedback import FeedbackGenerator, draw_question_feedback, draw_final_report
from utils import COLORS, draw_text_with_background, draw_multiline_text, draw_timer, draw_score_indicator, FPSCounter

# Application states
STATE_WELCOME = 0
STATE_COUNTDOWN = 1
STATE_QUESTION = 2
STATE_RECORDING = 3
STATE_PROCESSING = 4
STATE_FEEDBACK = 5
STATE_FINAL_REPORT = 6

class InterviewSimulator:
    """Main application class for the AI Interview Simulator."""
    
    def __init__(self, role, experience, num_questions):
        """Initialize the simulator."""
        self.role = role
        self.experience = experience
        self.num_questions = num_questions
        
        # Initialize components
        self.question_engine = QuestionEngine(role, experience, num_questions)
        self.face_analyzer = FaceAnalyzer()
        self.voice_analyzer = VoiceAnalyzer()
        self.feedback_generator = FeedbackGenerator()
        self.fps_counter = FPSCounter()
        
        # State management
        self.state = STATE_WELCOME
        self.state_start_time = time.time()
        
        # Timing
        self.question_time = 45  # seconds per question
        self.countdown_time = 3  # countdown before recording
        self.feedback_display_time = 5  # seconds to show feedback
        
        # Current question data
        self.current_feedback = None
        self.recording_start_time = None
        
        # Face analysis accumulation for current question
        self.question_face_data = {
            'total_frames': 0,
            'face_detected_frames': 0,
            'eye_contact_frames': 0,
            'stability_scores': []
        }
        
        # Window settings
        self.window_name = "AI Interview Simulator"
        self.window_width = 1280
        self.window_height = 720
        
        # Camera
        self.cap = None
        self.frame = None
        
    def initialize_camera(self):
        """Initialize webcam."""
        print("\nInitializing camera...")
        
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            # Try alternative camera indices
            for i in range(1, 4):
                self.cap = cv2.VideoCapture(i)
                if self.cap.isOpened():
                    break
        
        if not self.cap.isOpened():
            print("ERROR: Could not open camera!")
            print("Please check:")
            print("  - Camera is connected")
            print("  - Camera permissions are granted")
            print("  - No other application is using the camera")
            return False
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("Camera initialized successfully!")
        return True
    
    def change_state(self, new_state):
        """Change application state."""
        self.state = new_state
        self.state_start_time = time.time()
        
        if new_state == STATE_QUESTION:
            # Reset face data for new question
            self.question_face_data = {
                'total_frames': 0,
                'face_detected_frames': 0,
                'eye_contact_frames': 0,
                'stability_scores': []
            }
            self.face_analyzer.reset_stats()
            
            # Speak the question
            question = self.question_engine.get_current_question()
            if question:
                self.voice_analyzer.speak_question(question)
        
        elif new_state == STATE_RECORDING:
            self.voice_analyzer.start_recording()
            self.recording_start_time = time.time()
        
        elif new_state == STATE_PROCESSING:
            # Process the recorded answer
            voice_results = self.voice_analyzer.stop_recording()
            face_results = self.face_analyzer.get_session_stats()
            
            # Generate feedback
            self.current_feedback = self.feedback_generator.generate_feedback(
                face_results, 
                voice_results,
                self.question_engine.get_question_number()
            )
            
            # Store answer data
            self.question_engine.store_answer({
                'voice': voice_results,
                'face': face_results,
                'feedback': self.current_feedback
            })
            
            self.change_state(STATE_FEEDBACK)
    
    def get_elapsed_time(self):
        """Get time elapsed in current state."""
        return time.time() - self.state_start_time
    
    def get_remaining_time(self):
        """Get remaining time for current state."""
        elapsed = self.get_elapsed_time()
        
        if self.state == STATE_COUNTDOWN:
            return max(0, self.countdown_time - elapsed)
        elif self.state in [STATE_QUESTION, STATE_RECORDING]:
            return max(0, self.question_time - elapsed)
        elif self.state == STATE_FEEDBACK:
            return max(0, self.feedback_display_time - elapsed)
        return 0
    
    def handle_state_transitions(self):
        """Handle automatic state transitions."""
        if self.state == STATE_WELCOME:
            # Wait for keypress (handled in main loop)
            pass
        
        elif self.state == STATE_COUNTDOWN:
            if self.get_elapsed_time() >= self.countdown_time:
                self.change_state(STATE_RECORDING)
        
        elif self.state == STATE_QUESTION:
            if self.get_elapsed_time() >= 2:  # Brief pause to show question
                self.change_state(STATE_COUNTDOWN)
        
        elif self.state == STATE_RECORDING:
            if self.get_elapsed_time() >= self.question_time:
                self.change_state(STATE_PROCESSING)
        
        elif self.state == STATE_FEEDBACK:
            if self.get_elapsed_time() >= self.feedback_display_time:
                # Move to next question or final report
                if self.question_engine.next_question():
                    self.change_state(STATE_QUESTION)
                else:
                    self.change_state(STATE_FINAL_REPORT)
    
    def draw_ui(self, frame):
        """Draw UI elements based on current state."""
        h, w = frame.shape[:2]
        
        # Draw header bar
        cv2.rectangle(frame, (0, 0), (w, 60), COLORS['dark_gray'], -1)
        
        # Title
        cv2.putText(frame, "AI Interview Simulator", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLORS['cyan'], 2)
        
        # Role and Experience
        info_text = f"{self.role} | {self.experience}"
        cv2.putText(frame, info_text, (w - 300, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['white'], 1)
        
        # Question progress
        q_num = self.question_engine.get_question_number()
        q_total = self.question_engine.get_total_questions()
        progress_text = f"Question {q_num}/{q_total}"
        cv2.putText(frame, progress_text, (w // 2 - 60, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['yellow'], 2)
        
        # Draw FPS
        fps = self.fps_counter.get_fps()
        cv2.putText(frame, f"FPS: {int(fps)}", (w - 100, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['gray'], 1)
        
        # State-specific UI
        if self.state == STATE_WELCOME:
            self._draw_welcome_screen(frame)
        
        elif self.state == STATE_COUNTDOWN:
            self._draw_countdown(frame)
        
        elif self.state == STATE_QUESTION:
            self._draw_question(frame)
        
        elif self.state == STATE_RECORDING:
            self._draw_recording(frame)
        
        elif self.state == STATE_FEEDBACK:
            self._draw_feedback(frame)
        
        elif self.state == STATE_FINAL_REPORT:
            report = self.feedback_generator.get_final_report(
                self.role, self.experience, self.num_questions
            )
            draw_final_report(frame, report)
        
        return frame
    
    def _draw_welcome_screen(self, frame):
        """Draw welcome screen."""
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 60), (w, h), (30, 30, 40), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        
        # Welcome text
        welcome_text = "Welcome to Your Interview!"
        (tw, _), _ = cv2.getTextSize(welcome_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
        cv2.putText(frame, welcome_text, ((w - tw) // 2, h // 2 - 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLORS['cyan'], 2)
        
        # Role info
        role_text = f"Position: {self.role}"
        (rw, _), _ = cv2.getTextSize(role_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.putText(frame, role_text, ((w - rw) // 2, h // 2 - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['white'], 2)
        
        level_text = f"Level: {self.experience}"
        (lw, _), _ = cv2.getTextSize(level_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.putText(frame, level_text, ((w - lw) // 2, h // 2 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['white'], 2)
        
        q_text = f"Questions: {self.num_questions}"
        (qw, _), _ = cv2.getTextSize(q_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.putText(frame, q_text, ((w - qw) // 2, h // 2 + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['white'], 2)
        
        # Instructions
        instructions = [
            "Tips for your interview:",
            "- Look directly at the camera",
            "- Speak clearly and at a steady pace",
            "- Answer within the time limit",
            "",
            "Press SPACE to begin"
        ]
        
        y_start = h // 2 + 100
        for i, line in enumerate(instructions):
            color = COLORS['yellow'] if i == 0 else COLORS['light_gray']
            if "SPACE" in line:
                color = COLORS['green']
            (lw, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.putText(frame, line, ((w - lw) // 2, y_start + i * 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
    
    def _draw_countdown(self, frame):
        """Draw countdown before recording."""
        h, w = frame.shape[:2]
        
        # Question text at top
        question = self.question_engine.get_current_question()
        if question:
            draw_multiline_text(frame, question, (50, 80), w - 100,
                               font_scale=0.7, color=COLORS['white'],
                               bg_color=(40, 40, 50), thickness=2)
        
        # Big countdown number
        remaining = int(self.get_remaining_time()) + 1
        countdown_text = str(remaining)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(countdown_text, font, 5, 8)
        
        # Pulsing effect
        pulse = abs(np.sin(time.time() * 3)) * 0.3 + 0.7
        
        cv2.putText(frame, countdown_text, ((w - tw) // 2, h // 2 + th // 2),
                    font, 5, COLORS['yellow'], 8)
        
        cv2.putText(frame, "Get Ready!", ((w - 150) // 2, h // 2 + 80),
                    font, 1.0, COLORS['white'], 2)
    
    def _draw_question(self, frame):
        """Draw question display state."""
        h, w = frame.shape[:2]
        
        # Question text
        question = self.question_engine.get_current_question()
        if question:
            q_num = self.question_engine.get_question_number()
            full_text = f"Q{q_num}: {question}"
            draw_multiline_text(frame, full_text, (50, 80), w - 100,
                               font_scale=0.75, color=COLORS['white'],
                               bg_color=(40, 40, 50), thickness=2)
        
        cv2.putText(frame, "Listen to the question...", (w // 2 - 120, h - 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['cyan'], 2)
    
    def _draw_recording(self, frame):
        """Draw recording state UI."""
        h, w = frame.shape[:2]
        
        # Question text at top
        question = self.question_engine.get_current_question()
        if question:
            q_num = self.question_engine.get_question_number()
            full_text = f"Q{q_num}: {question}"
            draw_multiline_text(frame, full_text, (50, 80), w - 100,
                               font_scale=0.65, color=COLORS['white'],
                               bg_color=(40, 40, 50), thickness=1)
        
        # Timer
        remaining = self.get_remaining_time()
        draw_timer(frame, (w - 80, 120), remaining, self.question_time)
        
        # Recording indicator
        pulse = abs(np.sin(time.time() * 3))
        rec_color = (0, 0, int(200 + pulse * 55))  # Pulsing red
        cv2.circle(frame, (30, h - 40), 12, rec_color, -1)
        cv2.putText(frame, "RECORDING", (50, h - 33),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['red'], 2)
        
        # Audio level indicator
        audio_level = self.voice_analyzer.get_audio_level()
        bar_width = int(audio_level * 2)
        cv2.rectangle(frame, (150, h - 50), (150 + bar_width, h - 30), COLORS['green'], -1)
        cv2.rectangle(frame, (150, h - 50), (350, h - 30), COLORS['white'], 1)
        
        # Real-time scores on right side
        face_results = self.face_analyzer.get_session_stats()
        
        panel_x = w - 200
        panel_y = 200
        
        # Semi-transparent panel
        cv2.rectangle(frame, (panel_x - 10, panel_y - 10), 
                      (w - 10, panel_y + 120), (30, 30, 40), -1)
        cv2.rectangle(frame, (panel_x - 10, panel_y - 10), 
                      (w - 10, panel_y + 120), COLORS['cyan'], 1)
        
        cv2.putText(frame, "Real-time Analysis", (panel_x, panel_y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['cyan'], 1)
        
        draw_score_indicator(frame, (panel_x, panel_y + 30), 
                            face_results['eye_contact_rate'], "Eye Contact")
        draw_score_indicator(frame, (panel_x, panel_y + 70), 
                            face_results['average_stability'], "Stability")
        
        # Guidance text
        guidance = ""
        if face_results['eye_contact_rate'] < 40:
            guidance = "Look at the camera!"
        elif face_results['average_stability'] < 40:
            guidance = "Stay still"
        
        if guidance:
            (gw, _), _ = cv2.getTextSize(guidance, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.putText(frame, guidance, ((w - gw) // 2, h - 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['yellow'], 2)
        
        # Skip instruction
        cv2.putText(frame, "Press SPACE to finish answer", (w // 2 - 130, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['gray'], 1)
    
    def _draw_feedback(self, frame):
        """Draw feedback screen."""
        h, w = frame.shape[:2]
        
        if self.current_feedback:
            draw_question_feedback(frame, self.current_feedback, (w // 2 - 200, 100))
        
        # Continue indicator
        remaining = self.get_remaining_time()
        text = f"Next question in {int(remaining) + 1}s... (Press SPACE to skip)"
        cv2.putText(frame, text, (w // 2 - 200, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS['gray'], 1)
    
    def run(self):
        """Main application loop."""
        if not self.initialize_camera():
            return
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)
        
        print("\n" + "=" * 60)
        print("Interview Started!")
        print("=" * 60)
        print("\nControls:")
        print("  SPACE - Start / Skip / Continue")
        print("  Q     - Quit")
        print("  R     - Restart (in final report)")
        print("=" * 60)
        
        running = True
        
        while running:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to read from camera")
                break
            
            # Flip frame horizontally (mirror)
            frame = cv2.flip(frame, 1)
            
            # Resize to target dimensions
            frame = cv2.resize(frame, (self.window_width, self.window_height))
            
            # Process face analysis if recording
            if self.state == STATE_RECORDING:
                face_results = self.face_analyzer.process_frame(frame)
            else:
                # Light processing for visual feedback
                self.face_analyzer.process_frame(frame)
            
            # Update FPS counter
            self.fps_counter.update()
            
            # Handle state transitions
            self.handle_state_transitions()
            
            # Draw UI
            frame = self.draw_ui(frame)
            
            # Show frame
            cv2.imshow(self.window_name, frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                running = False
            
            elif key == ord(' '):  # Space
                if self.state == STATE_WELCOME:
                    self.change_state(STATE_QUESTION)
                elif self.state == STATE_RECORDING:
                    self.change_state(STATE_PROCESSING)
                elif self.state == STATE_FEEDBACK:
                    if self.question_engine.next_question():
                        self.change_state(STATE_QUESTION)
                    else:
                        self.change_state(STATE_FINAL_REPORT)
            
            elif key == ord('r') or key == ord('R'):
                if self.state == STATE_FINAL_REPORT:
                    # Restart
                    self.question_engine.reset()
                    self.feedback_generator.reset()
                    self.face_analyzer.reset_stats()
                    self.change_state(STATE_WELCOME)
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        self.face_analyzer.release()
        
        print("\nInterview session ended.")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("     AI INTERVIEW SIMULATOR")
    print("     Real-time Interview Practice with AI Feedback")
    print("=" * 60)
    
    # Get user preferences
    role = get_role_selection()
    experience = get_experience_selection()
    num_questions = get_num_questions()
    
    print(f"\nStarting interview for: {role} ({experience})")
    print(f"Number of questions: {num_questions}")
    print("\nInitializing... Please wait.")
    
    # Create and run simulator
    simulator = InterviewSimulator(role, experience, num_questions)
    simulator.run()


if __name__ == "__main__":
    main()
