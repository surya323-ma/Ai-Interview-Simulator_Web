#!/usr/bin/env python3
"""
AI Interview Simulator - Web Application
Flask backend for the browser-based dashboard. Replaces the original
OpenCV desktop loop with a small JSON API the frontend (static/js/app.js)
drives: pick a role -> answer questions on camera/mic in the browser ->
get live face-tracking feedback -> get a scored report at the end.
"""

import os
import time
import uuid

from flask import Flask, render_template, request, jsonify, session

from question_engine import QuestionEngine, AVAILABLE_ROLES, EXPERIENCE_LEVELS, QUESTION_DATABASE
from feedback_web import FeedbackGenerator
import face_analysis_web as face_web
import voice_scoring

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# In-memory session store: session_id -> interview state.
# Fine for a single-process demo deployment; swap for redis if you scale out.
SESSIONS = {}


def get_session_id():
    sid = session.get("sid")
    if not sid or sid not in SESSIONS:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    return sid


def get_state(sid):
    return SESSIONS.get(sid)


@app.route("/")
def index():
    return render_template(
        "index.html",
        roles=AVAILABLE_ROLES,
        experiences=EXPERIENCE_LEVELS,
    )


@app.route("/api/roles")
def api_roles():
    """Role -> question count per experience level, for the setup screen."""
    data = {}
    for role in AVAILABLE_ROLES:
        data[role] = {
            level: len(QUESTION_DATABASE[role][level])
            for level in QUESTION_DATABASE[role]
        }
    return jsonify({"roles": AVAILABLE_ROLES, "experiences": EXPERIENCE_LEVELS, "counts": data})


@app.route("/api/session/start", methods=["POST"])
def start_session():
    payload = request.get_json(force=True) or {}
    role = payload.get("role")
    experience = payload.get("experience")
    num_questions = int(payload.get("num_questions", 5))

    if role not in AVAILABLE_ROLES:
        return jsonify({"error": "Unknown role"}), 400
    if experience not in EXPERIENCE_LEVELS:
        return jsonify({"error": "Unknown experience level"}), 400
    num_questions = max(3, min(10, num_questions))

    sid = get_session_id()
    engine = QuestionEngine(role, experience, num_questions)

    SESSIONS[sid] = {
        "role": role,
        "experience": experience,
        "engine": engine,
        "feedback": FeedbackGenerator(),
        "face_stats": face_web.new_face_stats(),
        "started_at": time.time(),
    }

    return jsonify({
        "question": engine.get_current_question(),
        "question_number": engine.get_question_number(),
        "total_questions": engine.get_total_questions(),
        "role": role,
        "experience": experience,
    })


@app.route("/api/question/begin", methods=["POST"])
def begin_question():
    """Reset the live face-tracking accumulator for a fresh question."""
    sid = get_session_id()
    state = get_state(sid)
    if not state:
        return jsonify({"error": "No active session"}), 400

    state["face_stats"] = face_web.new_face_stats()
    return jsonify({"ok": True})


@app.route("/api/frame", methods=["POST"])
def analyze_frame():
    """Receive one webcam frame (data URL) and return live scores."""
    sid = get_session_id()
    state = get_state(sid)
    if not state:
        return jsonify({"error": "No active session"}), 400

    payload = request.get_json(force=True) or {}
    frame = face_web.decode_data_url(payload.get("image"))
    result = face_web.analyze_frame(frame, state["face_stats"])
    return jsonify(result)


@app.route("/api/answer/submit", methods=["POST"])
def submit_answer():
    """Score the answer (transcript from Web Speech API + accumulated face stats)."""
    sid = get_session_id()
    state = get_state(sid)
    if not state:
        return jsonify({"error": "No active session"}), 400

    payload = request.get_json(force=True) or {}
    transcript = payload.get("transcript", "")
    duration = payload.get("duration", 0)
    pause_count = int(payload.get("pause_count", 0))

    engine = state["engine"]
    voice_result = voice_scoring.score_voice(transcript, duration, pause_count)
    face_result = face_web.get_session_stats(state["face_stats"])

    feedback = state["feedback"].generate_feedback(
        face_result,
        voice_result,
        engine.get_question_number(),
        engine.get_current_question(),
    )

    engine.store_answer({"voice": voice_result, "face": face_result, "feedback": feedback})

    has_next = engine.next_question()
    next_question = engine.get_current_question() if has_next else None

    return jsonify({
        "feedback": feedback,
        "has_next": has_next,
        "next_question": next_question,
        "next_question_number": engine.get_question_number() if has_next else None,
        "total_questions": engine.get_total_questions(),
    })


@app.route("/api/report")
def get_report():
    sid = get_session_id()
    state = get_state(sid)
    if not state:
        return jsonify({"error": "No active session"}), 400

    engine = state["engine"]
    report = state["feedback"].get_final_report(
        state["role"], state["experience"], engine.get_total_questions()
    )
    return jsonify(report)


@app.route("/api/session/reset", methods=["POST"])
def reset_session():
    sid = session.get("sid")
    if sid in SESSIONS:
        del SESSIONS[sid]
    session.pop("sid", None)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
