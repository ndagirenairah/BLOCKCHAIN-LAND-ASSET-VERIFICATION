import hashlib
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    make_response,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parent
DATABASE = os.environ.get("DATABASE", str(BASE_DIR / "land_records.sqlite3"))
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(BASE_DIR / "private_uploads"))
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_ATTEMPTS = 5
MIN_PASSWORD_LENGTH = 14
login_attempts = {}

app = Flask(__name__)
configured_secret = os.environ.get("SECRET_KEY")
if not configured_secret and os.environ.get("APP_ENV") == "production":
    raise RuntimeError("SECRET_KEY must be configured in production.")
if os.environ.get("APP_ENV") == "production" and configured_secret and len(configured_secret) < 32:
    raise RuntimeError("SECRET_KEY must contain at least 32 characters in production.")
app.config.update(
    SECRET_KEY=configured_secret or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
    DATABASE=DATABASE,
    UPLOAD_DIR=UPLOAD_DIR,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("APP_ENV") == "production",
    PERMANENT_SESSION_LIFETIME=1800,
    AUTO_APPROVE_RECORDS=os.environ.get("AUTO_APPROVE_RECORDS", "true").lower() == "true",
)
USING_POSTGRES = DATABASE.startswith(("postgresql://", "postgres://"))
if USING_POSTGRES and psycopg is None:
    raise RuntimeError("psycopg is required when DATABASE is a PostgreSQL URL.")
DB_ERRORS = (sqlite3.Error,) if psycopg is None else (sqlite3.Error, psycopg.Error)
DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,) if psycopg is None else (
    sqlite3.IntegrityError,
    psycopg.errors.UniqueViolation,
)


class PostgresDatabase:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        return self.connection.execute(query.replace("?", "%s"), parameters)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        if USING_POSTGRES:
            g.db = PostgresDatabase(psycopg.connect(app.config["DATABASE"], row_factory=dict_row))
        else:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    db = get_db()
    if USING_POSTGRES:
        db.execute("SELECT pg_advisory_lock(824617203)")
    schema = """
        CREATE TABLE IF NOT EXISTS users (
            id {serial} PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('submitter', 'verifier', 'reviewer', 'administrator')),
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS records (
            id {serial} PRIMARY KEY,
            public_reference TEXT UNIQUE NOT NULL,
            asset_type TEXT NOT NULL,
            area_label TEXT NOT NULL,
            submitter_id INTEGER NOT NULL REFERENCES users(id),
            file_storage_key TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
            review_reason TEXT,
            district TEXT,
            county TEXT,
            block TEXT,
            plot TEXT,
            tenure TEXT,
            title_volume TEXT,
            title_folio TEXT,
            registration_number TEXT,
            chassis_number TEXT,
            engine_number TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS record_events (
            id {serial} PRIMARY KEY,
            record_id INTEGER NOT NULL REFERENCES records(id),
            event_type TEXT NOT NULL,
            actor_id INTEGER REFERENCES users(id),
            event_time TEXT NOT NULL,
            reason TEXT,
            tx_hash TEXT,
            event_status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS verification_checks (
            id {serial} PRIMARY KEY,
            record_id INTEGER REFERENCES records(id),
            submitted_hash TEXT NOT NULL,
            result TEXT NOT NULL,
            checked_by INTEGER REFERENCES users(id),
            checked_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS land_searches (
            id {serial} PRIMARY KEY,
            search_reference TEXT UNIQUE NOT NULL,
            search_type TEXT NOT NULL CHECK (search_type IN ('TITLE', 'PARCEL')),
            volume TEXT,
            folio TEXT,
            county TEXT,
            block TEXT,
            plot TEXT,
            created_by INTEGER REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'READY_FOR_OFFICIAL_CHECK',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id {serial} PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            plan_code TEXT NOT NULL CHECK (plan_code IN ('FREE', 'INDIVIDUAL', 'PROFESSIONAL', 'ORGANIZATION')),
            status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'PAYMENT_REQUIRED', 'CANCELLED')),
            provider TEXT,
            provider_reference TEXT,
            started_at TEXT NOT NULL,
            renewed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id, id);
        CREATE TABLE IF NOT EXISTS security_audit_logs (
            id {serial} PRIMARY KEY,
            actor_id INTEGER REFERENCES users(id),
            action TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT,
            timestamp TEXT NOT NULL,
            outcome TEXT NOT NULL,
            previous_hash TEXT,
            entry_hash TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_records_reference ON records(public_reference);
        CREATE INDEX IF NOT EXISTS idx_records_hash ON records(file_hash);
        """.format(serial="BIGSERIAL" if USING_POSTGRES else "INTEGER")
    if USING_POSTGRES:
        for statement in schema.split(";"):
            if statement.strip():
                db.execute(statement)
    else:
        db.executescript(schema)
    if USING_POSTGRES:
        columns = {
            row["column_name"]
            for row in db.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'security_audit_logs'"
            ).fetchall()
        }
    else:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(security_audit_logs)")}
    if "previous_hash" not in columns:
        db.execute("ALTER TABLE security_audit_logs ADD COLUMN previous_hash TEXT")
    if "entry_hash" not in columns:
        db.execute("ALTER TABLE security_audit_logs ADD COLUMN entry_hash TEXT")
    if USING_POSTGRES:
        record_columns = {
            row["column_name"]
            for row in db.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'records'"
            ).fetchall()
        }
    else:
        record_columns = {row["name"] for row in db.execute("PRAGMA table_info(records)")}
    for column in (
        "district", "county", "block", "plot", "tenure", "title_volume",
        "title_folio", "registration_number", "chassis_number", "engine_number",
    ):
        if column not in record_columns:
            db.execute(f"ALTER TABLE records ADD COLUMN {column} TEXT")
    db.commit()
    if USING_POSTGRES:
        db.execute("SELECT pg_advisory_unlock(824617203)")
        db.commit()


