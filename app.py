import json
import mimetypes
import os
import re
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from time import time

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, session, send_file, flash
)
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
from openpyxl import Workbook
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Совместимость со строками Railway вида postgres://...
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )
else:
    # Локально сайт продолжит работать с SQLite
    database_url = f"sqlite:///{DATA_DIR / 'travel.db'}"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

db = SQLAlchemy(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), default="")
    phone = db.Column(db.String(50), default="")
    email = db.Column(db.String(120), default="")
    wishes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Tour(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, default="")
    image = db.Column(db.String(255), default="")


def export_clients_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Клиенты"
    ws.append(["ID", "Имя", "Телефон", "Email", "Пожелания", "Дата"])
    for item in Client.query.order_by(Client.id.asc()).all():
        ws.append([
            item.id, item.name, item.phone, item.email,
            item.wishes, item.created_at.strftime("%d.%m.%Y %H:%M")
        ])
    path = DATA_DIR / "clients.xlsx"
    wb.save(path)
    return path


PARSER_INSTRUCTIONS = """
Ты CRM-парсер туристического агентства.
Извлеки данные клиента из сообщения и верни ТОЛЬКО JSON, без пояснений.

Строго в таком формате:
{
  "name": "",
  "phone": "",
  "email": "",
  "city_from": "",
  "country": "",
  "resort": "",
  "people_count": "",
  "budget": "",
  "travel_dates": "",
  "wishes": ""
}

Правила:
- country — страна назначения: Турция, Египет, ОАЭ, Таиланд, Мальдивы, Греция и т.д.
- people_count — только количество туристов. «Мы с мужем», «вдвоём», «нас двое» → "2".
- travel_dates — только даты поездки, например «15–25 сентября» или «в августе».
- budget — только бюджет, например «300000 рублей».
- city_from — город вылета, например «Калининград».
- wishes — пожелания к отелю, питанию, детям, пляжу.
- Если данных нет — оставь пустую строку. Не помещай всё сообщение в travel_dates.
"""

# Как называть поля в сводке для менеджера
DETAIL_TITLES = {
    "city_from": "вылет из",
    "country": "страна",
    "resort": "курорт",
    "people_count": "человек",
    "budget": "бюджет",
    "travel_dates": "даты",
}


def extract_client_data_with_ai(text):
    """Разбирает сообщение моделью. При любой осечке возвращает пустой словарь."""
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=PARSER_INSTRUCTIONS,
            input=text
        )
        raw = response.output_text.strip()

        # модель нередко оборачивает ответ в ```json ... ```
        raw = re.sub(r"^```(?:json)?", "", raw)
        raw = re.sub(r"```$", "", raw).strip()

        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception as error:
        app.logger.warning("Парсер клиента не сработал: %s", error)
        return {}


def extract_client_data_regex(text):
    """Запасной разбор без модели: только имя, телефон и почта."""
    result = {}

    name_match = re.search(
        r"(?:меня зовут|мо[её] имя)\s+([А-ЯЁA-Z][а-яёa-z-]{1,30})",
        text, re.IGNORECASE
    )
    phone_match = re.search(r"(?:\+?\d[\d\s()-]{8,}\d)", text)
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Zа-яА-Я]{2,}", text)

    if name_match:
        result["name"] = name_match.group(1).title()
    if phone_match:
        result["phone"] = phone_match.group(0).strip()
    if email_match:
        result["email"] = email_match.group(0).lower()

    return result


def extract_client_data(item, text):
    # Модель понимает «мы с мужем» и «в конце августа», регулярки — нет.
    # Но если запрос к модели не прошёл, старый разбор всё равно отработает.
    data = extract_client_data_with_ai(text) or extract_client_data_regex(text)

    for field in ("name", "phone", "email"):
        value = str(data.get(field) or "").strip()
        if value:
            setattr(item, field, value)

    details = [
        f"{title}: {str(data.get(key)).strip()}"
        for key, title in DETAIL_TITLES.items()
        if str(data.get(key) or "").strip()
    ]

    addition = text
    if details:
        addition += "\n[разобрано] " + "; ".join(details)
    if str(data.get("wishes") or "").strip():
        addition += "\n[пожелания] " + str(data["wishes"]).strip()

    item.wishes = (item.wishes + "\n" + addition).strip()[-5000:]


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    tours = Tour.query.order_by(Tour.id.desc()).all()
    return render_template("index.html", tours=tours)


