# AI Travel Agency

![AI Travel Agency](assets/banner.png)

Небольшой сайт туристического агентства на Flask.

---

#  О проекте

**AI Travel Agency** — современная платформа туристического агентства, разработанная на Flask с использованием искусственного интеллекта.

Проект позволяет пользователям подбирать туры, получать рекомендации от AI-консультанта, просматривать каталог путешествий и оставлять заявки через удобный веб-интерфейс.

Для администратора реализована полноценная панель управления турами, клиентами и изображениями. Все данные хранятся в PostgreSQL, а приложение развернуто в облаке Railway.

---

#  Возможности

- 🤖 AI-консультант на базе OpenAI;
- 🌍 каталог туристических направлений;
- 🔍 подбор тура по запросу пользователя;
- 👤 регистрация и авторизация клиентов;
- 🗄 хранение данных в PostgreSQL;
- 🖼 загрузка изображений туров;
- ⚙ административная панель;
- 📱 адаптивный интерфейс;
- ☁ готовность к развертыванию на Railway.

 #  Структура проекта

```text
Trevel_pyteshestvie
│
├── assets/             # Баннер README
├── static/             # CSS, JavaScript, изображения
├── templates/          # HTML-шаблоны Flask
├── app.py              # Главный файл приложения
├── config.py           # Конфигурация проекта
├── forms.py            # Формы Flask
├── models.py           # SQLAlchemy модели
├── requirements.txt    # Python зависимости
├── Procfile            # Конфигурация Railway
├── runtime.txt         # Версия Python
└── README.md
```

---

 #  Используемые технологии

<p>

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white">
<img src="https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white">
<img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge">
<img src="https://img.shields.io/badge/OpenAI_API-412991?style=for-the-badge">
<img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white">
<img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white">
<img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black">
<img src="https://img.shields.io/badge/Bootstrap-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white">
<img src="https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge">
<img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white">
<img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white">

</p>

---

## Локальный запуск

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Сайт: http://127.0.0.1:5000  
Админ-панель: http://127.0.0.1:5000/admin/login

## Railway

1. Создайте проект из GitHub-репозитория.
2. Добавьте переменные из `.env.example`.
3. Start Command: `gunicorn app:app`
4. Добавьте Volume и установите Mount Path `/data`.
5. Создайте публичный домен Railway.
6. Для holy-cow.ru добавьте Custom Domain и внесите DNS-запись, которую покажет Railway.

Важно: без Railway Volume база SQLite, Excel и загруженные изображения могут пропасть после нового деплоя.

#  Автор

**Татьяна**

GitHub: **[q1271qaz-arch](https://github.com/q1271qaz-arch)**
