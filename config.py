import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASS')}@"
        f"{os.getenv('DB_HOST')}/"
        f"{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "laporan")
    PROFILE_UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "profile")

    RAG_KB_PATH = os.getenv("RAG_KB_PATH", os.path.join(BASE_DIR, "ai-chat", "chatbot.txt"))

    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))

    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "650"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))