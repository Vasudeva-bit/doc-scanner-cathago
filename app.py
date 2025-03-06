import hashlib
import os
import sqlite3
from datetime import datetime, timedelta

import google.generativeai as genai
import requests
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def init_db():
    DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        credits INTEGER DEFAULT 20,
        last_reset TEXT
    )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT,
        content TEXT,
        upload_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS credit_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        requested_credits INTEGER,
        status TEXT DEFAULT 'pending',
        request_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )"""
    )

    # insertinng default admin by my name vasudeva
    admin_username = "vasudeva"
    admin_password = hashlib.sha256("vasudeva".encode()).hexdigest()
    c.execute("SELECT COUNT(*) FROM users WHERE username = ?", (admin_username,))
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (username, password, role, last_reset) VALUES (?, ?, ?, ?)",
            (admin_username, admin_password, "admin", datetime.now().isoformat()),
        )

    conn.commit()
    conn.close()


def log_action(user_id, action, details):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, action, details, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        role = "user"
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password, role, last_reset) VALUES (?, ?, ?, ?)",
                (username, password, role, datetime.now().isoformat()),
            )
            conn.commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
        conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute(
            "SELECT id, role FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        user = c.fetchone()
        conn.close()
        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]
            return redirect(url_for("index"))
        flash("Invalid credentials.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("role", None)
    return redirect(url_for("login"))


def reset_credits():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "UPDATE users SET credits = 20, last_reset = ? WHERE last_reset < ?",
        (datetime.now().isoformat(), (datetime.now() - timedelta(days=1)).isoformat()),
    )
    conn.commit()
    conn.close()


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    reset_credits()
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT username, credits FROM users WHERE id = ?", (session["user_id"],))
    user = c.fetchone()
    c.execute(
        "SELECT filename, upload_date FROM documents WHERE user_id = ?",
        (session["user_id"],),
    )
    scans = c.fetchall()
    c.execute(
        "SELECT SUM(requested_credits) FROM credit_requests WHERE user_id = ?",
        (session["user_id"],),
    )
    total_requested_credits = c.fetchone()[0] or 0
    conn.close()
    return render_template(
        "profile.html",
        user=user,
        scans=scans,
        credits=user[1],
        total_requested_credits=total_requested_credits,
    )


@app.route("/download_scans")
def download_scans():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "SELECT filename, upload_date FROM documents WHERE user_id = ?",
        (session["user_id"],),
    )
    scans = c.fetchall()
    conn.close()

    # generate text file content
    content = "Past Scans:\n"
    for scan in scans:
        content += f"Filename: {scan[0]}, Uploaded: {scan[1]}\n"

    # servs as downloadable file
    from io import BytesIO

    buffer = BytesIO(content.encode("utf-8"))
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="past_scans.txt",
        mimetype="text/plain",
    )


@app.route("/credits/request", methods=["POST"])
def request_credits():
    if "user_id" not in session:
        return redirect(url_for("login"))
    requested_credits = int(request.form["credits"])
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO credit_requests (user_id, requested_credits, request_date) VALUES (?, ?, ?)",
        (session["user_id"], requested_credits, datetime.now().isoformat()),
    )
    conn.commit()
    log_action(
        session["user_id"], "credit_request", f"Requested {requested_credits} credits"
    )
    conn.close()
    flash("Credit request submitted.")
    return redirect(url_for("profile"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("index"))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        request_id = request.form["request_id"]
        action = request.form["action"]
        if action == "approve":
            c.execute(
                "UPDATE users SET credits = credits + (SELECT requested_credits FROM credit_requests WHERE id = ?) WHERE id = (SELECT user_id FROM credit_requests WHERE id = ?)",
                (request_id, request_id),
            )
            c.execute(
                "UPDATE credit_requests SET status = 'approved' WHERE id = ?",
                (request_id,),
            )
            user_id = c.execute(
                "SELECT user_id FROM credit_requests WHERE id = ?", (request_id,)
            ).fetchone()[0]
            requested_credits = c.execute(
                "SELECT requested_credits FROM credit_requests WHERE id = ?",
                (request_id,),
            ).fetchone()[0]
            log_action(
                user_id, "credit_approved", f"Approved {requested_credits} credits"
            )
        else:
            c.execute(
                "UPDATE credit_requests SET status = 'denied' WHERE id = ?",
                (request_id,),
            )
            user_id = c.execute(
                "SELECT user_id FROM credit_requests WHERE id = ?", (request_id,)
            ).fetchone()[0]
            log_action(user_id, "credit_denied", "Request denied")
        conn.commit()

    # fethcing pending requests with total requested credits per user
    c.execute(
        """
        SELECT cr.id, u.username, cr.requested_credits, cr.status, cr.request_date, 
               (SELECT SUM(cr2.requested_credits) FROM credit_requests cr2 WHERE cr2.user_id = u.id) as total_requested
        FROM credit_requests cr 
        JOIN users u ON cr.user_id = u.id 
        WHERE cr.status = 'pending'
    """
    )
    reqts = c.fetchall()

    c.execute(
        "SELECT u.username, l.action, l.details, l.timestamp FROM logs l JOIN users u ON l.user_id = u.id ORDER BY l.timestamp DESC LIMIT 50"
    )
    logs = c.fetchall()
    conn.close()

    return render_template("admin.html", requests=reqts, logs=logs)


def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return 1
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return (previous_row[-1] * 1.0) / len(s1)


def get_dissimilarity_score(s1, s2):
    prompt = f"""Given two texts, return a dissimilarity score between 0 and 1,
        where 0 means identical and 1 means completely different.  
        Text 1: {s1}
        Text 2: {s2}
        Respond with only a single floating-point number in the range [0, 1]."""

    genai.configure(api_key="AIzaSyC9j6aM6MIuo_strmUkbsXuJWAd3UXn0qk")
    model = genai.GenerativeModel("gemini-2.0-flash")

    try:
        response = model.generate_content(prompt)
        score = response.text.strip()
        return float(score)
    except Exception as e:
        print(e)
        return levenshtein_distance(s1, s2)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    reset_credits()
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE id = ?", (session["user_id"],))
    credits = c.fetchone()[0]
    doc_id = None
    if request.method == "POST" and credits > 0:
        file = request.files["file"]
        if file and file.filename.endswith(".txt"):
            filename = file.filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            with open(filepath, "r") as f:
                content = f.read()
            c.execute(
                "INSERT INTO documents (user_id, filename, content, upload_date) VALUES (?, ?, ?, ?)",
                (session["user_id"], filename, content, datetime.now().isoformat()),
            )
            c.execute(
                "UPDATE users SET credits = credits - 1 WHERE id = ?",
                (session["user_id"],),
            )
            conn.commit()
            doc_id = c.lastrowid
            log_action(session["user_id"], "scan", f"Uploaded {filename}")
            flash("Document uploaded successfully.")
        else:
            flash("Please upload a .txt file.")
    conn.close()
    return render_template("upload.html", credits=credits, doc_id=doc_id)


@app.route("/match/<int:doc_id>", methods=["GET"])
def matchs(doc_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE id = ?", (session["user_id"],))
    credits = c.fetchone()[0]
    c.execute("SELECT content FROM documents WHERE id = ?", (doc_id,))
    target_doc = c.fetchone()
    if not target_doc:
        flash("Document not found.")
        return redirect(url_for("upload"))
    target_content = target_doc[0]

    # matchs
    c.execute("SELECT id, filename, content FROM documents WHERE id != ?", (doc_id,))
    all_docs = c.fetchall()
    matches = []
    for doc in all_docs:
        distance = get_dissimilarity_score(target_content, doc[2])
        if distance < 0.3:  # less than 30% dis-similarity threshold
            matches.append((doc[0], doc[1], distance))
    matches = sorted(matches, key=lambda x: x[2])[
        :5
    ]  # sorting based on hte distance, limit 5
    conn.close()
    return render_template("matchs.html", matches=matches, credits=credits)


@app.route("/download/<filename>")
def download_file(filename):
    if "user_id" not in session:
        return redirect(url_for("login"))
    return send_from_directory(
        app.config["UPLOAD_FOLDER"], filename, as_attachment=True
    )


@app.route("/admin/analytics")
def analytics():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("index"))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        "SELECT u.username, COUNT(d.id) FROM users u LEFT JOIN documents d ON u.id = d.user_id GROUP BY u.id, u.username ORDER BY COUNT(d.id) DESC LIMIT 5"
    )
    top_users = c.fetchall()
    c.execute(
        "SELECT COUNT(*) FROM documents WHERE upload_date > ?",
        ((datetime.now() - timedelta(days=1)).isoformat(),),
    )
    daily_scans = c.fetchone()[0]
    c.execute("SELECT AVG(credits) FROM users")
    avg_credits = c.fetchone()[0]
    conn.close()
    return render_template(
        "analytics.html",
        top_users=top_users,
        daily_scans=daily_scans,
        avg_credits=avg_credits,
    )


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
