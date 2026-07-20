"""
Feedback Module - Generates feedback and final report
"""

from utils import COLORS, draw_text_with_background, draw_multiline_text, draw_score_indicator
import cv2

class FeedbackGenerator:
    """Generates feedback for interview answers."""
    
    def __init__(self):
        """Initialize feedback generator."""
        self.all_feedback = []
        self.question_scores = []
    
    def generate_feedback(self, face_analysis, voice_analysis, question_num):
        """Generate feedback for a single answer."""
        feedback = {
            'question_number': question_num,
            'face': face_analysis,
            'voice': voice_analysis,
            'suggestions': [],
            'strengths': [],
        }
        
        # Analyze eye contact
        eye_contact = face_analysis.get('eye_contact_rate', 0)
        if eye_contact > 70:
            feedback['strengths'].append("Excellent eye contact maintained")
        elif eye_contact > 40:
            feedback['suggestions'].append("Try to maintain more consistent eye contact")
        else:
            feedback['suggestions'].append("Focus on looking at the camera more")
        
        # Analyze stability
        stability = face_analysis.get('average_stability', 0)
        if stability > 70:
            feedback['strengths'].append("Good posture stability")
        elif stability < 40:
            feedback['suggestions'].append("Try to minimize head movement")
        
        # Analyze response length
        length_score = voice_analysis.get('length_score', 0)
        length_cat = voice_analysis.get('length_category', 'Unknown')
        
        if length_score > 80:
            feedback['strengths'].append(f"Good response length ({length_cat})")
        elif length_cat == "Too Short":
            feedback['suggestions'].append("Elaborate more on your answers")
        elif length_cat == "Too Long":
            feedback['suggestions'].append("Be more concise in your responses")
        
        # Analyze speaking pace
        pace_score = voice_analysis.get('pace_score', 0)
        pace_cat = voice_analysis.get('pace_category', 'Unknown')
        
        if pace_score > 80:
            feedback['strengths'].append(f"Good speaking pace ({pace_cat})")
        elif pace_cat == "Too Slow":
            feedback['suggestions'].append("Try to speak a bit faster")
        elif pace_cat == "Too Fast":
            feedback['suggestions'].append("Slow down to improve clarity")
        
        # Analyze pauses
        pause_score = voice_analysis.get('pause_score', 0)
        if pause_score > 80:
            feedback['strengths'].append("Fluent delivery with natural pacing")
        elif pause_score < 60:
            feedback['suggestions'].append("Practice to reduce hesitations")
        
        # Calculate overall score for this question
        face_score = (eye_contact + stability) / 2
        voice_score = voice_analysis.get('overall_voice_score', 50)
        overall_score = (face_score * 0.4 + voice_score * 0.6)
        
        feedback['overall_score'] = overall_score
        
        self.all_feedback.append(feedback)
        self.question_scores.append(overall_score)
        
        return feedback
    
    def get_final_report(self, role, experience, total_questions):
        """Generate final interview report."""
        if not self.question_scores:
            return {
                'overall_score': 0,
                'grade': 'N/A',
                'strengths': [],
                'weaknesses': [],
                'recommendations': []
            }
        
        # Calculate overall score
        overall_score = sum(self.question_scores) / len(self.question_scores)
        
        # Determine grade
        if overall_score >= 85:
            grade = "Excellent"
            grade_color = COLORS['green']
        elif overall_score >= 70:
            grade = "Good"
            grade_color = COLORS['cyan']
        elif overall_score >= 55:
            grade = "Average"
            grade_color = COLORS['yellow']
        elif overall_score >= 40:
            grade = "Needs Improvement"
            grade_color = COLORS['orange']
        else:
            grade = "Poor"
            grade_color = COLORS['red']
        
        # Aggregate strengths and weaknesses
        all_strengths = []
        all_suggestions = []
        
        for fb in self.all_feedback:
            all_strengths.extend(fb['strengths'])
            all_suggestions.extend(fb['suggestions'])
        
        # Count frequency of feedback items
        strength_counts = {}
        for s in all_strengths:
            strength_counts[s] = strength_counts.get(s, 0) + 1
        
        weakness_counts = {}
        for w in all_suggestions:
            weakness_counts[w] = weakness_counts.get(w, 0) + 1
        
        # Get top items
        top_strengths = sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_weaknesses = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Generate recommendations
        recommendations = []
        
        if any('eye contact' in w[0].lower() for w in top_weaknesses):
            recommendations.append("Practice maintaining eye contact by looking directly at the camera")
        
        if any('elaborate' in w[0].lower() or 'short' in w[0].lower() for w in top_weaknesses):
            recommendations.append("Prepare more detailed examples using the STAR method")
        
        if any('concise' in w[0].lower() or 'long' in w[0].lower() for w in top_weaknesses):
            recommendations.append("Practice summarizing your points in 1-2 minutes")
        
        if any('pace' in w[0].lower() or 'fast' in w[0].lower() or 'slow' in w[0].lower() for w in top_weaknesses):
            recommendations.append("Record yourself practicing and adjust your speaking speed")
        
        if any('pause' in w[0].lower() or 'hesitation' in w[0].lower() for w in top_weaknesses):
            recommendations.append("Practice with common questions to reduce filler words")
        
        if any('movement' in w[0].lower() or 'posture' in w[0].lower() for w in top_weaknesses):
            recommendations.append("Be mindful of your body language; sit upright and stay still")
        
        # Default recommendation if none apply
        if not recommendations:
            recommendations.append("Keep practicing! Regular mock interviews help build confidence")
        
        return {
            'role': role,
            'experience': experience,
            'total_questions': total_questions,
            'questions_answered': len(self.question_scores),
            'overall_score': overall_score,
            'grade': grade,
            'grade_color': grade_color,
            'question_scores': self.question_scores,
            'strengths': [s[0] for s in top_strengths],
            'weaknesses': [w[0] for w in top_weaknesses],
            'recommendations': recommendations,
            'detailed_feedback': self.all_feedback
        }
    
    def reset(self):
        """Reset feedback data."""
        self.all_feedback = []
        self.question_scores = []


