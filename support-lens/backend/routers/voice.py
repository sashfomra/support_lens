"""
Voice transcription router — accepts audio file uploads and transcribes with Whisper.
Supported formats: .mp3, .wav, .ogg, .m4a, .webm, .flac
Model: openai-whisper base (free, local, no API key needed)
"""
import os
import re
import json
import logging
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".webm", ".flac"}
MAX_FILE_MB = 25


def _find_ffmpeg() -> str:
    """Find absolute path to ffmpeg.exe."""
    import shutil, glob as _g
    found = shutil.which("ffmpeg")
    if found:
        return found
    localappdata = os.environ.get("LOCALAPPDATA", "")
    for exe in _g.glob(f"{localappdata}/Microsoft/WinGet/Packages/**/ffmpeg.exe", recursive=True):
        return exe
    for p in ["C:/ffmpeg/bin/ffmpeg.exe", "C:/Program Files/ffmpeg/bin/ffmpeg.exe"]:
        if os.path.exists(p):
            return p
    return "ffmpeg"


def _transcribe(file_path: str) -> str:
    """Convert audio to WAV via ffmpeg subprocess, then transcribe with Whisper."""
    import subprocess, numpy as np, wave, struct

    ffmpeg = _find_ffmpeg()
    logger.info(f"ffmpeg: {ffmpeg}")

    # Step 1: Use ffmpeg to decode any format → raw 16-bit PCM mono 16kHz
    wav_tmp = file_path + "_converted.wav"
    try:
        result = subprocess.run(
            [ffmpeg, "-y", "-i", file_path, "-ac", "1", "-ar", "16000",
             "-sample_fmt", "s16", "-f", "wav", wav_tmp],
            capture_output=True, timeout=120
        )
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            logger.error(f"ffmpeg conversion failed: {err}")
            raise HTTPException(status_code=500, detail=f"Audio conversion failed: {err[:200]}")

        # Step 2: Load the WAV and convert to float32 numpy array
        with wave.open(wav_tmp, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

        # Step 3: Transcribe using numpy array (no ffmpeg needed by Whisper)
        import whisper
        model = whisper.load_model("base")
        result2 = model.transcribe(audio, fp16=False)
        return result2["text"].strip()

    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=503, detail="Whisper not installed. Run: pip install openai-whisper")
    except Exception as e:
        logger.error(f"Transcription error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        try:
            os.unlink(wav_tmp)
        except Exception:
            pass




# ── Metadata extraction ───────────────────────────────────────────────────────
def _extract_metadata(transcript: str) -> dict:
    email = None
    name = None
    subject = None

    # Email — direct match
    m = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', transcript)
    if m:
        email = m.group(0).strip().lower()
    if not email:
        m = re.search(r'(\b[\w.-]+)\s+at\s+([\w-]+\.(?:com|org|net|io|co|in|uk))', transcript, re.IGNORECASE)
        if m:
            email = f"{m.group(1).split()[-1].lower()}@{m.group(2).lower()}"
    if not email:
        m = re.search(r'(\b[\w.-]+)\s+at\s+the\s+rate\s+([\w-]+)\s+dot\s+(com|org|net|io|co|in|uk)', transcript, re.IGNORECASE)
        if m:
            email = f"{m.group(1).split()[-1].lower()}@{m.group(2).lower()}.{m.group(3).lower()}"
    if not email:
        m = re.search(r'(\b[\w.-]+)\s+at\s+([\w-]+)\s+dot\s+(com|org|net|io|co|in|uk)', transcript, re.IGNORECASE)
        if m:
            email = f"{m.group(1).split()[-1].lower()}@{m.group(2).lower()}.{m.group(3).lower()}"

    # Name
    m = re.search(r"(?:my name is|i(?:'m| am))\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", transcript, re.IGNORECASE)
    if m:
        name = m.group(1).strip()

    # Groq — extract name, email, AND generate a clean subject title
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            prompt = f"""You are a support ticket classifier. Read this voice transcript and extract:
1. Customer name (or null)
2. Customer email (or null)  
3. A SHORT ticket subject — exactly 5 to 7 words that describe the PROBLEM. 
   Write it like a bug title: "Stripe webhook not delivering payment events"
   DO NOT copy sentences from the transcript. Summarize the core issue concisely.

Reply ONLY with this JSON (no extra text):
{{"name": "Ram", "email": "ram@gmail.com", "subject": "Stripe webhook not sending payment events"}}

Transcript:
{transcript}

JSON:"""
            resp = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=120,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown code fences if present
            raw = re.sub(r'^```[a-z]*\n?', '', raw).strip('`').strip()
            # Extract just the JSON object
            json_match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if parsed.get("name") and str(parsed["name"]).lower() not in ("null", "none", ""):
                    name = parsed["name"]
                if parsed.get("email") and str(parsed["email"]).lower() not in ("null", "none", ""):
                    email = parsed["email"]
                if parsed.get("subject") and str(parsed["subject"]).lower() not in ("null", "none", ""):
                    subject = parsed["subject"]
        except Exception as e:
            logger.warning(f"Groq extraction failed: {e}")

    # Subject fallback — build from key nouns/verbs, not raw sentence
    if not subject:
        # Try to extract the core problem clause
        problem_patterns = [
            r'(?:issue|problem|error|trouble)\s+(?:is\s+)?(?:that\s+)?(.{10,60}?)(?:\.|,|$)',
            r'(?:not\s+(?:working|sending|receiving|loading|connecting))(.{0,40}?)(?:\.|,|$)',
            r'(?:keeps?\s+(?:failing|crashing|timing out))(.{0,40}?)(?:\.|,|$)',
        ]
        for pat in problem_patterns:
            m = re.search(pat, transcript, re.IGNORECASE)
            if m:
                subject = m.group(0).strip()[:65]
                break
        if not subject:
            # Last resort: first meaningful sentence
            sentences = re.split(r'(?<=[.!?])\s+', transcript)
            for s in sentences[1:]:  # skip greeting
                if len(s) > 15:
                    subject = s.strip()[:65]
                    break
        if not subject:
            subject = transcript[:65].strip()

    return {"name": name, "email": email, "subject": subject}




# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(413, f"File too large ({size_mb:.1f}MB). Max: {MAX_FILE_MB}MB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        transcript = _transcribe(tmp_path)
        meta = _extract_metadata(transcript)
        return {
            "transcript": transcript,
            "filename": file.filename,
            "size_mb": round(size_mb, 2),
            "chars": len(transcript),
            "suggested_subject": meta["subject"],
            "suggested_name": meta["name"],
            "suggested_email": meta["email"],
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/transcribe-and-process")
async def transcribe_and_process(
    file: UploadFile = File(...),
    customer_name: str = "Voice Ticket",
    customer_email: str = "voice@support.local",
    customer_tier: str = "standard",
):
    transcript_result = await transcribe_audio(file)
    transcript = transcript_result["transcript"]
    try:
        from ai.pipeline import process_ticket
        result = await process_ticket(
            subject=f"[Voice] {transcript[:60]}...",
            description=transcript,
            customer_tier=customer_tier,
            run_llm=True,
        )
        return {"transcript": transcript, "pipeline_result": result,
                "suggested_subject": transcript[:80].strip(), "suggested_description": transcript}
    except Exception as e:
        logger.error(f"Pipeline error after transcription: {e}")
        return {"transcript": transcript, "pipeline_result": None,
                "suggested_subject": transcript[:80].strip(), "suggested_description": transcript}