def audit(action, object_type, object_id, outcome="success"):
    db = get_db()
    timestamp = utc_now()
    actor_id = g.user["id"] if g.user else None
    previous = db.execute(
        "SELECT entry_hash FROM security_audit_logs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    previous_hash = previous["entry_hash"] if previous and previous["entry_hash"] else ""
    canonical = "|".join(
        [previous_hash, str(actor_id or ""), action, object_type, str(object_id or ""), timestamp, outcome]
    )
    entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    db.execute(
        """
        INSERT INTO security_audit_logs
            (actor_id, action, object_type, object_id, timestamp, outcome, previous_hash, entry_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (actor_id, action, object_type, str(object_id) if object_id else None, timestamp, outcome, previous_hash, entry_hash),
    )
    db.commit()


def verify_audit_chain():
    previous_hash = ""
    rows = get_db().execute(
        """
        SELECT actor_id, action, object_type, object_id, timestamp, outcome, previous_hash, entry_hash
        FROM security_audit_logs ORDER BY id
        """
    ).fetchall()
    for row in rows:
        canonical = "|".join(
            [
                previous_hash,
                str(row["actor_id"] or ""),
                row["action"],
                row["object_type"],
                str(row["object_id"] or ""),
                row["timestamp"],
                row["outcome"],
            ]
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if row["previous_hash"] != previous_hash or row["entry_hash"] != expected:
            return False
        previous_hash = row["entry_hash"]
    return True


def ledger_record(record_id, file_hash, event_type):
    """A deterministic local ledger adapter; no personal data is written."""
    digest = hashlib.sha256(f"{record_id}:{file_hash}:{event_type}".encode()).hexdigest()
    return f"demo-ledger-{digest[:32]}"


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user["role"] not in roles:
                audit("unauthorized_access", "route", request.path, "denied")
                flash("You do not have permission for that action.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


@app.before_request
def load_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if g.user is None or g.user["status"] != "active":
            session.clear()
            g.user = None


@app.context_processor
def inject_user():
    return {"current_user": g.user, "csrf_token": csrf_token}


def csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.before_request
def enforce_csrf():
    if request.method == "POST" and not app.config.get("TESTING"):
        expected = session.get("_csrf_token")
        supplied = request.form.get("_csrf_token")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            flash("Please refresh this page, choose your document again, and click Check document.", "warning")
            return redirect(request.path)


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self'; form-action 'self'; frame-ancestors 'none'",
    )
    if app.config.get("SESSION_COOKIE_SECURE"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.errorhandler(413)
def request_entity_too_large(_error):
    return "Uploaded file exceeds the 10 MB limit.", 413


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def valid_upload(file_storage):
    if not file_storage.filename or not allowed_file(file_storage.filename):
        return False
    extension = file_storage.filename.rsplit(".", 1)[1].lower()
    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    signatures = {
        "pdf": header.startswith(b"%PDF-"),
        "png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "jpg": header.startswith(b"\xff\xd8\xff"),
        "jpeg": header.startswith(b"\xff\xd8\xff"),
        "txt": True,
    }
    return signatures[extension]


def file_hash(file_storage):
    digest = hashlib.sha256()
    while chunk := file_storage.stream.read(1024 * 1024):
        digest.update(chunk)
    file_storage.stream.seek(0)
    return digest.hexdigest()


def record_details(record_id):
    db = get_db()
    record = db.execute(
        """
        SELECT records.*, users.username AS submitter
        FROM records JOIN users ON users.id = records.submitter_id
        WHERE records.id = ?
        """,
        (record_id,),
    ).fetchone()
    events = db.execute(
        """
        SELECT record_events.*, users.username AS actor, users.role AS actor_role
        FROM record_events LEFT JOIN users ON users.id = record_events.actor_id
        WHERE record_id = ? ORDER BY event_time DESC
        """,
        (record_id,),
    ).fetchall()
    return record, events


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


SUBSCRIPTION_PLANS = (
    {"code": "FREE", "name": "Basic", "price": "Free", "description": "Check saved documents at no cost."},
    {"code": "INDIVIDUAL", "name": "Individual", "price": "UGX 25,000 / month", "description": "More saved records and downloadable verification reports."},
    {"code": "PROFESSIONAL", "name": "Professional", "price": "UGX 100,000 / month", "description": "For land agents, surveyors, and legal professionals."},
    {"code": "ORGANIZATION", "name": "Organization", "price": "Talk to us", "description": "Shared workspaces and support for institutions."},
)


@app.route("/pricing")
def pricing():
    return render_template("pricing.html", plans=SUBSCRIPTION_PLANS)


@app.route("/billing", methods=("GET", "POST"))
@login_required
def billing():
    db = get_db()
    if request.method == "POST":
        plan_code = request.form.get("plan_code", "").strip().upper()
        plan = next((item for item in SUBSCRIPTION_PLANS if item["code"] == plan_code), None)
        if plan is None:
            flash("Choose a valid plan.", "danger")
            return redirect(url_for("billing"))
        status = "ACTIVE" if plan_code == "FREE" else "PAYMENT_REQUIRED"
        db.execute(
            """
            INSERT INTO subscriptions (user_id, plan_code, status, provider, started_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (g.user["id"], plan_code, status, "checkout_pending" if status == "PAYMENT_REQUIRED" else None, utc_now()),
        )
        db.commit()
        audit("select_plan", "subscription", plan_code)
        if status == "PAYMENT_REQUIRED":
            flash(f"{plan['name']} selected. Payment setup is not connected yet.", "warning")
        else:
            flash("Basic plan selected.", "success")
        return redirect(url_for("billing"))
    subscription = db.execute(
        "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (g.user["id"],)
    ).fetchone()
    return render_template("billing.html", plans=SUBSCRIPTION_PLANS, subscription=subscription)


@app.route("/land-search", methods=("GET", "POST"))
@login_required
def land_search():
    search = None
    if request.method == "POST":
        search_type = request.form.get("search_type", "").strip().upper()
        volume = request.form.get("volume", "").strip()
        folio = request.form.get("folio", "").strip()
        county = request.form.get("county", "").strip()
        block = request.form.get("block", "").strip()
        plot = request.form.get("plot", "").strip()
        title_complete = search_type == "TITLE" and volume and folio
        parcel_complete = search_type == "PARCEL" and county and block and plot
        if not title_complete and not parcel_complete:
            flash("Enter all the details for the selected search.", "danger")
            return render_template("land_search.html")
        reference = f"UG-SEARCH-{secrets.token_hex(6).upper()}"
        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO land_searches
                (search_reference, search_type, volume, folio, county, block, plot, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (reference, search_type, volume or None, folio or None, county or None, block or None, plot or None, g.user["id"], utc_now()),
            )
            db.commit()
        except DB_ERRORS:
            db.rollback()
            audit("land_search", "search", reference, "failed")
            flash("The land search could not be saved. No success was reported.", "danger")
            return render_template("land_search.html")
        search = db.execute("SELECT * FROM land_searches WHERE search_reference = ?", (reference,)).fetchone()
        audit("land_search", "search", search["id"])
    return render_template("land_search.html", search=search)


@app.route("/healthz")
def healthz():
    try:
        get_db().execute("SELECT 1").fetchone()
    except DB_ERRORS:
        return {"status": "unhealthy"}, 503
    return {"status": "healthy"}, 200


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        client_key = request.remote_addr or "unknown"
        now = time.monotonic()
        attempts = [timestamp for timestamp in login_attempts.get(client_key, []) if now - timestamp < LOGIN_WINDOW_SECONDS]
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            flash("Too many sign-in attempts. Try again later.", "danger")
            return render_template("login.html"), 429
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and user["status"] == "active" and check_password_hash(user["password_hash"], password):
            login_attempts.pop(client_key, None)
            session.clear()
            session["user_id"] = user["id"]
            audit("login", "user", user["id"])
            next_url = request.args.get("next", "")
            parsed = urlparse(next_url)
            safe_next = next_url if next_url.startswith("/") and not next_url.startswith("//") and not parsed.netloc else ""
            return redirect(safe_next or url_for("dashboard"))
        attempts.append(now)
        login_attempts[client_key] = attempts
        audit("login", "user", username, "denied")
        flash("Invalid credentials or disabled account.", "danger")
    return render_template("login.html")


@app.route("/register", methods=("GET", "POST"))
def register_account():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirmation = request.form.get("password_confirmation", "")
        if (
            len(username) < 3
            or len(username) > 80
            or not username.replace("_", "").replace("-", "").isalnum()
        ):
            flash("Use a username of 3-80 letters, numbers, hyphens, or underscores.", "danger")
            return render_template("register_account.html"), 400
        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return render_template("register_account.html"), 400
        if password != password_confirmation:
            flash("Passwords do not match.", "danger")
            return render_template("register_account.html"), 400
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, 'submitter', ?)",
                (username, generate_password_hash(password), utc_now()),
            )
            db.commit()
        except DB_INTEGRITY_ERRORS:
            db.rollback()
            flash("That username is already registered. Choose another.", "danger")
            return render_template("register_account.html"), 409
        audit("register_account", "user", username)
        flash("Account created. You can now sign in and register a document.", "success")
        return redirect(url_for("login"))
    return render_template("register_account.html")


