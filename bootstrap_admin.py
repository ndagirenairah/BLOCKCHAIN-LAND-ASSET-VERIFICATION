import os
import sys

from werkzeug.security import generate_password_hash

from app import DB_INTEGRITY_ERRORS, app, get_db, init_db, utc_now


def main():
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not username or not password or len(password) < 14:
        raise SystemExit("Set ADMIN_USERNAME and an ADMIN_PASSWORD of at least 14 characters.")
    with app.app_context():
        init_db()
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, 'administrator', ?)",
                (username.strip(), generate_password_hash(password), utc_now()),
            )
            db.commit()
        except DB_INTEGRITY_ERRORS:
            db.rollback()
            raise SystemExit(f"Administrator {username!r} could not be created; the username may already exist.")
    print(f"Administrator {username!r} created.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Administrator bootstrap failed: {error}", file=sys.stderr)
        raise
