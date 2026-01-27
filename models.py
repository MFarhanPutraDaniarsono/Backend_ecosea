from extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), default='user')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    foto_profil = db.Column(db.String(255))

    laporan = db.relationship('Laporan', backref='user', lazy=True)
    ulasan = db.relationship('Review', backref='user', lazy=True)


class Laporan(db.Model):
    __tablename__ = 'laporan'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tanggal = db.Column(db.DateTime, default=datetime.utcnow)
    lokasi = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    judul = db.Column(db.String(150))
    deskripsi = db.Column(db.Text)
    foto = db.Column(db.String(255))
    status = db.Column(db.String(20), default='menunggu')
    tanggapan = db.Column(db.Text)
    ai_label = db.Column(db.String(20))       
    ai_confidence = db.Column(db.Float)       


class Berita(db.Model):
    __tablename__ = 'berita'

    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(255), nullable=False)
    isi = db.Column(db.Text, nullable=False)
    gambar = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    rating = db.Column(db.Integer, nullable=False)
    kritik = db.Column(db.Text)
    saran = db.Column(db.Text)

    sentiment = db.Column(db.String(20), default='netral')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
