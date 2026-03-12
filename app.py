#!/usr/bin/env python3
"""
app.py - Flask web interface for the Video Storyboard Generator
Run with:  python app.py
Then open  http://localhost:5000
"""

import os
import threading
import uuid
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, send_from_directory

app = Flask(__name__)
BASE_OUTPUT = Path("storyboard_output")

# Track jobs: {job_id: {"status": "...", "log": [...], "html": "..."}}
JOBS: dict = {}
JOBS_LOCK = threading.Lock()

# ── HTML templates ─────────────────────────────────────────────────────────────

INDEX_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🎬 Video Storyboard Generator</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d0d0d;
    color: #f0f0f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px 16px;
  }
  h1 { font-size: 2.2rem; color: #96c8ff; margin-bottom: 8px; }
  .subtitle { color: #888; margin-bottom: 36px; text-align: center; }
  .card {
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 14px;
    padding: 32px;
    width: 100%;
    max-width: 600px;
  }
  label { display: block; font-size: 0.9rem; color: #aaa; margin-bottom: 6px; }
  input[type=url], select {
    width: 100%;
    background: #0d0d0d;
    border: 1px solid #444;
    border-radius: 8px;
    color: #f0f0f0;
    padding: 12px 14px;
    font-size: 1rem;
    margin-bottom: 18px;
    outline: none;
    transition: border-color .2s;
    direction: ltr;
  }
  input[type=url]:focus, select:focus { border-color: #96c8ff; }
  .row { display: flex; gap: 16px; }
  .row > div { flex: 1; }
  button {
    width: 100%;
    background: #1a6aff;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 14px;
    font-size: 1.1rem;
    cursor: pointer;
    font-weight: 700;
    transition: background .2s;
  }
  button:hover { background: #0050dd; }
  button:disabled { background: #333; color: #666; cursor: default; }
  #log-box {
    display: none;
    margin-top: 24px;
    background: #0d0d0d;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 16px;
    font-family: monospace;
    font-size: 0.85rem;
    color: #aef;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    direction: ltr;
    text-align: left;
  }
  #result-link {
    display: none;
    margin-top: 20px;
    text-align: center;
    padding: 14px;
    background: #0a3a1a;
    border: 1px solid #1a8a3a;
    border-radius: 8px;
  }
  #result-link a {
    color: #4cff8a;
    font-size: 1.1rem;
    font-weight: 700;
    text-decoration: none;
  }
  #result-link a:hover { text-decoration: underline; }
  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid #fff;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin .8s linear infinite;
    vertical-align: middle;
    margin-left: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<h1>🎬 Video Storyboard Generator</h1>
<p class="subtitle">הכניסי קישור לסרטון – תקבלי סטוריבורד מדויק עם צילומי מסך וטקסט</p>
<div class="card">
  <label>קישור לסרטון (Instagram, TikTok, YouTube, וכו׳)</label>
  <input type="url" id="url" placeholder="https://www.instagram.com/reel/..." />

  <div class="row">
    <div>
      <label>דיוק תמלול</label>
      <select id="model">
        <option value="tiny">tiny – מהיר מאוד</option>
        <option value="base" selected>base – מאוזן (מומלץ)</option>
        <option value="small">small – מדויק יותר</option>
        <option value="medium">medium – איכותי</option>
        <option value="large">large – הכי מדויק (איטי)</option>
      </select>
    </div>
    <div>
      <label>עמודות בגריד PNG</label>
      <select id="columns">
        <option value="1">1</option>
        <option value="2" selected>2</option>
        <option value="3">3</option>
      </select>
    </div>
  </div>

  <button id="btn" onclick="startJob()">צור סטוריבורד ▶</button>
  <div id="log-box"></div>
  <div id="result-link"></div>
</div>

<script>
let pollInterval = null;

async function startJob() {
  const url = document.getElementById('url').value.trim();
  if (!url) { alert('נא להכניס קישור לסרטון'); return; }
  const model = document.getElementById('model').value;
  const columns = document.getElementById('columns').value;

  const btn = document.getElementById('btn');
  btn.disabled = true;
  btn.innerHTML = 'מעבד... <span class="spinner"></span>';

  const logBox = document.getElementById('log-box');
  logBox.style.display = 'block';
  logBox.textContent = 'מתחיל...\\n';

  document.getElementById('result-link').style.display = 'none';

  const res = await fetch('/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({url, model, columns: parseInt(columns)}),
  });
  const {job_id} = await res.json();

  pollInterval = setInterval(() => pollJob(job_id), 2000);
}

async function pollJob(job_id) {
  const res = await fetch(`/status/${job_id}`);
  const data = await res.json();

  const logBox = document.getElementById('log-box');
  logBox.textContent = data.log.join('\\n');
  logBox.scrollTop = logBox.scrollHeight;

  if (data.status === 'done') {
    clearInterval(pollInterval);
    document.getElementById('btn').disabled = false;
    document.getElementById('btn').innerHTML = 'צור סטוריבורד ▶';
    const rl = document.getElementById('result-link');
    rl.style.display = 'block';
    rl.innerHTML = `<a href="/result/${job_id}" target="_blank">✅ פתח את הסטוריבורד »</a>`;
  } else if (data.status === 'error') {
    clearInterval(pollInterval);
    document.getElementById('btn').disabled = false;
    document.getElementById('btn').innerHTML = 'צור סטוריבורד ▶';
    logBox.style.color = '#ff7070';
  }
}
</script>
</body>
</html>
"""


# ── Background worker ──────────────────────────────────────────────────────────

def run_job(job_id: str, url: str, model: str, columns: int):
    from downloader import download_video
    from transcriber import transcribe
    from frame_extractor import extract_frames_for_segments
    from storyboard import build_storyboard_html

    def log(msg):
        with JOBS_LOCK:
            JOBS[job_id]["log"].append(msg)
        print(f"[{job_id[:8]}] {msg}")

    output_dir = BASE_OUTPUT / job_id
    work_dir = output_dir / "_work"
    frames_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        log("📥 מוריד סרטון...")
        video_path = download_video(url, str(work_dir))
        log(f"✓ הורד: {Path(video_path).name}")

        log(f"🎙️ מתמלל עם Whisper ({model})...")
        segments = transcribe(video_path, model_size=model)
        if not segments:
            segments = [{"start": 0, "end": 1, "text": "(לא זוהה דיבור)"}]
            log("⚠️ לא זוהה דיבור בסרטון")
        else:
            log(f"✓ זוהו {len(segments)} קטעים")

        log("🖼️ מחלץ פריימים...")
        enriched = extract_frames_for_segments(video_path, segments, str(frames_dir))
        log(f"✓ חולצו {len(enriched)} פריימים")

        log("🎨 בונה סטוריבורד...")
        html_path = str(output_dir / "storyboard.html")
        build_storyboard_html(enriched, html_path, video_url=url)
        log("✅ הסטוריבורד מוכן!")

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["html"] = html_path

    except Exception as e:
        log(f"❌ שגיאה: {e}")
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "error"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/start", methods=["POST"])
def start():
    data = request.get_json()
    url = data.get("url", "").strip()
    model = data.get("model", "base")
    columns = int(data.get("columns", 2))

    if not url:
        return jsonify({"error": "missing url"}), 400

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "running", "log": [], "html": None}

    t = threading.Thread(target=run_job, args=(job_id, url, model, columns), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404
    return jsonify({"status": job["status"], "log": job["log"]})


@app.route("/result/<job_id>")
def result(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job or job["status"] != "done":
        return "Job not ready", 404
    html_path = job["html"]
    with open(html_path, encoding="utf-8") as f:
        return f.read()


@app.route("/frames/<job_id>/<path:filename>")
def frames(job_id, filename):
    frames_dir = BASE_OUTPUT / job_id / "frames"
    return send_from_directory(str(frames_dir), filename)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    BASE_OUTPUT.mkdir(parents=True, exist_ok=True)
    print("\n🎬 Video Storyboard Generator")
    print("   Open http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
