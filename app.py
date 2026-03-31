import os
import uuid
import sqlite3
from datetime import datetime

from flask import Flask, request, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from dotenv import load_dotenv

from line_sender import send_message

load_dotenv()

app = Flask(__name__)

DB_PATH = "scheduled_messages.db"
TIMEZONE = os.environ.get("TIMEZONE", "Asia/Taipei")

# APScheduler with SQLite job store (survives restarts)
scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{DB_PATH}")},
    executors={"default": ThreadPoolExecutor(5)},
    timezone=TIMEZONE,
)


# ---------- Job function ----------

def _run_send(job_id: str, target_name: str, message: str):
    try:
        send_message(target_name, message, headless=True)
        _update_status(job_id, "sent")
    except Exception as e:
        _update_status(job_id, f"error: {e}")
        print(f"[ERROR] job {job_id}: {e}")


# ---------- DB helpers ----------

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          TEXT PRIMARY KEY,
                target_name TEXT NOT NULL,
                message     TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                created_at  TEXT NOT NULL
            )
        """)


def _update_status(job_id: str, status: str):
    with _get_db() as conn:
        conn.execute("UPDATE messages SET status=? WHERE id=?", (status, job_id))


# ---------- Routes ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/schedules", methods=["GET"])
def list_schedules():
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM messages ORDER BY scheduled_at DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/schedules", methods=["POST"])
def create_schedule():
    data = request.get_json(force=True)

    target_name  = (data.get("target_name")  or "").strip()
    message      = (data.get("message")      or "").strip()
    scheduled_at_str = (data.get("scheduled_at") or "").strip()

    if not target_name or not message or not scheduled_at_str:
        return jsonify({"error": "target_name, message, scheduled_at 為必填"}), 400

    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_str)
    except ValueError:
        return jsonify({"error": "scheduled_at 格式錯誤，請用 YYYY-MM-DDTHH:MM"}), 400

    if scheduled_at <= datetime.now():
        return jsonify({"error": "預約時間必須在未來"}), 400

    job_id = str(uuid.uuid4())

    with _get_db() as conn:
        conn.execute(
            "INSERT INTO messages VALUES (?,?,?,?,?,?)",
            (job_id, target_name, message, scheduled_at.isoformat(), "pending", datetime.now().isoformat()),
        )

    scheduler.add_job(
        _run_send,
        trigger="date",
        run_date=scheduled_at,
        args=[job_id, target_name, message],
        id=job_id,
        replace_existing=True,
    )

    return jsonify({"id": job_id, "scheduled_at": scheduled_at.isoformat()}), 201


@app.route("/api/schedules/<job_id>", methods=["DELETE"])
def cancel_schedule(job_id):
    with _get_db() as conn:
        row = conn.execute("SELECT status FROM messages WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return jsonify({"error": "找不到此排程"}), 404
        if row["status"] == "sent":
            return jsonify({"error": "訊息已發送，無法取消"}), 400

    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    with _get_db() as conn:
        conn.execute("UPDATE messages SET status='cancelled' WHERE id=?", (job_id,))

    return jsonify({"message": "已取消"})


# ---------- Main ----------

if __name__ == "__main__":
    _init_db()
    scheduler.start()
    print("LINE 預約發訊息機器人啟動中... http://localhost:5000")
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        scheduler.shutdown()
