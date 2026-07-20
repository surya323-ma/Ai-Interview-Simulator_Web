"""
Feedback Module (Web) - Generates per-answer feedback and the final report.
Scoring logic is carried over unchanged from the desktop feedback.py; the
cv2-based drawing functions are dropped since the browser frontend renders
the dashboard.
"""


class FeedbackGenerator:
    """Generates feedback for interview answers."""

    def __init__(self):
        self.all_feedback = []
        self.question_scores = []

    def generate_feedback(self, face_analysis, voice_analysis, question_num, question_text=""):
        """Generate feedback for a single answer."""
        feedback = {
            'question_number': question_num,
            'question': question_text,
            'face': face_analysis,
            'voice': voice_analysis,
            'suggestions': [],
            'strengths': [],
        }

        eye_contact = face_analysis.get('eye_contact_rate', 0)
        if eye_contact > 70:
            feedback['strengths'].append("Excellent eye contact maintained")
        elif eye_contact > 40:
            feedback['suggestions'].append("Try to maintain more consistent eye contact")
        else:
            feedback['suggestions'].append("Focus on looking at the camera more")

        stability = face_analysis.get('average_stability', 0)
        if stability > 70:
            feedback['strengths'].append("Good posture stability")
        elif stability < 40:
            feedback['suggestions'].append("Try to minimize head movement")

        length_score = voice_analysis.get('length_score', 0)
        length_cat = voice_analysis.get('length_category', 'Unknown')
        if length_score > 80:
            feedback['strengths'].append(f"Good response length ({length_cat})")
        elif length_cat == "Too Short":
            feedback['suggestions'].append("Elaborate more on your answers")
        elif length_cat == "Too Long":
            feedback['suggestions'].append("Be more concise in your responses")

        pace_score = voice_analysis.get('pace_score', 0)
        pace_cat = voice_analysis.get('pace_category', 'Unknown')
        if pace_score > 80:
            feedback['strengths'].append(f"Good speaking pace ({pace_cat})")
        elif pace_cat == "Too Slow":
            feedback['suggestions'].append("Try to speak a bit faster")
        elif pace_cat == "Too Fast":
            feedback['suggestions'].append("Slow down to improve clarity")

        pause_score = voice_analysis.get('pause_score', 0)
        if pause_score > 80:
            feedback['strengths'].append("Fluent delivery with natural pacing")
        elif pause_score < 60:
            feedback['suggestions'].append("Practice to reduce hesitations")

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

        overall_score = sum(self.question_scores) / len(self.question_scores)

        if overall_score >= 85:
            grade = "Excellent"
        elif overall_score >= 70:
            grade = "Good"
        elif overall_score >= 55:
            grade = "Average"
        elif overall_score >= 40:
            grade = "Needs Improvement"
        else:
            grade = "Poor"

        all_strengths = []
        all_suggestions = []
        for fb in self.all_feedback:
            all_strengths.extend(fb['strengths'])
            all_suggestions.extend(fb['suggestions'])

        strength_counts = {}
        for s in all_strengths:
            strength_counts[s] = strength_counts.get(s, 0) + 1

        weakness_counts = {}
        for w in all_suggestions:
            weakness_counts[w] = weakness_counts.get(w, 0) + 1

        top_strengths = sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_weaknesses = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)[:5]

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
        if not recommendations:
            recommendations.append("Keep practicing! Regular mock interviews help build confidence")

        return {
            'role': role,
            'experience': experience,
            'total_questions': total_questions,
            'questions_answered': len(self.question_scores),
            'overall_score': overall_score,
            'grade': grade,
            'question_scores': self.question_scores,
            'strengths': [s[0] for s in top_strengths],
            'weaknesses': [w[0] for w in top_weaknesses],
            'recommendations': recommendations,
            'detailed_feedback': self.all_feedback,
        }

    def reset(self):
        self.all_feedback = []
        self.question_scores = []
