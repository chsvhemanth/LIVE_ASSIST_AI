from flask import Flask, request, jsonify
from flask import send_from_directory
from flask_cors import CORS
from groq import Groq
from datetime import datetime

# ==== CONFIG ====
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"  
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

# build client if key present
client = None
if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception:
        client = None

# ==== STATE ====
meeting_active = False
customer_name = ""
conversation_log = []          # [{role, content, t}]
full_transcript_chunks = []    # [str, str, ...]

# ==== HELPERS ====
def groq_chat(system_prompt: str, user_prompt: str) -> str:
    if not client:
        return ("[CONFIG] Groq API key is missing or invalid. "
                "Edit groq_integration.py and set GROQ_API_KEY to your real key.")
    try:
        chat = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.5,
            max_tokens=900,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return chat.choices[0].message.content
    except Exception as e:
        text = str(e)
        if "401" in text or "invalid_api_key" in text:
            return "[AUTH] Invalid Groq API key. Please set a valid key and restart."
        return f"[Groq Error] {e}"

# ==== ROUTES ====
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "meeting_active": meeting_active})

@app.route("/start", methods=["POST"])
def start():
    global meeting_active, customer_name, conversation_log, full_transcript_chunks
    data = request.get_json(force=True) or {}
    customer_name = (data.get("username") or "Guest").strip()
    conversation_log = []
    full_transcript_chunks = []
    meeting_active = True
    return jsonify({"status": "started", "user": customer_name, "t": utc_now()})

@app.route("/transcribe", methods=["POST"])
def transcribe():
    global full_transcript_chunks, conversation_log
    if not meeting_active:
        return jsonify({"error": "No active meeting"}), 400
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if text:
        full_transcript_chunks.append(text)
        conversation_log.append({"role": "user", "content": text, "t": utc_now()})
    return jsonify({"ok": True})

@app.route("/end", methods=["POST"])
def end():
    global meeting_active, conversation_log
    meeting_active = False

    transcript = " ".join(full_transcript_chunks).strip()
    if not transcript:
        return jsonify({"summary": "No audio captured. Make sure Virtual Cable / Stereo Mix is selected, then try again."})

    system = (
        "You are LiveAssist AI, a domain-agnostic sales/meeting assistant. "
        "Generate an executive summary with this exact structure:\n"
        "• Overview (2–3 lines)\n"
        "• Key Points (bullets)\n"
        "• Decisions & Owners (bullets)\n"
        "• Action Items with Deadlines (bullets)\n"
        "• Risks/Concerns (bullets)\n"
        "• Overall Sentiment (1 line)\n"
        "Keep it factual, concise, and useful."
    )
    user = f"Full meeting transcript:\n{transcript}\n\nGenerate the summary exactly in that structure."

    summary = groq_chat(system, user)
    conversation_log.append({"role": "assistant", "content": summary, "t": utc_now()})
    return jsonify({"summary": summary})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"reply": "Type a question first."})

    context = " ".join(full_transcript_chunks[-30:])
    system = (
        "You are LiveAssist AI. Answer based on the meeting context. "
        "Be concise. Where helpful, add one short recommendation and a brief sentiment."
    )
    user = f"Meeting context (may be partial):\n{context}\n\nQuestion: {query}"
    reply = groq_chat(system, user)
    conversation_log.append({"role": "assistant", "content": reply, "t": utc_now()})
    return jsonify({"reply": reply})


if __name__ == "__main__":
    # pip install flask flask-cors groq
    app.run(host="0.0.0.0", port=5000, debug=False)



