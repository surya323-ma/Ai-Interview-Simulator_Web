/* AI Interview Simulator — frontend controller
 * Talks to the Flask API (app.py) and drives the four screens:
 * setup -> stage (question/recording) -> feedback -> report
 */
(() => {
  "use strict";

  const QUESTION_TIME = 45;   // seconds to answer
  const COUNTDOWN_TIME = 3;   // seconds before recording starts
  const FRAME_INTERVAL_MS = 800;
  const AUTO_ADVANCE_MS = 6000;
  const SILENCE_PAUSE_MS = 650; // silence duration that counts as one "pause"
  const RING_CIRCUMFERENCE = 2 * Math.PI * 34;

  // ---------- DOM ----------
  const screens = {
    setup: document.getElementById("screen-setup"),
    stage: document.getElementById("screen-stage"),
    feedback: document.getElementById("screen-feedback"),
    report: document.getElementById("screen-report"),
  };

  const roleGrid = document.getElementById("roleGrid");
  const expRow = document.getElementById("expRow");
  const numQuestionsInput = document.getElementById("numQuestions");
  const numQuestionsValue = document.getElementById("numQuestionsValue");
  const startBtn = document.getElementById("startBtn");

  const stageProgress = document.getElementById("stageProgress");
  const questionText = document.getElementById("questionText");
  const camVideo = document.getElementById("camVideo");
  const camPlaceholder = document.getElementById("camPlaceholder");
  const ringProgress = document.getElementById("ringProgress");
  const ringTimerText = document.getElementById("ringTimerText");
  const recIndicator = document.getElementById("recIndicator");
  const captionLine = document.getElementById("captionLine");
  const eyeContactFill = document.getElementById("eyeContactFill");
  const eyeContactValue = document.getElementById("eyeContactValue");
  const stabilityFill = document.getElementById("stabilityFill");
  const stabilityValue = document.getElementById("stabilityValue");
  const audioMeter = document.getElementById("audioMeter");
  const guidanceNote = document.getElementById("guidanceNote");
  const skipBtn = document.getElementById("skipBtn");

  const fbScore = document.getElementById("fbScore");
  const fbGrade = document.getElementById("fbGrade");
  const fbStrengths = document.getElementById("fbStrengths");
  const fbSuggestions = document.getElementById("fbSuggestions");
  const continueBtn = document.getElementById("continueBtn");
  const autoAdvanceNote = document.getElementById("autoAdvanceNote");

  const reportDial = document.getElementById("reportDial");
  const reportScoreText = document.getElementById("reportScoreText");
  const reportGrade = document.getElementById("reportGrade");
  const reportRoleLine = document.getElementById("reportRoleLine");
  const reportBadge = document.getElementById("reportBadge");
  const reportStrengths = document.getElementById("reportStrengths");
  const reportWeaknesses = document.getElementById("reportWeaknesses");
  const reportRecs = document.getElementById("reportRecs");
  const restartBtn = document.getElementById("restartBtn");
  const changeRoleBtn = document.getElementById("changeRoleBtn");

  const captureCanvas = document.getElementById("captureCanvas");
  const captureCtx = captureCanvas.getContext("2d");

  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");

  // ---------- state ----------
  let selectedRole = null;
  let selectedExperience = null;
  let totalQuestions = 5;
  let currentQuestionNumber = 1;
  let currentTotal = 5;

  let mediaStream = null;
  let audioCtx = null;
  let analyser = null;
  let audioBars = [];
  let audioLoopHandle = null;
  let speaking = false;
  let silenceStart = null;
  let pauseCount = 0;

  let recognition = null;
  let recognitionSupported = "webkitSpeechRecognition" in window || "SpeechRecognition" in window;
  let finalTranscript = "";
  let recognitionShouldRun = false;

  let frameTimer = null;
  let countdownTimer = null;
  let answerTimer = null;
  let recordStartedAt = null;
  let autoAdvanceTimeout = null;
  let autoAdvanceInterval = null;

  // ---------- helpers ----------
  function showScreen(name) {
    Object.values(screens).forEach((s) => s.classList.remove("active"));
    screens[name].classList.add("active");
  }

  function setStatus(live) {
    if (live) {
      statusDot.classList.remove("ready");
      statusDot.classList.add("live");
      statusText.textContent = "Recording";
    } else {
      statusDot.classList.remove("live");
      statusDot.classList.add("ready");
      statusText.textContent = "Ready";
    }
  }

  function scoreColor(score) {
    if (score >= 70) return "#3ECF8E";
    if (score >= 45) return "#F2B84B";
    return "#FF6B6B";
  }

  // ---------- setup screen ----------
  roleGrid.querySelectorAll(".role-tile").forEach((tile) => {
    tile.addEventListener("click", () => {
      roleGrid.querySelectorAll(".role-tile").forEach((t) => t.classList.remove("selected"));
      tile.classList.add("selected");
      selectedRole = tile.dataset.role;
      updateStartEnabled();
    });
  });

  expRow.querySelectorAll(".pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      expRow.querySelectorAll(".pill").forEach((p) => p.classList.remove("selected"));
      pill.classList.add("selected");
      selectedExperience = pill.dataset.exp;
      updateStartEnabled();
    });
  });

  numQuestionsInput.addEventListener("input", () => {
    numQuestionsValue.textContent = numQuestionsInput.value;
    totalQuestions = parseInt(numQuestionsInput.value, 10);
  });

  function updateStartEnabled() {
    startBtn.disabled = !(selectedRole && selectedExperience);
  }

  startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    startBtn.textContent = "Setting the stage…";
    try {
      await ensureMedia();
      const res = await fetch("/api/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: selectedRole,
          experience: selectedExperience,
          num_questions: totalQuestions,
        }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      currentTotal = data.total_questions;
      showScreen("stage");
      buildProgressDots(currentTotal);
      beginQuestionFlow(data.question, data.question_number, currentTotal);
    } catch (err) {
      console.error(err);
      guidanceNote.textContent = "Couldn't access camera/microphone. Please allow permissions and try again.";
      alert("Couldn't start the interview: " + err.message + "\n\nMake sure you allow camera & microphone access.");
    } finally {
      startBtn.disabled = false;
      startBtn.textContent = "Begin interview →";
    }
  });

  // ---------- media setup ----------
  async function ensureMedia() {
    if (mediaStream) return;
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    camVideo.srcObject = mediaStream;
    camPlaceholder.style.display = "none";

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtx.createMediaStreamSource(mediaStream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);

    audioMeter.innerHTML = "";
    audioBars = [];
    for (let i = 0; i < 20; i++) {
      const bar = document.createElement("div");
      bar.className = "audio-bar";
      audioMeter.appendChild(bar);
      audioBars.push(bar);
    }
  }

  function buildProgressDots(total) {
    stageProgress.innerHTML = "";
    for (let i = 1; i <= total; i++) {
      const dot = document.createElement("div");
      dot.className = "dot";
      dot.dataset.n = i;
      stageProgress.appendChild(dot);
    }
    const label = document.createElement("span");
    label.className = "label";
    label.id = "stageLabelDynamic";
    stageProgress.appendChild(label);
    updateProgressDots();
  }

  function updateProgressDots() {
    stageProgress.querySelectorAll(".dot").forEach((dot) => {
      const n = parseInt(dot.dataset.n, 10);
      dot.classList.remove("done", "active");
      if (n < currentQuestionNumber) dot.classList.add("done");
      else if (n === currentQuestionNumber) dot.classList.add("active");
    });
    const dyn = document.getElementById("stageLabelDynamic");
    if (dyn) dyn.textContent = `Question ${currentQuestionNumber} / ${currentTotal}`;
  }

  // ---------- question flow ----------
  async function beginQuestionFlow(question, qnum, total) {
    currentQuestionNumber = qnum;
    currentTotal = total;
    updateProgressDots();

    questionText.textContent = question;
    resetLiveMeters();
    guidanceNote.textContent = "Get comfortable — recording starts after a short countdown.";
    skipBtn.style.display = "none";
    recIndicator.style.display = "none";
    captionLine.textContent = "";
    finalTranscript = "";
    pauseCount = 0;
    speaking = false;
    silenceStart = null;

    await fetch("/api/question/begin", { method: "POST" });

    // Speak the question aloud (Web Speech Synthesis)
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(question);
      utter.rate = 1.0;
      window.speechSynthesis.speak(utter);
    } catch (e) { /* speech synthesis not available - not fatal */ }

    runCountdown();
  }

  function runCountdown() {
    let remaining = COUNTDOWN_TIME;
    setRing(1, "#F2B84B");
    ringTimerText.textContent = remaining;
    guidanceNote.textContent = "Get ready…";
    clearInterval(countdownTimer);
    countdownTimer = setInterval(() => {
      remaining -= 1;
      ringTimerText.textContent = Math.max(remaining, 0);
      if (remaining <= 0) {
        clearInterval(countdownTimer);
        startRecording();
      }
    }, 1000);
  }

  function startRecording() {
    recIndicator.style.display = "flex";
    skipBtn.style.display = "inline-flex";
    guidanceNote.textContent = "Speak your answer — look at the camera.";
    setStatus(true);

    recordStartedAt = performance.now();
    let remaining = QUESTION_TIME;
    ringTimerText.textContent = remaining;
    setRing(1, "#F2B84B");

    clearInterval(answerTimer);
    answerTimer = setInterval(() => {
      remaining -= 1;
      const frac = Math.max(0, remaining / QUESTION_TIME);
      setRing(frac, remaining <= 10 ? "#FF6B6B" : "#F2B84B");
      ringTimerText.textContent = Math.max(remaining, 0);
      if (remaining <= 0) {
        clearInterval(answerTimer);
        finishAnswer();
      }
    }, 1000);

    startFrameCapture();
    startAudioLoop();
    startSpeechRecognition();
  }

  skipBtn.addEventListener("click", () => {
    if (answerTimer) {
      clearInterval(answerTimer);
      finishAnswer();
    }
  });

  function setRing(fraction, color) {
    const offset = RING_CIRCUMFERENCE * (1 - Math.max(0, Math.min(1, fraction)));
    ringProgress.style.strokeDasharray = `${RING_CIRCUMFERENCE}`;
    ringProgress.style.strokeDashoffset = `${offset}`;
    ringProgress.style.stroke = color;
  }

  function resetLiveMeters() {
    eyeContactFill.style.width = "0%";
    eyeContactValue.textContent = "0%";
    stabilityFill.style.width = "0%";
    stabilityValue.textContent = "0%";
    eyeContactFill.style.background = "#3ECF8E";
    stabilityFill.style.background = "#3ECF8E";
  }

  // ---------- frame capture -> /api/frame ----------
  function startFrameCapture() {
    clearInterval(frameTimer);
    frameTimer = setInterval(async () => {
      if (!mediaStream || camVideo.videoWidth === 0) return;
      captureCanvas.width = 320;
      captureCanvas.height = 240;
      captureCtx.drawImage(camVideo, 0, 0, 320, 240);
      const dataUrl = captureCanvas.toDataURL("image/jpeg", 0.55);
      try {
        const res = await fetch("/api/frame", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image: dataUrl }),
        });
        const data = await res.json();
        updateLiveMeters(data);
      } catch (e) { /* transient network hiccup, ignore */ }
    }, FRAME_INTERVAL_MS);
  }

  function updateLiveMeters(data) {
    const eye = Math.round(data.eye_contact || 0);
    const stab = Math.round(data.stability || 0);
    eyeContactFill.style.width = eye + "%";
    eyeContactValue.textContent = eye + "%";
    eyeContactFill.style.background = scoreColor(eye);
    stabilityFill.style.width = stab + "%";
    stabilityValue.textContent = stab + "%";
    stabilityFill.style.background = scoreColor(stab);

    if (!data.face_detected) {
      guidanceNote.textContent = "We can't see your face — center yourself in frame.";
    } else if (eye < 40) {
      guidanceNote.textContent = "Look at the camera lens, not the screen.";
    } else if (stab < 40) {
      guidanceNote.textContent = "Try to stay a little more still.";
    } else {
      guidanceNote.textContent = "Looking good — keep going.";
    }
  }

  // ---------- audio level + pause detection ----------
  function startAudioLoop() {
    const data = new Uint8Array(analyser.frequencyBinCount);

    function loop() {
      analyser.getByteTimeDomainData(data);
      let sumSquares = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sumSquares += v * v;
      }
      const rms = Math.sqrt(sumSquares / data.length);
      const level = Math.min(1, rms * 6);

      const activeBars = Math.round(level * audioBars.length);
      audioBars.forEach((bar, i) => {
        bar.style.height = (i < activeBars ? 15 + (i / audioBars.length) * 85 : 8) + "%";
        bar.style.background = i < activeBars ? (i > audioBars.length * 0.8 ? "#FF6B6B" : "#F2B84B") : "#2A2F3A";
      });

      const now = performance.now();
      const THRESHOLD = 0.06;
      if (level > THRESHOLD) {
        if (!speaking && silenceStart !== null) {
          const silenceDuration = now - silenceStart;
          if (silenceDuration > SILENCE_PAUSE_MS) pauseCount += 1;
        }
        speaking = true;
        silenceStart = null;
      } else {
        if (speaking) {
          speaking = false;
          silenceStart = now;
        }
      }

      audioLoopHandle = requestAnimationFrame(loop);
    }
    loop();
  }

  function stopAudioLoop() {
    if (audioLoopHandle) cancelAnimationFrame(audioLoopHandle);
    audioLoopHandle = null;
    audioBars.forEach((bar) => { bar.style.height = "8%"; bar.style.background = "#2A2F3A"; });
  }

  // ---------- speech recognition (transcript) ----------
  function startSpeechRecognition() {
    finalTranscript = "";
    if (!recognitionSupported) {
      captionLine.textContent = "Live captions need Chrome or Edge — your answer will still be timed.";
      return;
    }
    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognitionShouldRun = true;

    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptPiece = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcriptPiece + " ";
        } else {
          interim += transcriptPiece;
        }
      }
      captionLine.textContent = (finalTranscript + interim).trim();
    };

    recognition.onerror = () => { /* swallow — we'll restart on 'end' if still recording */ };

    recognition.onend = () => {
      if (recognitionShouldRun) {
        try { recognition.start(); } catch (e) { /* already starting */ }
      }
    };

    try { recognition.start(); } catch (e) { /* ignore */ }
  }

  function stopSpeechRecognition() {
    recognitionShouldRun = false;
    if (recognition) {
      try { recognition.stop(); } catch (e) { /* ignore */ }
    }
  }

  // ---------- finishing an answer ----------
  async function finishAnswer() {
    clearInterval(answerTimer);
    clearInterval(frameTimer);
    stopAudioLoop();
    stopSpeechRecognition();
    skipBtn.style.display = "none";
    recIndicator.style.display = "none";
    setStatus(false);

    const durationSeconds = recordStartedAt ? (performance.now() - recordStartedAt) / 1000 : QUESTION_TIME;

    guidanceNote.textContent = "Scoring your answer…";

    const res = await fetch("/api/answer/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transcript: finalTranscript.trim(),
        duration: durationSeconds,
        pause_count: pauseCount,
      }),
    });
    const data = await res.json();
    renderFeedback(data);
  }

  function renderFeedback(data) {
    const fb = data.feedback;
    const score = Math.round(fb.overall_score);
    fbScore.textContent = score + "%";
    fbScore.style.color = scoreColor(score);
    fbGrade.textContent = `Question ${fb.question_number} of ${currentTotal} — here's how that went`;

    fbStrengths.innerHTML = "";
    if (fb.strengths.length === 0) {
      fbStrengths.innerHTML = "<li>Nothing flagged yet — keep going.</li>";
    } else {
      fb.strengths.forEach((s) => {
        const li = document.createElement("li");
        li.textContent = s;
        fbStrengths.appendChild(li);
      });
    }

    fbSuggestions.innerHTML = "";
    if (fb.suggestions.length === 0) {
      fbSuggestions.innerHTML = "<li>Nothing specific — nicely balanced answer.</li>";
    } else {
      fb.suggestions.forEach((s) => {
        const li = document.createElement("li");
        li.textContent = s;
        fbSuggestions.appendChild(li);
      });
    }

    showScreen("feedback");

    const goNext = () => {
      clearTimeout(autoAdvanceTimeout);
      clearInterval(autoAdvanceInterval);
      if (data.has_next) {
        showScreen("stage");
        beginQuestionFlow(data.next_question, data.next_question_number, data.total_questions);
      } else {
        loadReport();
      }
    };

    continueBtn.onclick = goNext;

    let secondsLeft = Math.round(AUTO_ADVANCE_MS / 1000);
    autoAdvanceNote.textContent = `Auto-advancing in ${secondsLeft}s…`;
    clearInterval(autoAdvanceInterval);
    autoAdvanceInterval = setInterval(() => {
      secondsLeft -= 1;
      autoAdvanceNote.textContent = `Auto-advancing in ${Math.max(secondsLeft, 0)}s…`;
    }, 1000);
    clearTimeout(autoAdvanceTimeout);
    autoAdvanceTimeout = setTimeout(goNext, AUTO_ADVANCE_MS);
  }

  // ---------- final report ----------
  let scoreChart = null;

  async function loadReport() {
    const res = await fetch("/api/report");
    const report = await res.json();

    const score = Math.round(report.overall_score);
    reportScoreText.textContent = score + "%";
    const circumference = 2 * Math.PI * 68;
    reportDial.style.strokeDasharray = `${circumference}`;
    reportDial.style.strokeDashoffset = `${circumference * (1 - score / 100)}`;
    reportDial.style.stroke = scoreColor(score);

    reportGrade.textContent = report.grade;
    reportRoleLine.textContent = `${report.role} · ${report.experience} · ${report.questions_answered}/${report.total_questions} questions`;
    reportBadge.textContent = report.grade;
    const c = scoreColor(score);
    reportBadge.style.borderColor = c;
    reportBadge.style.color = c;

    reportStrengths.innerHTML = "";
    (report.strengths.length ? report.strengths : ["Complete a full interview to surface patterns."]).forEach((s) => {
      const li = document.createElement("li");
      li.textContent = s;
      reportStrengths.appendChild(li);
    });

    reportWeaknesses.innerHTML = "";
    (report.weaknesses.length ? report.weaknesses : ["No recurring issues spotted — nice work."]).forEach((w) => {
      const li = document.createElement("li");
      li.textContent = w;
      reportWeaknesses.appendChild(li);
    });

    reportRecs.innerHTML = "";
    report.recommendations.forEach((r, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="rec-num">${String(i + 1).padStart(2, "0")}</span><span>${r}</span>`;
      reportRecs.appendChild(li);
    });

    renderScoreChart(report.question_scores);
    showScreen("report");
  }

  function renderScoreChart(scores) {
    const ctx = document.getElementById("scoreChart").getContext("2d");
    if (scoreChart) scoreChart.destroy();
    scoreChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: scores.map((_, i) => `Q${i + 1}`),
        datasets: [{
          data: scores.map((s) => Math.round(s)),
          backgroundColor: scores.map((s) => scoreColor(s)),
          borderRadius: 6,
          maxBarThickness: 46,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, max: 100, ticks: { color: "#8B93A7" }, grid: { color: "#2A2F3A" } },
          x: { ticks: { color: "#8B93A7" }, grid: { display: false } },
        },
      },
    });
  }

  // ---------- restart ----------
  async function resetToSetup() {
    await fetch("/api/session/reset", { method: "POST" });
    currentQuestionNumber = 1;
    showScreen("setup");
  }

  restartBtn.addEventListener("click", resetToSetup);
  changeRoleBtn.addEventListener("click", resetToSetup);
})();
