from flask import Blueprint, render_template, request, redirect, url_for, session
import requests
import os

admin_web_bp = Blueprint('admin_web', __name__)

def _api_base():
    return os.getenv("API_BASE") or (request.host_url.rstrip("/") + "/api")

def _require_token():
    token = session.get('token')
    if not token:
        return None
    return token

def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _redirect_login_if_unauthorized(res):
    """Redirect ke halaman login kalau token tidak valid/expired.

    API biasanya mengembalikan 401 dengan JSON: {"msg": "Token has expired"}.
    Kita redirect untuk semua response unauthorized (401/422) agar UX lebih rapi.
    """
    if res is None:
        return None

    if res.status_code not in (401, 422):
        return None

    # Coba ambil pesan error (kalau ada)
    msg = ""
    try:
        j = res.json() or {}
        msg = str(j.get("msg") or j.get("message") or "")
    except Exception:
        msg = str(res.text or "")

    # Kalau unauthorized (termasuk token expired), bersihkan session lalu login
    if msg or res.status_code in (401, 422):
        session.clear()
        return redirect(url_for('admin_web.admin_login'))

    return None


# ===============================
# HOME
# ===============================
@admin_web_bp.route('/')
def home():
    try:
        return render_template('public/index.html')
    except Exception:
        return redirect(url_for('admin_web.dashboard'))


# ===============================
# LOGIN ADMIN
# ===============================
@admin_web_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email') or request.form.get('username')
        password = request.form.get('password')

        res = requests.post(
            f"{_api_base()}/admin/login",
            json={"email": email, "password": password}
        )

        if res.status_code == 200:
            data = res.json()
            session['token'] = data.get('access_token')
            return redirect(url_for('admin_web.dashboard'))

        return f"Login admin gagal: {res.text}", 401

    return render_template('admin/login.html')


# ===============================
# DASHBOARD
# ===============================
@admin_web_bp.route('/admin/dashboard')
def dashboard():
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    res = requests.get(f"{_api_base()}/laporan", headers=_headers(token))
    redir = _redirect_login_if_unauthorized(res)
    if redir:
        return redir
    if res.status_code != 200:
        return f"Gagal ambil data laporan<br>{res.text}", 500

    laporan = res.json()

    def norm(s):
        return (s or "").strip().lower()

    total = len(laporan)
    menunggu = diproses = selesai = 0

    for x in laporan:
        status = norm(x.get("status"))
        if status in ["terkirim", "menunggu"]:
            menunggu += 1
        elif status in ["dalam proses", "diproses"]:
            diproses += 1
        elif status == "selesai":
            selesai += 1

    return render_template(
        'admin/dashboard.html',
        total=total,
        menunggu=menunggu,
        diproses=diproses,
        selesai=selesai
    )


# ===============================
# LAPORAN MASYARAKAT
# ===============================
@admin_web_bp.route('/admin/reports')
def reports():
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    res = requests.get(f"{_api_base()}/laporan", headers=_headers(token))
    redir = _redirect_login_if_unauthorized(res)
    if redir:
        return redir
    if res.status_code != 200:
        return f"Gagal ambil data laporan<br>{res.text}", 500

    return render_template('admin/reports.html', reports=res.json())


# ===============================
# DETAIL LAPORAN
# ===============================
@admin_web_bp.route('/admin/laporan/<int:id>', methods=['GET', 'POST'])
def detail_laporan(id):
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    headers = _headers(token)

    if request.method == 'POST':
        put_res = requests.put(
            f"{_api_base()}/laporan/{id}/tanggapi",
            headers=headers,
            json={
                "status": request.form.get('status'),
                "tanggapan": request.form.get('tanggapan')
            }
        )
        redir = _redirect_login_if_unauthorized(put_res)
        if redir:
            return redir
        return redirect(url_for('admin_web.reports'))

    res = requests.get(f"{_api_base()}/laporan/{id}", headers=headers)
    redir = _redirect_login_if_unauthorized(res)
    if redir:
        return redir
    if res.status_code != 200:
        return f"Gagal ambil detail laporan<br>{res.text}", 500

    return render_template('admin/detail.html', laporan=res.json())


