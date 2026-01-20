from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Review
from routes.admin_utils import admin_required


ulasan_bp = Blueprint('ulasan', __name__)


def _sentiment_from_rating(rating: int) -> str:
    if rating <= 2:
        return 'negatif'
    if rating == 3:
        return 'netral'
    return 'positif'


@ulasan_bp.route('/ulasan', methods=['POST'])
@jwt_required()
def kirim_ulasan():
    """User mengirim ulasan (rating + kritik/saran)."""
    data = request.get_json(silent=True) or {}

    rating = data.get('rating', None)
    kritik = (data.get('kritik') or '').strip()
    saran = (data.get('saran') or '').strip()

    if rating is None:
        return jsonify({"message": "Rating wajib diisi"}), 400

    try:
        rating = int(rating)
    except Exception:
        return jsonify({"message": "Rating harus berupa angka"}), 400

    if rating < 1 or rating > 5:
        return jsonify({"message": "Rating harus 1 sampai 5"}), 400

    if not kritik and not saran:
        return jsonify({"message": "Kritik atau saran wajib diisi (minimal salah satu)"}), 400

    user_id = int(get_jwt_identity())

    ulasan = Review(
        user_id=user_id,
        rating=rating,
        kritik=kritik or None,
        saran=saran or None,
        sentiment=_sentiment_from_rating(rating),
    )

    db.session.add(ulasan)
    db.session.commit()

    return jsonify({
        "message": "Ulasan berhasil dikirim",
        "id": ulasan.id,
        "sentiment": ulasan.sentiment,
        "created_at": ulasan.created_at.strftime("%Y-%m-%d %H:%M"),
    }), 201


@ulasan_bp.route('/ulasan', methods=['GET'])
@jwt_required()
@admin_required
def list_ulasan():
    """Admin mengambil semua ulasan untuk ditampilkan di web."""
    rows = Review.query.order_by(Review.created_at.desc()).all()

    return jsonify([
        {
            "id": r.id,
            "user_id": r.user_id,
            "nama": r.user.nama if r.user else "-",
            "email": r.user.email if r.user else "-",
            "rating": r.rating,
            "kritik": r.kritik or "",
            "saran": r.saran or "",
            "sentiment": r.sentiment,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
        } for r in rows
    ]), 200
