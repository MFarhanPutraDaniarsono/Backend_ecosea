from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from extensions import db
from models import Laporan, User
from ai.predict import predict_image
import os
import time

laporan_bp = Blueprint('laporan', __name__)


@laporan_bp.route('/laporan', methods=['POST'])
@jwt_required()
def kirim_laporan():
    foto = request.files.get('foto')
    if not foto:
        return jsonify({"message": "Foto laporan wajib diupload"}), 400

    
    filename = f"{int(time.time())}_{secure_filename(foto.filename)}"
    foto_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    foto.save(foto_path)

    ai_result = predict_image(foto_path)

    
    laporan = Laporan(
        user_id=get_jwt_identity(),
        judul=request.form['judul'],
        deskripsi=request.form['deskripsi'],
        lokasi=request.form['lokasi'],
        latitude=float(request.form['latitude']),
        longitude=float(request.form['longitude']),
        foto=filename,
        ai_label=ai_result["label"],
        ai_confidence=ai_result["confidence"],
        status="pending"
    )

    db.session.add(laporan)
    db.session.commit()

    return jsonify({
        "message": "Laporan berhasil dikirim",
        "ai_label": ai_result["label"],
        "ai_confidence": ai_result["confidence"]
    }), 201


@laporan_bp.route('/laporan/<int:laporan_id>/tanggapi', methods=['PUT'])
@jwt_required()
def tanggapi_laporan(laporan_id):
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user or user.role != 'admin':
        return jsonify({"message": "Akses ditolak"}), 403

    laporan = Laporan.query.get(laporan_id)
    if not laporan:
        return jsonify({"message": "Laporan tidak ditemukan"}), 404

    data = request.get_json()
    laporan.tanggapan = data.get('tanggapan')
    laporan.status = data.get('status', laporan.status)

    db.session.commit()

    return jsonify({"message": "Laporan berhasil ditanggapi"}), 200


@laporan_bp.route('/laporan/user', methods=['GET'])
@jwt_required()
def get_laporan_user():
    user_id = int(get_jwt_identity())

    laporan_list = Laporan.query.filter_by(
        user_id=user_id
    ).order_by(Laporan.tanggal.desc()).all()

    data = []
    for l in laporan_list:
        data.append({
            "id": l.id,
            "judul": l.judul,
            "deskripsi": l.deskripsi,
            "lokasi": l.lokasi,
            "latitude": l.latitude,
            "longitude": l.longitude,
            "foto": f"/uploads/laporan/{l.foto}",
            "status": l.status,
            "tanggapan": l.tanggapan,
            "ai_label": l.ai_label,
            "ai_confidence": l.ai_confidence,
            "tanggal": l.tanggal.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify(data), 200


@laporan_bp.route('/laporan', methods=['GET'])
@jwt_required()
def get_all_laporan():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if user.role != 'admin':
        return jsonify({"message": "Akses ditolak"}), 403

    laporan_list = Laporan.query.order_by(Laporan.tanggal.desc()).all()

    data = []
    for l in laporan_list:
        data.append({
            "id": l.id,
            "nama": l.user.nama,
            "judul": l.judul,
            "deskripsi": l.deskripsi,
            "lokasi": l.lokasi,
            "latitude": l.latitude,
            "longitude": l.longitude,
            "foto": f"/uploads/laporan/{l.foto}",
            "status": l.status,
            "tanggapan": l.tanggapan,
            "ai_label": l.ai_label,
            "ai_confidence": l.ai_confidence,
            "tanggal": l.tanggal.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify(data), 200


@laporan_bp.route('/laporan/terbaru', methods=['GET'])
@jwt_required()
def get_laporan_terbaru():
    limit = request.args.get('limit', default=5, type=int)
    limit = max(1, min(limit, 20))

    laporan_list = Laporan.query.order_by(
        Laporan.tanggal.desc()
    ).limit(limit).all()

    data = []
    for l in laporan_list:
        data.append({
            "id": l.id,
            "nama": l.user.nama,
            "judul": l.judul,
            "deskripsi": l.deskripsi,
            "lokasi": l.lokasi,
            "latitude": l.latitude,
            "longitude": l.longitude,
            "foto": f"/uploads/laporan/{l.foto}",
            "status": l.status,
            "tanggapan": l.tanggapan,
            "ai_label": l.ai_label,
            "ai_confidence": l.ai_confidence,
            "tanggal": l.tanggal.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify(data), 200
