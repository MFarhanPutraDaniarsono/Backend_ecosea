from flask import Blueprint, request, jsonify
from extensions import db
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
import os
import secrets

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

auth_bp = Blueprint('auth', __name__)


def _allowed_google_client_ids():
    raw = os.getenv("GOOGLE_CLIENT_IDS", "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _verify_google_id_token(token: str):
    try:
        idinfo = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
        )
    except Exception:
        return None, "Token Google tidak valid"

    allowed = _allowed_google_client_ids()
    aud = idinfo.get("aud")
    if allowed and aud not in allowed:
        return None, "Client ID tidak cocok"

    if not idinfo.get("email"):
        return None, "Email tidak ditemukan di token"
    if idinfo.get("email_verified") is False:
        return None, "Email Google belum terverifikasi"

    return idinfo, None

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json

    if not all(k in data for k in ('nama', 'email', 'password')):
        return jsonify({"message": "Data tidak lengkap"}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email sudah terdaftar"}), 400

    user = User(
        nama=data['nama'],
        email=data['email'],
        password=generate_password_hash(data['password'])
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Register berhasil"}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"message": "Email / Password salah"}), 401

    if not check_password_hash(user.password, password):
        return jsonify({"message": "Email / Password salah"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )

    return jsonify({
        "access_token": access_token,
        "nama": user.nama,
        "role": user.role
    }), 200


@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    data = request.get_json() or {}
    token = (data.get('id_token') or '').strip()

    if not token:
        return jsonify({"message": "id_token diperlukan"}), 400

    idinfo, err = _verify_google_id_token(token)
    if err:
        return jsonify({"message": err}), 401

    email = idinfo.get('email')
    nama = idinfo.get('name') or idinfo.get('given_name') or email.split('@')[0]

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            nama=nama,
            email=email,
            password=generate_password_hash(secrets.token_urlsafe(24)),
        )
        db.session.add(user)
    else:
        if not getattr(user, 'nama', None) and nama:
            user.nama = nama

    db.session.commit()

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )

    return jsonify({
        "access_token": access_token,
        "nama": user.nama,
        "role": user.role
    }), 200