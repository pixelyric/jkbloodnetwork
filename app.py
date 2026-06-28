import csv
import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "donors.db")
CSV_FILE = os.path.join(BASE_DIR, "donors.csv")
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    IntegrityError = psycopg2.IntegrityError
else:
    import sqlite3

    IntegrityError = sqlite3.IntegrityError

CSV_HEADERS = [
    "Name",
    "Gender",
    "Age",
    "Email",
    "Phone",
    "District",
    "City",
    "Blood_group",
    "Months_since_last_donation",
]

DONOR_COLUMNS = (
    '"Name", "Gender", "Age", "Email", "Phone", '
    '"District", "City", "Blood_group", "Months_since_last_donation"'
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-in-production")

if os.environ.get("FLASK_ENV") == "production" or os.environ.get("RENDER"):
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def execute(conn, sql, params=()):
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def scalar(cur):
    row = cur.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0]


def row_value(row, key, index=0):
    if isinstance(row, dict):
        return row.get(key) or row.get(key.lower()) or list(row.values())[index]
    return row[index]


def create_database():
    conn = get_db()
    if USE_POSTGRES:
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS donors (
                id SERIAL PRIMARY KEY,
                "Name" TEXT NOT NULL,
                "Gender" TEXT,
                "Age" INTEGER,
                "Email" TEXT,
                "Phone" TEXT,
                "District" TEXT,
                "City" TEXT,
                "Blood_group" TEXT,
                "Months_since_last_donation" INTEGER
            )
            """,
        )
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """,
        )
    else:
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS donors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT NOT NULL,
                Gender TEXT,
                Age INTEGER,
                Email TEXT,
                Phone TEXT,
                District TEXT,
                City TEXT,
                Blood_group TEXT,
                Months_since_last_donation INTEGER
            )
            """,
        )
        execute(
            conn,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """,
        )
    conn.commit()
    conn.close()


def sync_csv_from_db():
    conn = get_db()
    cur = execute(
        conn,
        f"""
        SELECT {DONOR_COLUMNS}
        FROM donors
        ORDER BY id
        """,
    )
    rows = cur.fetchall()
    conn.close()

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CSV_HEADERS)
        for row in rows:
            writer.writerow(
                [
                    row_value(row, header, index) or ""
                    for index, header in enumerate(CSV_HEADERS)
                ]
            )


create_database()
sync_csv_from_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = generate_password_hash(request.form["password"])
        conn = get_db()
        try:
            execute(
                conn,
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password),
            )
            conn.commit()
            session["username"] = username
            flash("Account created. Welcome.", "success")
            return redirect(url_for("register"))
        except IntegrityError:
            flash("Username or email already exists.", "error")
        finally:
            conn.close()
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        user = execute(
            conn,
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()
        if user and check_password_hash(row_value(user, "password", 3), password):
            session["username"] = username
            flash(f"Welcome back, {username}.", "success")
            return redirect(url_for("home"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" not in session:
        flash("Please log in to register a donor.", "info")
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form["name"].strip()
        blood = request.form["blood_group"]
        if not name or not blood:
            flash("Name and Blood Group are required.", "error")
            return redirect(url_for("register"))

        age = request.form.get("age") or None
        months = request.form.get("months") or None
        if age is not None:
            age = int(age)
        if months is not None:
            months = int(months)

        conn = get_db()
        execute(
            conn,
            f"""
            INSERT INTO donors ({DONOR_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                request.form.get("gender", ""),
                age,
                request.form.get("email", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("district", ""),
                request.form.get("city", "").strip(),
                blood,
                months,
            ),
        )
        conn.commit()
        conn.close()
        sync_csv_from_db()
        return redirect(url_for("success"))
    return render_template("register.html")


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    donors = []
    searched = False
    query_bg = ""
    query_dist = ""
    if request.method == "POST":
        query_bg = request.form.get("blood_group", "").strip()
        query_dist = request.form.get("district", "").strip()
        searched = True
        conn = get_db()
        if query_dist:
            donors = execute(
                conn,
                """
                SELECT * FROM donors
                WHERE "Blood_group" = ? AND "District" = ?
                ORDER BY "Months_since_last_donation" ASC
                """,
                (query_bg, query_dist),
            ).fetchall()
        else:
            donors = execute(
                conn,
                """
                SELECT * FROM donors
                WHERE "Blood_group" = ?
                ORDER BY "Months_since_last_donation" ASC
                """,
                (query_bg,),
            ).fetchall()
        conn.close()

    conn = get_db()
    districts = [
        row_value(row, "District", 0)
        for row in execute(
            conn,
            'SELECT DISTINCT "District" FROM donors WHERE "District" IS NOT NULL AND "District" != \'\' ORDER BY "District"',
        ).fetchall()
    ]
    conn.close()
    return render_template(
        "search.html",
        donors=donors,
        searched=searched,
        query_bg=query_bg,
        query_dist=query_dist,
        districts=districts,
    )


@app.route("/donors")
def all_donors():
    page = max(1, int(request.args.get("page", 1)))
    per_page = 20
    offset = (page - 1) * per_page
    conn = get_db()
    total = scalar(execute(conn, "SELECT COUNT(*) FROM donors"))
    rows = execute(
        conn,
        "SELECT * FROM donors ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()
    conn.close()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "donors.html",
        donors=rows,
        page=page,
        total_pages=total_pages,
        total=total,
    )


if __name__ == "__main__":
    create_database()
    sync_csv_from_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
