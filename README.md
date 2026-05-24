git clone ...
cd bi-bi-backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # вставить строку подключения к БД
uvicorn app.main:app --reload