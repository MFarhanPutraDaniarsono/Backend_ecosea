from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests

chat_bp = Blueprint("chat", __name__)

def _to_gemini_contents(history):

    contents = []
    if not isinstance(history, list):
        return contents

    for item in history[-12:]:
        if not isinstance(item, dict):
            continue

        role = (item.get("role") or "").strip()
        text = (item.get("text") or "").strip()
        if not text:
            continue

        gem_role = "user" if role == "user" else "model"
        contents.append({
            "role": gem_role,
            "parts": [{"text": text}]
        })

    return contents


@chat_bp.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    _ = get_jwt_identity()

    data = request.get_json(silent=True) or {}

    user_message = (data.get("message") or "").strip()
    system_prompt = (data.get("system_prompt") or "").strip()
    history = data.get("history", [])

    if not user_message and (not isinstance(history, list) or len(history) == 0):
        return jsonify({"message": "Pesan kosong"}), 400

    api_key = current_app.config.get("GEMINI_API_KEY")
    model = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")

    if model.startswith("models/"):
        model = model.replace("models/", "", 1)

    if not api_key:
        return jsonify({"message": "GEMINI_API_KEY belum diset di backend (.env)"}), 500

    contents = _to_gemini_contents(history[-6:])

    if user_message:
        if not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != user_message:
            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt or "Kamu adalah EcoSea."}]
        },
        "contents": contents
    }

    print("DEBUG GEMINI KEY:", api_key[:6] if api_key else "NONE")
    print("DEBUG MODEL:", model)

    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=30
        )
    except requests.RequestException as e:
        return jsonify({"message": "Gagal menghubungi Gemini API", "detail": str(e)}), 502

    if resp.status_code != 200:
        return jsonify({
            "message": "Gemini API error",
            "status": resp.status_code,
            "detail": resp.text
        }), 502

    data = resp.json()

    reply_text = ""
    try:
        reply_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        try:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            reply_text = "".join([p.get("text", "") for p in parts]).strip()
        except Exception:
            reply_text = ""

    if not reply_text:
        reply_text = "Maaf, aku belum bisa menjawab itu."

    return jsonify({"reply": reply_text}), 200