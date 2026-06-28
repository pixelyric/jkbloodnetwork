# J&K Blood Network

Blood donor finder and registration system for Jammu & Kashmir.

## Local development

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

Local development uses SQLite (`donors.db`) in the project folder. Donor data is mirrored to `donors.csv`.

## Production (Render)

1. Create a new **Web Service** from this repository or upload the project.
2. Add a **PostgreSQL** database in Render and attach it to the web service.
3. Render sets `DATABASE_URL` automatically. The app uses PostgreSQL when that variable exists.
4. Set `SECRET_KEY` (Render can generate one via `render.yaml`).
5. Deploy. Tables are created automatically on startup.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Production | Flask session signing key |
| `DATABASE_URL` | Render | PostgreSQL connection string (auto-set on Render) |
| `PORT` | Render | HTTP port (auto-set on Render) |
| `FLASK_ENV` | Optional | Set to `production` on Render |

## Routes

- `/` — Home
- `/signup` — Create account
- `/login` / `/logout` — Session auth
- `/register` — Register a donor (login required)
- `/search` — Search donors by blood group and district
- `/donors` — Paginated donor listing
- `/success` — Registration confirmation

## Notes

- Only `donors.db` is used locally.
- `donors.csv` is synchronized with the database whenever a donor is registered.
