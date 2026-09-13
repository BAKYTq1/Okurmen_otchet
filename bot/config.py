import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

# Список менторов — добавляйте/убирайте по необходимости
MENTORS: list[str] = [
    "Иванов Иван Иванович",
    "Петрова Мария Сергеевна",
    "Сидоров Алексей Николаевич",
    "Козлова Елена Дмитриевна",
    "Смирнов Дмитрий Павлович",
]

REVIEWS_FILE = "reviews.json"
