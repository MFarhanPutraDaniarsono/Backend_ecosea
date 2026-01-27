from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ai.rag.rag_engine import answer_question


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    # identity saat ini tidak dipakai untuk RAG, tapi tetap wajib login
    _ = get_jwt_identity()

    data = request.get_json(silent=True) or {}

    user_message = (data.get("message") or "").strip()
    history = data.get("history", [])

    if not user_message and (not isinstance(history, list) or len(history) == 0):
        return jsonify({"message": "Pesan kosong"}), 400

    try:
        res = answer_question(user_message, history=history if isinstance(history, list) else None)
    except Exception as e:
        # Fail-safe: jangan bocorin detail stacktrace ke client.
        return jsonify({
            "message": "Gagal memproses chat RAG",
            "detail": str(e)
        }), 500

    return jsonify({
        "reply": res.reply,
        "contexts": res.contexts,
    }), 200
