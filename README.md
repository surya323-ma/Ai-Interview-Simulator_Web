# AI Interview Simulator — Web Edition

A browser-based mock interview coach. Pick a role, answer questions on
camera, and get live feedback on eye contact, posture stability, speaking
pace, and pauses — then a full performance report at the end.

This is a rebuild of the original OpenCV desktop app (`cv2.imshow` +
local mic) as a Flask web app, so it can actually run on a host like
Render, where there's no display or microphone attached to the server.

## How it works

- **Camera & mic** are captured entirely in the browser
  (`getUserMedia`). Frames are sent to the server for face analysis;
  audio never leaves the browser — speech-to-text and pause detection
  both run client-side.
- **Face analysis** (`face_analysis_web.py`) uses MediaPipe's
  `FaceLandmarker` task (`static/models/face_landmarker.task`) on
  frames posted from the browser roughly every 800ms, scoring eye
  contact and stability the same way the original desktop version did.
- **Speech-to-text** uses the browser's Web Speech API (best support in
  Chrome/Edge). If it's unavailable, the interview still runs and is
  scored on timing/duration, just without a transcript.
- **Text-to-speech** for reading questions aloud uses the browser's
  `speechSynthesis` API — no server-side TTS engine required.
- **Scoring & feedback** (`voice_scoring.py`, `feedback_web.py`) reuse
  the original scoring bands and recommendation logic.
- **Question bank** (`question_engine.py`) is unchanged from the
  desktop version.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in Chrome (recommended for live captions),
allow camera/microphone access, and start an interview.

## Deploy to Render

**Option A — Blueprint (recommended):**
1. Push this folder to a GitHub repo.
2. In Render, click **New > Blueprint**, point it at the repo — it will
   read `render.yaml` and set everything up automatically.
3. Deploy. Render installs `requirements.txt` and runs the app with
   gunicorn.

**Option B — Manual web service:**
1. **New > Web Service**, connect the repo.
2. Runtime: Python 3.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
5. Add an environment variable `SECRET_KEY` with any random string
   (used to sign the session cookie).

Notes:
- The free Render plan spins down on inactivity — first request after
  idle will be slow while MediaPipe's model loads.
- Camera/mic access requires HTTPS in the browser; Render serves your
  app on HTTPS by default, so this works out of the box.
- Session state (question progress, scores) is kept in memory per
  process. That's fine for a single instance; if you scale to multiple
  instances, move `SESSIONS` in `app.py` to Redis or a database.

## Project structure

```
app.py                  Flask routes / session orchestration
question_engine.py      Role-based question bank
face_analysis_web.py    MediaPipe FaceLandmarker scoring (server-side)
voice_scoring.py        Transcript/timing -> pace/length/pause scores
feedback_web.py         Per-answer feedback + final report generation
static/models/          face_landmarker.task (used), blaze_face_full_range.tflite (kept, currently unused)
static/css/style.css    Dashboard design system
static/js/app.js        Camera/mic capture, live meters, screen flow
templates/index.html    Setup / stage / feedback / report screens
requirements.txt        Python dependencies
Procfile, render.yaml   Deployment config
```

## Original desktop version

The original OpenCV desktop app (single-machine, `cv2.imshow` window,
local mic via `sounddevice`) is preserved for reference in
`legacy_desktop/`. It's not part of the deployable web app.