# ===============================
# AKUN USER
# ===============================
@admin_web_bp.route('/admin/users')
def users():
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    res = requests.get(f"{_api_base()}/admin/users", headers=_headers(token))
    redir = _redirect_login_if_unauthorized(res)
    if redir:
        return redir
    if res.status_code != 200:
        return f"Gagal ambil data user<br>{res.text}", 500

    return render_template('admin/users.html', users=res.json(), error=None)


# ===============================
# BERITA (LIST + TAMBAH)
# ===============================
@admin_web_bp.route('/admin/news', methods=['GET', 'POST'])
def news():
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    if request.method == 'POST':
        files = {}
        if request.files.get('gambar'):
            files['gambar'] = request.files['gambar']

        data = {
            'judul': request.form.get('judul'),
            'isi': request.form.get('isi')
        }

        res = requests.post(
            f"{_api_base()}/berita",
            headers=_headers(token),
            data=data,
            files=files
        )

        redir = _redirect_login_if_unauthorized(res)
        if redir:
            return redir

        if res.status_code != 201:
            return f"Gagal simpan berita<br>{res.text}", 400

    res = requests.get(f"{_api_base()}/berita")
    news_list = res.json() if res.status_code == 200 else []

    return render_template('admin/news.html', news_list=news_list)


# ===============================
# UPDATE BERITA
# ===============================
@admin_web_bp.route('/admin/news/update/<int:id>', methods=['POST'])
def update_news(id):
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    files = {}
    if request.files.get('gambar') and request.files['gambar'].filename:
        files['gambar'] = request.files['gambar']

    data = {
        'judul': request.form.get('judul'),
        'isi': request.form.get('isi')
    }

    res = requests.put(
        f"{_api_base()}/berita/{id}",
        headers=_headers(token),
        data=data,
        files=files
    )

    redir = _redirect_login_if_unauthorized(res)
    if redir:
        return redir

    if res.status_code != 200:
        return f"Gagal update berita<br>{res.text}", 400

    return redirect(url_for('admin_web.news'))


# ===============================
# HAPUS BERITA
# ===============================
@admin_web_bp.route('/admin/news/delete/<int:id>', methods=['POST'])
def delete_news(id):
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    res = requests.delete(
        f"{_api_base()}/berita/{id}",
        headers=_headers(token)
    )

    redir = _redirect_login_if_unauthorized(res)
    if redir:
        return redir

    return redirect(url_for('admin_web.news'))


# ===============================
# LOGOUT
# ===============================
@admin_web_bp.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_web.admin_login'))


# ===============================
# ULASAN APLIKASI
# ===============================
@admin_web_bp.route('/admin/reviews')
def reviews():
    token = _require_token()
    if not token:
        return redirect(url_for('admin_web.admin_login'))

    res = requests.get(f"{_api_base()}/ulasan", headers=_headers(token))
    redir = _redirect_login_if_unauthorized(res)
    if redir:
        return redir
    if res.status_code != 200:
        return f"Gagal ambil data ulasan<br>{res.text}", 500

    reviews = res.json() or []
    total = len(reviews)

    # Summary sederhana
    avg_rating = 0
    if total:
        try:
            avg_rating = round(sum(int(r.get('rating') or 0) for r in reviews) / total, 2)
        except Exception:
            avg_rating = 0

    sentiment_count = {'positif': 0, 'netral': 0, 'negatif': 0}
    star_count = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        s = (r.get('sentiment') or '').strip().lower()
        if s in sentiment_count:
            sentiment_count[s] += 1

        try:
            star = int(r.get('rating') or 0)
            if star in star_count:
                star_count[star] += 1
        except Exception:
            pass

    return render_template(
        'admin/reviews.html',
        reviews=reviews,
        total=total,
        avg_rating=avg_rating,
        sentiment_count=sentiment_count,
        star_count=star_count
    )
