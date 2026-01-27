from app import app
from ai.rag.rag_engine import answer_question

if __name__ == "__main__":
    with app.app_context():
        res = answer_question("Apa itu EcoSea?")
        print(res.reply)