def draw_question_feedback(frame, feedback, position):
    """Draw feedback for a single question on the frame."""
    x, y = position
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Background panel
    panel_width = 400
    panel_height = 250
    cv2.rectangle(frame, (x, y), (x + panel_width, y + panel_height), 
                  COLORS['dark_gray'], -1)
    cv2.rectangle(frame, (x, y), (x + panel_width, y + panel_height), 
                  COLORS['cyan'], 2)
    
    # Title
    cv2.putText(frame, f"Question {feedback['question_number']} Feedback",
                (x + 10, y + 25), font, 0.6, COLORS['cyan'], 2)
    
    current_y = y + 50
    
    # Overall score
    score = feedback.get('overall_score', 0)
    if score >= 70:
        score_color = COLORS['green']
    elif score >= 50:
        score_color = COLORS['yellow']
    else:
        score_color = COLORS['red']
    
    cv2.putText(frame, f"Score: {int(score)}%",
                (x + 10, current_y), font, 0.7, score_color, 2)
    current_y += 30
    
    # Strengths
    if feedback['strengths']:
        cv2.putText(frame, "Strengths:", (x + 10, current_y), font, 0.5, COLORS['green'], 1)
        current_y += 20
        for strength in feedback['strengths'][:2]:
            cv2.putText(frame, f"+ {strength[:35]}", (x + 15, current_y), 
                        font, 0.4, COLORS['white'], 1)
            current_y += 18
    
    # Suggestions
    if feedback['suggestions']:
        current_y += 5
        cv2.putText(frame, "To Improve:", (x + 10, current_y), font, 0.5, COLORS['yellow'], 1)
        current_y += 20
        for suggestion in feedback['suggestions'][:2]:
            cv2.putText(frame, f"- {suggestion[:35]}", (x + 15, current_y), 
                        font, 0.4, COLORS['white'], 1)
            current_y += 18


