from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import time

user_bp = Blueprint("user", __name__)


def _get_current_user():
    """Get logged-in user from JWT. Returns (user, error_response).

    error_response is a tuple (json, status_code) or None.
    """
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except Exception:
        user_id_int = user_id

    user = User.query.get(user_id_int)
    if not user:
        return None, (jsonify({"message": "User tidak ditemukan"}), 404)
    return user, None


def _profile_json(user: User):
    photo_path = f"/uploads/profile/{user.foto_profil}" if getattr(user, "foto_profil", None) else ""
    return {
        "id": user.id,
        "name": user.nama,
        "email": user.email,
        "photo_url": photo_path,
    }


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user, err = _get_current_user()
    if err:
        return err

    return jsonify(_profile_json(user)), 200


@user_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_me():
    """Update basic profile fields (currently only name)."""
    user, err = _get_current_user()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    if not name:
        return jsonify({"message": "Nama tidak boleh kosong"}), 400

    if len(name) > 100:
        return jsonify({"message": "Nama terlalu panjang"}), 400

    user.nama = name
    db.session.commit()

    return jsonify({"message": "Profil berhasil diperbarui", "user": _profile_json(user)}), 200


@user_bp.route("/me/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user, err = _get_current_user()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    old_password = (data.get("old_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not old_password or not new_password:
        return jsonify({"message": "old_password dan new_password wajib diisi"}), 400

    if len(new_password) < 6:
        return jsonify({"message": "Password baru minimal 6 karakter"}), 400

    if not check_password_hash(user.password, old_password):
        return jsonify({"message": "Password lama salah"}), 400

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Password berhasil diganti"}), 200


@user_bp.route("/me/photo", methods=["POST"])
@jwt_required()
def upload_profile_photo():
    user, err = _get_current_user()
    if err:
        return err

    if "photo" not in request.files:
        return jsonify({"message": "Field file 'photo' tidak ditemukan"}), 400

    file = request.files["photo"]
    if not file or not file.filename:
        return jsonify({"message": "File foto tidak valid"}), 400

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    if ext not in allowed:
        return jsonify({"message": "Format foto harus jpg/jpeg/png/webp"}), 400

    ts = int(time.time())
    save_name = f"{user.id}_{ts}{ext}"
    save_dir = current_app.config.get("PROFILE_UPLOAD_FOLDER")
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, save_name)
    file.save(save_path)

    # Optional: remove old photo file to avoid orphan files
    old = getattr(user, "foto_profil", None)
    if old and old != save_name:
        try:
            old_path = os.path.join(save_dir, old)
            if os.path.exists(old_path):
                os.remove(old_path)
        except Exception:
            pass

    user.foto_profil = save_name
    db.session.commit()

    return jsonify({
        "message": "Foto profil berhasil diperbarui",
        "user": _profile_json(user),
    }), 200
