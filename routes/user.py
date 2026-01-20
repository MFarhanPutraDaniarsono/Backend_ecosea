from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User  # sesuaikan nama model user kamu

user_bp = Blueprint("user", __name__)

@user_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User tidak ditemukan"}), 404

    return jsonify({
        "id": user.id,
        "name": user.nama,
        "email": user.email
    }), 200