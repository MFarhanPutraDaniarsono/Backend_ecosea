from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Berita, User
from extensions import db
import os
import uuid

berita_bp = Blueprint('berita', __name__)

UPLOAD_FOLDER = 'static/uploads/berita'


def _ensure_admin():
    """Pastikan user yang login adalah admin."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return None, (jsonify({"message": "Akses ditolak"}), 403)
    return user, None


def _save_image(file_storage):
    ext = os.path.splitext(file_storage.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_storage.save(os.path.join(UPLOAD_FOLDER, filename))
    return filename


def _delete_image(filename):
    if not filename:
        return
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)


# ===============================
# TAMBAH BERITA (ADMIN)
# ===============================
@berita_bp.route('/berita', methods=['POST'])
@jwt_required()
def tambah_berita():
    _, err = _ensure_admin()
    if err:
        return err

    judul = (request.form.get('judul') or '').strip()
    isi = (request.form.get('isi') or '').strip()
    file = request.files.get('gambar')

    if not judul or not isi:
        return jsonify({"message": "Judul dan isi wajib diisi"}), 400

    filename = None
    if file and file.filename:
        filename = _save_image(file)

    berita = Berita(
        judul=judul,
        isi=isi,
        gambar=filename
        # created_at otomatis dari model
    )

    db.session.add(berita)
    db.session.commit()

    return jsonify({"message": "Berita berhasil disimpan", "id": berita.id}), 201


# ===============================
# LIST BERITA (USER / FLUTTER)
# ===============================
@berita_bp.route('/berita', methods=['GET'])
def list_berita():
    data = Berita.query.order_by(Berita.created_at.desc()).all()

    return jsonify([
        {
            "id": b.id,
            "judul": b.judul,
            "isi": b.isi,
            "gambar": f"/static/uploads/berita/{b.gambar}" if b.gambar else None,
            "created_at": b.created_at.isoformat()
        } for b in data
    ])


# ===============================
# UPDATE BERITA (ADMIN)
# ===============================
@berita_bp.route('/berita/<int:id>', methods=['PUT'])
@jwt_required()
def update_berita(id):
    _, err = _ensure_admin()
    if err:
        return err

    berita = Berita.query.get_or_404(id)

    # Terima dari form-data (admin web) atau JSON
    judul = None
    isi = None
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        judul = payload.get('judul')
        isi = payload.get('isi')
    else:
        judul = request.form.get('judul')
        isi = request.form.get('isi')

    changed = False

    if judul is not None:
        judul = judul.strip()
        if not judul:
            return jsonify({"message": "Judul tidak boleh kosong"}), 400
        berita.judul = judul
        changed = True

    if isi is not None:
        isi = isi.strip()
        if not isi:
            return jsonify({"message": "Isi tidak boleh kosong"}), 400
        berita.isi = isi
        changed = True

    file = request.files.get('gambar')
    if file and file.filename:
        _delete_image(berita.gambar)
        berita.gambar = _save_image(file)
        changed = True

    if not changed:
        return jsonify({"message": "Tidak ada data untuk diupdate"}), 400

    db.session.commit()
    return jsonify({"message": "Berita berhasil diupdate"}), 200


# ===============================
# HAPUS BERITA (ADMIN)
# ===============================
@berita_bp.route('/berita/<int:id>', methods=['DELETE'])
@jwt_required()
def hapus_berita(id):
    _, err = _ensure_admin()
    if err:
        return err

    berita = Berita.query.get_or_404(id)

    # hapus file gambar jika ada
    _delete_image(berita.gambar)

    db.session.delete(berita)
    db.session.commit()

    return jsonify({"message": "Berita berhasil dihapus"}), 200