PLACEHOLDER_IMAGE = "/static/images/tour-placeholder.jpg"


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    # Было <path:filename> — конвертер пропускает слеши, и через ../
    # по этому адресу можно было скачать любой файл на сервере.
    safe_name = secure_filename(filename)
    path = UPLOAD_DIR / safe_name

    if not path.is_file():
        # Файла нет — показываем заглушку: дырка на странице выглядит
        # хуже серого кадра, а ошибка 500 хуже всего.
        return redirect(PLACEHOLDER_IMAGE)

    # У старых файлов расширения нет, тип по имени не угадывается,
    # и send_file без явного mimetype падает.
    mimetype = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return send_file(path, mimetype=mimetype)


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    user_text = str(data.get("message", "")).strip()
    if not user_text:
        return jsonify({"error": "Введите сообщение"}), 400

    session_id = session.get("client_session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        session["client_session_id"] = session_id

    visitor = Client.query.filter_by(session_id=session_id).first()
    if not visitor:
        visitor = Client(session_id=session_id)
        db.session.add(visitor)
        db.session.flush()

    extract_client_data(visitor, user_text)
    db.session.add(ChatMessage(client_id=visitor.id, role="user", text=user_text))

    history = ChatMessage.query.filter_by(client_id=visitor.id)\
        .order_by(ChatMessage.id.desc()).limit(12).all()
    history = list(reversed(history))

    conversation = "\n".join(
        f"{'Клиент' if m.role == 'user' else 'Менеджер'}: {m.text}"
        for m in history
    )

    instructions = """
Ты опытный менеджер туристического агентства «Holy Cow Travel».
Общайся по-русски, дружелюбно и профессионально.
Твоя задача — выяснить имя, телефон или email, направление, даты,
количество туристов, бюджет, тип питания и пожелания.
Задавай за один раз не больше двух вопросов.
Не обещай наличие тура и точную цену без проверки менеджером.
Когда данных достаточно, кратко подведи итог и предложи передать заявку человеку.
"""

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=instructions,
            input=conversation + f"\nКлиент: {user_text}\nМенеджер:"
        )
        answer = response.output_text.strip()
    except Exception:
        answer = (
            "Спасибо! Я записал ваши пожелания. Уточните, пожалуйста, "
            "направление, даты поездки, количество туристов и примерный бюджет."
        )

    db.session.add(ChatMessage(client_id=visitor.id, role="assistant", text=answer))
    db.session.commit()
    export_clients_excel()
    return jsonify({"answer": answer})


MAX_LOGIN_ATTEMPTS = 5
LOGIN_BLOCK_SECONDS = 300
login_attempts = {}  # ip -> (сколько неудач, когда началась серия)


def client_ip():
    # Railway отдаёт приложение через прокси: настоящий адрес приходит
    # в заголовке, а не в remote_addr
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() or request.remote_addr or "unknown"


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    ip = client_ip()
    attempts, started_at = login_attempts.get(ip, (0, 0))

    # серия неудач протухла — забываем её
    if started_at and time() - started_at > LOGIN_BLOCK_SECONDS:
        attempts, started_at = 0, 0
        login_attempts.pop(ip, None)

    if attempts >= MAX_LOGIN_ATTEMPTS:
        wait = int(LOGIN_BLOCK_SECONDS - (time() - started_at))
        flash(f"Слишком много попыток. Попробуйте через {max(wait, 1) // 60 + 1} мин.")
        return render_template("login.html")

    if request.method == "POST":
        login = request.form.get("login", "")
        password = request.form.get("password", "")
        expected_login = os.getenv("ADMIN_LOGIN", "admin")
        stored_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
        plain_password = os.getenv("ADMIN_PASSWORD", "admin123")

        valid_password = (
            check_password_hash(stored_hash, password)
            if stored_hash else password == plain_password
        )
        if login == expected_login and valid_password:
            login_attempts.pop(ip, None)
            session["admin"] = True
            return redirect(url_for("admin"))

        login_attempts[ip] = (attempts + 1, started_at or time())
        flash("Неверный логин или пароль")
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin():
    return render_template(
        "admin.html",
        tours=Tour.query.order_by(Tour.id.desc()).all(),
        clients=Client.query.order_by(Client.id.desc()).all()
    )


@app.post("/admin/tours/add")
@admin_required
def add_tour():
    image_path = ""
    image = request.files.get("image")
    if image and image.filename:
        # secure_filename выбрасывает кириллицу целиком: "фото.jpg" даёт "jpg",
        # то есть файл сохранялся вообще без расширения. Берём расширение
        # отдельно и не полагаемся на исходное имя.
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        image.save(UPLOAD_DIR / filename)
        image_path = f"/uploads/{filename}"

    tour = Tour(
        title=request.form.get("title", "").strip(),
        country=request.form.get("country", "").strip(),
        price=request.form.get("price", "").strip(),
        description=request.form.get("description", "").strip(),
        image=image_path
    )
    db.session.add(tour)
    db.session.commit()
    return redirect(url_for("admin"))


@app.post("/admin/tours/<int:tour_id>/delete")
@admin_required
def delete_tour(tour_id):
    tour = db.session.get(Tour, tour_id)
    if tour:
        db.session.delete(tour)
        db.session.commit()
    return redirect(url_for("admin"))


@app.get("/admin/export")
@admin_required
def download_excel():
    return send_file(
        export_clients_excel(),
        as_attachment=True,
        download_name="clients.xlsx"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


with app.app_context():
    db.create_all()
    if not Tour.query.first():
        db.session.add_all([
            Tour(
                title="Турция — всё включено",
                country="Турция",
                price="от 145 000 ₽",
                description="7 ночей, отель 5★, перелёт и трансфер.",
                image="https://images.unsplash.com/photo-1524231757912-21f4fe3a7200"
            ),
            Tour(
                title="Мальдивы для двоих",
                country="Мальдивы",
                price="от 290 000 ₽",
                description="Романтический отдых на берегу океана.",
                image="https://images.unsplash.com/photo-1514282401047-d79a71a590e8"
            ),
        ])
        db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