def draw_final_report(frame, report):
    """Draw the final report on a frame."""
    h, w = frame.shape[:2]
    
    # Dark overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (20, 20, 30), -1)
    cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Title
    title = "INTERVIEW COMPLETE - FINAL REPORT"
    (tw, _), _ = cv2.getTextSize(title, font, 1.0, 2)
    cv2.putText(frame, title, ((w - tw) // 2, 50), font, 1.0, COLORS['cyan'], 2)
    
    # Role and Experience
    info_text = f"Role: {report['role']} | Level: {report['experience']}"
    (iw, _), _ = cv2.getTextSize(info_text, font, 0.6, 1)
    cv2.putText(frame, info_text, ((w - iw) // 2, 85), font, 0.6, COLORS['white'], 1)
    
    # Overall Score (big display)
    score = report['overall_score']
    grade = report['grade']
    grade_color = report.get('grade_color', COLORS['white'])
    
    # Score circle
    center_x = w // 2
    cv2.circle(frame, (center_x, 170), 70, COLORS['dark_gray'], -1)
    cv2.circle(frame, (center_x, 170), 70, grade_color, 4)
    
    score_text = f"{int(score)}%"
    (stw, _), _ = cv2.getTextSize(score_text, font, 1.5, 3)
    cv2.putText(frame, score_text, (center_x - stw // 2, 180), font, 1.5, grade_color, 3)
    
    cv2.putText(frame, grade, (center_x - 50, 215), font, 0.7, grade_color, 2)
    
    # Questions answered
    q_text = f"Questions Answered: {report['questions_answered']}/{report['total_questions']}"
    cv2.putText(frame, q_text, (center_x - 100, 260), font, 0.5, COLORS['white'], 1)
    
    # Two columns: Strengths and Areas to Improve
    col1_x = 50
    col2_x = w // 2 + 30
    col_y = 300
    
    # Strengths column
    cv2.putText(frame, "STRENGTHS", (col1_x, col_y), font, 0.7, COLORS['green'], 2)
    for i, strength in enumerate(report['strengths'][:4]):
        y_pos = col_y + 30 + i * 25
        cv2.putText(frame, f"+ {strength[:40]}", (col1_x, y_pos), font, 0.45, COLORS['white'], 1)
    
    # Weaknesses column
    cv2.putText(frame, "AREAS TO IMPROVE", (col2_x, col_y), font, 0.7, COLORS['yellow'], 2)
    for i, weakness in enumerate(report['weaknesses'][:4]):
        y_pos = col_y + 30 + i * 25
        cv2.putText(frame, f"- {weakness[:40]}", (col2_x, y_pos), font, 0.45, COLORS['white'], 1)
    
    # Recommendations
    rec_y = 450
    cv2.putText(frame, "RECOMMENDATIONS", (col1_x, rec_y), font, 0.7, COLORS['cyan'], 2)
    for i, rec in enumerate(report['recommendations'][:3]):
        y_pos = rec_y + 30 + i * 25
        cv2.putText(frame, f"{i+1}. {rec[:70]}", (col1_x, y_pos), font, 0.45, COLORS['white'], 1)
    
    # Question scores bar chart
    chart_y = 560
    cv2.putText(frame, "Score by Question:", (col1_x, chart_y), font, 0.5, COLORS['white'], 1)
    
    bar_width = 40
    bar_spacing = 10
    chart_x = col1_x
    
    for i, score in enumerate(report['question_scores']):
        bar_x = chart_x + i * (bar_width + bar_spacing)
        bar_height = int(score * 0.8)  # Scale to max 80 pixels
        
        if score >= 70:
            color = COLORS['green']
        elif score >= 50:
            color = COLORS['yellow']
        else:
            color = COLORS['red']
        
        cv2.rectangle(frame, (bar_x, chart_y + 100 - bar_height),
                      (bar_x + bar_width, chart_y + 100), color, -1)
        cv2.putText(frame, f"Q{i+1}", (bar_x + 10, chart_y + 115), font, 0.4, COLORS['white'], 1)
    
    # Instructions
    cv2.putText(frame, "Press 'Q' to quit or 'R' to restart", 
                (w // 2 - 150, h - 30), font, 0.6, COLORS['gray'], 1)
