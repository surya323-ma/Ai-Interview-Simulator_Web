"""
Voice Scoring Module (Web) - Scores a spoken answer using the transcript and
timing captured in the browser via the Web Speech API (SpeechRecognition) and
a simple silence-based pause counter run on the client. The scoring bands are
carried over unchanged from the desktop voice_analysis.py so results line up
with the rest of the project.

Running the mic server-side (as the desktop app did with sounddevice) isn't
an option for a hosted web app, so the browser does the listening and this
module just turns the resulting numbers into scores + categories.
"""


def score_voice(transcript, duration_seconds, pause_count=0):
    """
    Score a single answer.

    transcript: the recognized text (may be empty if speech recognition
        wasn't available/granted - we still score on duration/silence).
    duration_seconds: how long the user was recording.
    pause_count: number of pauses >= ~0.6s detected client-side.
    """
    transcript = (transcript or "").strip()
    words = transcript.split()
    word_count = len(words)
    duration_seconds = max(0.0, float(duration_seconds or 0))

    words_per_minute = (word_count / duration_seconds) * 60 if duration_seconds > 0 else 0

    # Response length
    if word_count < 20:
        length_category, length_score = "Too Short", 30
    elif word_count < 50:
        length_category, length_score = "Short", 60
    elif word_count < 150:
        length_category, length_score = "Good", 90
    elif word_count < 250:
        length_category, length_score = "Detailed", 85
    else:
        length_category, length_score = "Too Long", 60

    # Speaking pace
    if words_per_minute < 80:
        pace_category, pace_score = "Too Slow", 50
    elif words_per_minute < 120:
        pace_category, pace_score = "Measured", 80
    elif words_per_minute < 160:
        pace_category, pace_score = "Good", 95
    elif words_per_minute < 200:
        pace_category, pace_score = "Quick", 75
    else:
        pace_category, pace_score = "Too Fast", 50

    # Pauses
    if pause_count == 0:
        pause_category, pause_score = "Fluent", 95
    elif pause_count <= 2:
        pause_category, pause_score = "Natural", 85
    elif pause_count <= 5:
        pause_category, pause_score = "Some Hesitation", 65
    else:
        pause_category, pause_score = "Frequent Pauses", 40

    return {
        'transcript': transcript,
        'word_count': word_count,
        'speaking_duration': duration_seconds,
        'words_per_minute': words_per_minute,
        'pause_count': pause_count,
        'length_category': length_category,
        'length_score': length_score,
        'pace_category': pace_category,
        'pace_score': pace_score,
        'pause_category': pause_category,
        'pause_score': pause_score,
        'overall_voice_score': (length_score + pace_score + pause_score) / 3,
    }
