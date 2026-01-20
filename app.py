from flask import Flask, send_from_directory, current_app
from config import Config
from extensions import db, jwt

from routes.admin_web import admin_web_bp
from routes.laporan import laporan_bp
from routes.admin import admin_bp
from routes.user import user_bp
from routes.chat import chat_bp
from routes.auth import auth_bp
from routes.berita import berita_bp
from routes.ulasan import ulasan_bp
from flask_cors import CORS
import os

app = Flask(__name__)
app.config.from_object(Config)

app.secret_key = "web-admin-secret"

app.register_blueprint(berita_bp, url_prefix='/api')

CORS(app, resources={r"/api/*": {"origins": "*"}})

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
jwt.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(laporan_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api')
app.register_blueprint(chat_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(ulasan_bp, url_prefix="/api")

app.register_blueprint(admin_web_bp)

@app.route('/uploads/laporan/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
