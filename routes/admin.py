from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import User, Laporan
from extensions import db
from werkzeug.security import check_password_hash

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()

    user = User.query.filter_by(email=data['email']).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"msg": "Login gagal"}), 401

    if user.role != 'admin':
        return jsonify({"msg": "Bukan admin"}), 403

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": token
    }), 200


@admin_bp.route('/admin/laporan', methods=['GET'])
@jwt_required()
def get_all_laporan():
    laporan = Laporan.query.order_by(Laporan.tanggal.desc()).all()

    return jsonify([
        {
            "id": l.id,
            "nama": l.user.nama,
            "judul": l.judul,
            "deskripsi": l.deskripsi,
            "status": l.status,
            "foto": l.foto,
            "tanggal": l.tanggal.strftime("%Y-%m-%d %H:%M")
        } for l in laporan
    ]), 200

@admin_bp.route('/admin/laporan/<int:id>', methods=['GET'])
@jwt_required()
def detail_laporan(id):
    l = Laporan.query.get_or_404(id)

    return jsonify({
        "id": l.id,
        "nama": l.user.nama,
        "judul": l.judul,
        "deskripsi": l.deskripsi,
        "status": l.status,
        "tanggapan": l.tanggapan,
        "foto": l.foto
    })

@admin_bp.route('/admin/laporan/<int:id>/tanggapi', methods=['PUT'])
@jwt_required()
def tanggapi_laporan(id):
    data = request.get_json()

    l = Laporan.query.get_or_404(id)
    l.status = data['status']
    l.tanggapan = data['tanggapan']

    db.session.commit()

    return jsonify({"msg": "Laporan ditanggapi"}), 200

@admin_bp.route('/admin/users', methods=['GET'])
@jwt_required()
def list_users():
    users = User.query.order_by(User.id.desc()).all()
    return jsonify([
        {
            'id': u.id,
            'nama': u.nama,
            'email': u.email,
            'role': u.role,
            'created_at': (u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else None)} for u in users
    ]), 200
