# Holy Cow Travel

Небольшой сайт туристического агентства на Flask.

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
