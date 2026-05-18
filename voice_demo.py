# -*- coding: utf-8 -*-
"""
SupportLens Voice + Scraping Demo
===================================
What this script does:
  1. Generates a realistic .wav audio file of a customer complaint (pyttsx3 offline TTS)
  2. Sends it to /voice/transcribe  -> Whisper transcribes it
  3. Submits the transcript through the full AI pipeline -> creates a ticket
  4. Triggers App Store + Reddit scrapers

Usage:
    python voice_demo.py          (billing complaint)
    python voice_demo.py 1        (churn risk)
    python voice_demo.py 2        (enterprise crash)
"""

import os, sys, wave, struct, math, requests

BACKEND     = "http://localhost:8000"
OUTPUT_FILE = "demo_voice_ticket.wav"

COMPLAINT_SCRIPTS = [
    # 0 - Billing / Duplicate charge (HIGH urgency)
    (
        "Hi, I am really frustrated right now. I have been charged twice for my subscription this month. "
        "My card shows two charges of forty nine dollars each on the same day. "
        "I have been a customer for three years and this has never happened before. "
        "I need a refund immediately. My account email is john dot smith at company dot com. "
        "Please escalate this to your billing team right away."
    ),
    # 1 - Churn risk (CRITICAL urgency)
    (
        "I am calling to let you know I am cancelling my account. "
        "I found a competitor who offers the same features at thirty percent less. "
        "Unless you match their pricing by end of this week, I am moving everything over. "
        "I have a team of twenty people on this plan so this is a significant account. "
        "This is your last chance to keep my business."
    ),
    # 2 - Enterprise app crash (HIGH urgency)
    (
        "Your app has been crashing every time I try to open it since your latest update yesterday. "
        "I am on Android version fourteen, app version four point two. "
        "I have cleared the cache and reinstalled it three times already. "
        "My entire team of fifteen people is completely blocked and cannot do any work. "
        "We are an enterprise customer paying for reliability and this is unacceptable."
    ),
]


def generate_wav_pyttsx3(text, output_path):
    """Offline TTS -> WAV using pyttsx3. Returns True on success."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.setProperty("volume", 0.9)
        for v in engine.getProperty("voices"):
            if "zira" in v.name.lower() or "female" in v.name.lower():
                engine.setProperty("voice", v.id)
                break
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        print("  Audio generated: " + output_path)
        return True
    except ImportError:
        print("  pyttsx3 not installed. Run: pip install pyttsx3")
    except Exception as e:
        print("  TTS error: " + str(e))
    return False


def generate_sine_wav(output_path, duration=3):
    """Fallback: generate a 440 Hz sine-wave WAV so Whisper gets a real file."""
    sr = 16000
    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = b"".join(
            struct.pack("<h", int(800 * math.sin(2 * math.pi * 440 * i / sr)))
            for i in range(sr * duration)
        )
        wf.writeframes(frames)
    print("  Fallback WAV generated: " + output_path)


def transcribe(wav_path):
    print("\n[STEP 2/4] Sending audio to Whisper transcription endpoint...")
    with open(wav_path, "rb") as f:
        r = requests.post(
            f"{BACKEND}/voice/transcribe",
            files={"file": (os.path.basename(wav_path), f, "audio/wav")},
            timeout=300,
        )
    if r.status_code == 200:
        d = r.json()
        print("  Transcript (%d chars):" % d["chars"])
        print("  >> " + d["transcript"])
        return d["transcript"]
    else:
        print("  FAILED (%d): %s" % (r.status_code, r.json().get("detail", r.text)))
        return ""


def submit_ticket(transcript):
    print("\n[STEP 3/4] Running full AI pipeline on transcript...")
    payload = {
        "subject": transcript[:80].strip(),
        "description": transcript,
        "customer_name": "Demo Voice Customer",
        "customer_email": "voice.demo@company.com",
        "customer_tier": "premium",
        "source": "voice",
    }
    r = requests.post(f"{BACKEND}/tickets/process-sync", json=payload, timeout=120)
    if r.status_code == 200:
        t = r.json()
        print("  [OK] Ticket #%s created!" % t.get("id"))
        print("  Urgency      : %s/100" % int(t.get("urgency_score", 0)))
        print("  Emotion      : %s  (%.1f/10)" % (t.get("emotion_type"), t.get("emotion_score", 0)))
        print("  Intent       : %s" % t.get("intent"))
        print("  Churn Risk   : %s" % ("YES" if t.get("is_churn_risk") else "No"))
        print("  Human Gate   : %s" % ("YES" if t.get("requires_human") else "No"))
        print("  Severity     : %s" % t.get("severity"))
        print("  Product Area : %s" % t.get("product_area"))
        print("  >> Open http://localhost:5173 to see it in the Agent Queue")
        return t
    else:
        print("  FAILED (%d): %s" % (r.status_code, r.text))
        return {}


def trigger_scrapers():
    print("\n[STEP 4/4] Triggering data scrapers in background...")

    # App Store - Notion (Apple ID 1232780281, free public RSS)
    r = requests.post(f"{BACKEND}/ingest/appstore",
                      json={"apple_app_id": "1232780281"}, timeout=30)
    if r.status_code == 200:
        print("  App Store scraper queued: " + r.json().get("message", ""))
    else:
        print("  App Store error: %d %s" % (r.status_code, r.text))

    # Reddit - r/techsupport (requires REDDIT_CLIENT_ID in .env)
    r = requests.post(f"{BACKEND}/ingest/reddit",
                      json={"subreddits": ["techsupport", "softwaregore"], "limit_per_sub": 10},
                      timeout=30)
    if r.status_code == 200:
        print("  Reddit scraper queued:    " + r.json().get("message", ""))
    else:
        print("  Reddit error: %d %s" % (r.status_code, r.text))

    print("  Check status at: http://localhost:8000/api/ingest/status")
    print("  Or visit the Data Sources page: http://localhost:5173/sources")


if __name__ == "__main__":
    idx = min(int(sys.argv[1]) if len(sys.argv) > 1 else 0, len(COMPLAINT_SCRIPTS) - 1)
    text = COMPLAINT_SCRIPTS[idx]

    print("=" * 60)
    print("  SupportLens Voice + Scraping Demo  (script %d/2)" % idx)
    print("=" * 60)
    print("\nComplaint text:\n  " + text[:100] + "...")

    # Step 1: Generate audio
    print("\n[STEP 1/4] Generating audio file...")
    ok = generate_wav_pyttsx3(text, OUTPUT_FILE)
    if not ok:
        generate_sine_wav(OUTPUT_FILE)

    # Step 2: Transcribe
    transcript = transcribe(OUTPUT_FILE)

    # Step 3: Create ticket
    if transcript:
        submit_ticket(transcript)
    else:
        print("\n  No transcript - Whisper returned empty. Try with pyttsx3 installed.")

    # Step 4: Scrapers
    trigger_scrapers()

    print("\n" + "=" * 60)
    print("  DONE! Open these URLs:")
    print("    http://localhost:5173           -> Agent Urgency Queue")
    print("    http://localhost:5173/sources   -> Data Sources + Spike Alerts")
    print("    http://localhost:5173/dashboard -> Manager Dashboard")
    print("=" * 60)