@app.route("/logout", methods=("POST",))
def logout():
    if g.user:
        audit("logout", "user", g.user["id"])
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    if g.user["role"] == "reviewer":
        records = db.execute(
            "SELECT records.*, users.username AS submitter FROM records JOIN users ON users.id = records.submitter_id ORDER BY created_at DESC"
        ).fetchall()
    elif g.user["role"] == "administrator":
        records = db.execute("SELECT * FROM records ORDER BY created_at DESC").fetchall()
    else:
        records = db.execute(
            "SELECT * FROM records WHERE submitter_id = ? ORDER BY created_at DESC", (g.user["id"],)
        ).fetchall()
    return render_template("dashboard.html", records=records)


@app.route("/records/new", methods=("GET", "POST"))
@roles_required("submitter")
def register_record():
    if request.method == "POST":
        asset_type = request.form.get("asset_type", "").strip()
        area_label = request.form.get("area_label", "").strip()
        asset_fields = {
            "district": request.form.get("district", "").strip() or None,
            "county": request.form.get("county", "").strip() or None,
            "block": request.form.get("block", "").strip() or None,
            "plot": request.form.get("plot", "").strip() or None,
            "tenure": request.form.get("tenure", "").strip() or None,
            "title_volume": request.form.get("title_volume", "").strip() or None,
            "title_folio": request.form.get("title_folio", "").strip() or None,
            "registration_number": request.form.get("registration_number", "").strip() or None,
            "chassis_number": request.form.get("chassis_number", "").strip() or None,
            "engine_number": request.form.get("engine_number", "").strip() or None,
        }
        uploaded = request.files.get("document")
        if not asset_type or not area_label or not uploaded or not uploaded.filename:
            flash("Asset type, area label, and a document are required.", "danger")
            return render_template("register.html")
        asset_type_key = asset_type.lower()
        if asset_type_key in {"land", "land title", "title"} and (
            not asset_fields["district"] or not asset_fields["tenure"]
        ):
            flash("Land records require a district and tenure.", "danger")
            return render_template("register.html")
        if asset_type_key in {"vehicle", "vehicle logbook", "logbook"} and not asset_fields["registration_number"]:
            flash("Vehicle records require a registration number.", "danger")
            return render_template("register.html")
        if not allowed_file(uploaded.filename) or not valid_upload(uploaded):
            flash("Unsupported file type. Use PDF, PNG, JPG, JPEG, or TXT.", "danger")
            return render_template("register.html")
        digest = file_hash(uploaded)
        reference = f"UG-REC-{secrets.token_hex(6).upper()}"
        storage_key = f"{uuid.uuid4().hex}_{secure_filename(uploaded.filename)}"
        path = Path(app.config["UPLOAD_DIR"]) / storage_key
        uploaded.save(path)
        db = get_db()
        auto_approved = app.config["AUTO_APPROVE_RECORDS"]
        record_status = "APPROVED" if auto_approved else "PENDING_REVIEW"
        try:
            db.execute(
                """
                INSERT INTO records
                (public_reference, asset_type, area_label, submitter_id, file_storage_key, file_hash, status,
                 district, county, block, plot, tenure, title_volume, title_folio,
                 registration_number, chassis_number, engine_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reference, asset_type, area_label, g.user["id"], storage_key, digest, record_status,
                    asset_fields["district"], asset_fields["county"], asset_fields["block"],
                    asset_fields["plot"], asset_fields["tenure"], asset_fields["title_volume"],
                    asset_fields["title_folio"], asset_fields["registration_number"],
                    asset_fields["chassis_number"], asset_fields["engine_number"], utc_now(),
                ),
            )
            record_id = db.execute("SELECT id FROM records WHERE public_reference = ?", (reference,)).fetchone()["id"]
            db.execute(
                "INSERT INTO record_events (record_id, event_type, actor_id, event_time, event_status) VALUES (?, ?, ?, ?, ?)",
                (record_id, "REGISTERED", g.user["id"], utc_now(), "CONFIRMED"),
            )
            if auto_approved:
                db.execute(
                    "INSERT INTO record_events (record_id, event_type, actor_id, event_time, tx_hash, event_status) VALUES (?, ?, ?, ?, ?, ?)",
                    (record_id, "AUTO_APPROVED", g.user["id"], utc_now(), ledger_record(record_id, digest, "AUTO_APPROVED"), "CONFIRMED"),
                )
            db.commit()
        except DB_ERRORS:
            path.unlink(missing_ok=True)
            db.rollback()
            audit("register_record", "record", reference, "failed")
            flash("The record could not be saved. No success was reported.", "danger")
            return render_template("register.html")
        audit("register_record", "record", record_id)
        if auto_approved:
            flash(f"Record {reference} registered and automatically approved.", "success")
        else:
            flash(f"Record {reference} registered and is pending authorized review.", "success")
        return redirect(url_for("record_view", record_id=record_id))
    return render_template("register.html")


@app.route("/records/<int:record_id>")
@login_required
def record_view(record_id):
    record, events = record_details(record_id)
    if record is None:
        flash("Record not found.", "danger")
        return redirect(url_for("dashboard"))
    if g.user["role"] == "submitter" and record["submitter_id"] != g.user["id"]:
        audit("record_access", "record", record_id, "denied")
        flash("You cannot access that record.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("record.html", record=record, events=events)


@app.route("/records/<int:record_id>/report")
@login_required
def record_report(record_id):
    record, events = record_details(record_id)
    if record is None:
        flash("Record not found.", "danger")
        return redirect(url_for("dashboard"))
    if g.user["role"] == "submitter" and record["submitter_id"] != g.user["id"]:
        audit("record_report", "record", record_id, "denied")
        flash("You cannot access that record.", "danger")
        return redirect(url_for("dashboard"))
    rendered = render_template("report.html", record=record, events=events)
    response = make_response(rendered)
    response.headers["Content-Disposition"] = f'attachment; filename="{record["public_reference"]}-report.html"'
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    audit("record_report", "record", record_id)
    return response


@app.route("/verify", methods=("GET", "POST"))
def verify():
    result = None
    record = None
    events = []
    submitted_hash = None
    if request.method == "POST":
        reference = request.form.get("reference", "").strip()
        uploaded = request.files.get("document")
        if not uploaded or not uploaded.filename:
            result = "DOCUMENT_REQUIRED"
            return render_template("verify.html", result=result, record=record, events=events, submitted_hash=submitted_hash)
        if not allowed_file(uploaded.filename) or not valid_upload(uploaded):
            result = "INVALID_DOCUMENT"
            audit("verify_record", "record", reference or "unknown", "invalid_document")
            return render_template("verify.html", result=result, record=record, events=events, submitted_hash=submitted_hash)
        submitted_hash = file_hash(uploaded)
        if reference:
            record = get_db().execute("SELECT * FROM records WHERE public_reference = ?", (reference,)).fetchone()
            if record is None:
                result = "RECORD_NOT_FOUND"
            else:
                result = "HASH_MATCH" if submitted_hash == record["file_hash"] else "HASH_MISMATCH"
        else:
            record = get_db().execute("SELECT * FROM records WHERE file_hash = ? ORDER BY created_at DESC LIMIT 1", (submitted_hash,)).fetchone()
            result = "HASH_MATCH" if record else "DOCUMENT_NOT_AUTHENTICATED"
        if record:
            get_db().execute(
                "INSERT INTO verification_checks (record_id, submitted_hash, result, checked_by, checked_at) VALUES (?, ?, ?, ?, ?)",
                (record["id"], submitted_hash, result, g.user["id"] if g.user else None, utc_now()),
            )
            get_db().commit()
            events = record_details(record["id"])[1]
        audit("verify_record", "record", reference or (record["id"] if record else "unknown"), "success" if record else "not_found")
    return render_template("verify.html", result=result, record=record, events=events, submitted_hash=submitted_hash)


@app.route("/records/<int:record_id>/review", methods=("POST",))
@roles_required("reviewer", "administrator")
def review_record(record_id):
    decision = request.form.get("decision", "")
    reason = request.form.get("reason", "").strip()
    statuses = {"approve": "APPROVED", "reject": "REVIEW_REJECTED", "flag": "PENDING_REVIEW"}
    if decision not in statuses or (decision in {"reject", "flag"} and not reason):
        flash("Choose a valid decision and provide a reason when required.", "danger")
        return redirect(url_for("record_view", record_id=record_id))
    record = get_db().execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    if record is None:
        flash("Record not found.", "danger")
        return redirect(url_for("dashboard"))
    if record["status"] != "PENDING_REVIEW":
        flash("Only records pending review can receive a new decision.", "danger")
        return redirect(url_for("record_view", record_id=record_id))
    status = statuses[decision]
    tx_hash = ledger_record(record_id, record["file_hash"], "REVIEWED") if decision == "approve" else None
    db = get_db()
    event_time = utc_now()
    try:
        db.execute("BEGIN")
        updated = db.execute(
            "UPDATE records SET status = ?, review_reason = ? WHERE id = ? AND status = 'PENDING_REVIEW'",
            (status, reason or None, record_id),
        )
        if updated.rowcount != 1:
            db.rollback()
            flash("This record was already reviewed. Refresh and try again.", "danger")
            return redirect(url_for("record_view", record_id=record_id))
        db.execute(
            "INSERT INTO record_events (record_id, event_type, actor_id, event_time, reason, tx_hash, event_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record_id, "REVIEWED", g.user["id"], event_time, reason or None, tx_hash, "CONFIRMED" if tx_hash else "APPLICATION_ONLY"),
        )
        db.commit()
    except DB_ERRORS:
        db.rollback()
        audit("review_record", "record", record_id, "failed")
        flash("The review could not be saved. No success was reported.", "danger")
        return redirect(url_for("record_view", record_id=record_id))
    audit("review_record", "record", record_id)
    flash("Review decision saved.", "success")
    return redirect(url_for("record_view", record_id=record_id))


@app.route("/admin")
@roles_required("administrator")
def admin():
    users = get_db().execute("SELECT id, username, role, status, created_at FROM users ORDER BY username").fetchall()
    logs = get_db().execute(
        """
        SELECT security_audit_logs.*, users.username
        FROM security_audit_logs LEFT JOIN users ON users.id = security_audit_logs.actor_id
        ORDER BY timestamp DESC LIMIT 50
        """
    ).fetchall()
    return render_template("admin.html", users=users, logs=logs)


@app.route("/admin/users/<int:user_id>/toggle", methods=("POST",))
@roles_required("administrator")
def toggle_user(user_id):
    if user_id == g.user["id"]:
        flash("You cannot disable your own account.", "danger")
        return redirect(url_for("admin"))
    db = get_db()
    user = db.execute("SELECT status FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        flash("User not found.", "danger")
    else:
        status = "disabled" if user["status"] == "active" else "active"
        db.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
        db.commit()
        audit("toggle_user", "user", user_id)
        flash("User status updated.", "success")
    return redirect(url_for("admin"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=False, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
