import sqlite3
import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "tokens.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def clean_phone_number(phone_number: str | None) -> str:
    if not phone_number:
        return ""
    p = str(phone_number).strip().replace(" ", "").replace("whatsapp:", "").replace("@c.us", "").replace("@g.us", "")
    if p.startswith("%2B") or p.startswith("%2b"):
        p = "+" + p[3:]
    if not p.startswith("+"):
        p = "+" + p
    return p

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_accounts (
            phone_number TEXT PRIMARY KEY,
            active_email TEXT NOT NULL,
            creds_data TEXT NOT NULL,
            auth_type TEXT NOT NULL DEFAULT 'oauth',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_drafts (
            phone_number TEXT PRIMARY KEY,
            target_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            media_url TEXT,
            file_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_media_buffer (
            phone_number TEXT PRIMARY KEY,
            media_url TEXT NOT NULL,
            file_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        try:
            cursor.execute("ALTER TABLE recent_media_buffer ADD COLUMN file_name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE pending_drafts ADD COLUMN file_name TEXT")
        except sqlite3.OperationalError:
            pass
        # Auto-migrate any phone numbers missing '+' or having spaces
        try:
            cursor.execute("UPDATE user_accounts SET phone_number = '+' || TRIM(phone_number) WHERE phone_number NOT LIKE '+%'")
            cursor.execute("UPDATE pending_drafts SET phone_number = '+' || TRIM(phone_number) WHERE phone_number NOT LIKE '+%'")
            cursor.execute("UPDATE recent_media_buffer SET phone_number = '+' || TRIM(phone_number) WHERE phone_number NOT LIKE '+%'")
        except Exception:
            pass
        conn.commit()

def save_recent_media(phone_number: str, media_url: str, file_name: str = None):
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO recent_media_buffer (phone_number, media_url, file_name, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(phone_number) DO UPDATE SET
            media_url=excluded.media_url,
            file_name=COALESCE(excluded.file_name, recent_media_buffer.file_name),
            created_at=CURRENT_TIMESTAMP
        """, (phone_number, media_url, file_name))
        conn.commit()

def get_recent_media(phone_number: str, max_age_seconds: int = 180) -> tuple[str | None, str | None]:
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT media_url, file_name FROM recent_media_buffer
        WHERE phone_number = ? AND (strftime('%s', 'now') - strftime('%s', created_at)) <= ?
        """, (phone_number, max_age_seconds))
        row = cursor.fetchone()
        if row:
            return row["media_url"], row["file_name"]
        return None, None

def clear_recent_media(phone_number: str):
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recent_media_buffer WHERE phone_number = ?", (phone_number,))
        conn.commit()

def save_user_credentials(phone_number: str, active_email: str, creds_data: dict, auth_type: str = 'oauth'):
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_accounts (phone_number, active_email, creds_data, auth_type, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(phone_number) DO UPDATE SET
            active_email=excluded.active_email,
            creds_data=excluded.creds_data,
            auth_type=excluded.auth_type,
            updated_at=CURRENT_TIMESTAMP
        """, (phone_number, active_email, json.dumps(creds_data), auth_type))
        conn.commit()

def get_user_credentials(phone_number: str):
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_accounts WHERE phone_number = ?", (phone_number,))
        row = cursor.fetchone()
        if row:
            return {
                "phone_number": row["phone_number"],
                "active_email": row["active_email"],
                "creds_data": json.loads(row["creds_data"]),
                "auth_type": row["auth_type"]
            }
        return None

def delete_user_credentials(phone_number: str):
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_accounts WHERE phone_number = ?", (phone_number,))
        conn.commit()

def save_pending_draft(phone_number: str, target_email: str, subject: str, body: str, media_url: str = None, file_name: str = None):
    init_db()
    phone_number = clean_phone_number(phone_number)
    cached_media, cached_fname = get_recent_media(phone_number)
    if not media_url:
        media_url = cached_media
        if not file_name:
            file_name = cached_fname
        if not media_url:
            existing = get_pending_draft(phone_number)
            if existing and existing.get("media_url"):
                media_url = existing.get("media_url")
                if not file_name:
                    file_name = existing.get("file_name")
    else:
        save_recent_media(phone_number, media_url, file_name)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO pending_drafts (phone_number, target_email, subject, body, media_url, file_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(phone_number) DO UPDATE SET
            target_email=excluded.target_email,
            subject=excluded.subject,
            body=excluded.body,
            media_url=excluded.media_url,
            file_name=COALESCE(excluded.file_name, pending_drafts.file_name),
            created_at=CURRENT_TIMESTAMP
        """, (phone_number, target_email, subject, body, media_url, file_name))
        conn.commit()

def get_pending_draft(phone_number: str):
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_drafts WHERE phone_number = ?", (phone_number,))
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            return {
                "target_email": row_dict["target_email"],
                "subject": row_dict["subject"],
                "body": row_dict["body"],
                "media_url": row_dict.get("media_url"),
                "file_name": row_dict.get("file_name")
            }
        return None

def clear_pending_draft(phone_number: str):
    init_db()
    phone_number = clean_phone_number(phone_number)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_drafts WHERE phone_number = ?", (phone_number,))
        cursor.execute("DELETE FROM recent_media_buffer WHERE phone_number = ?", (phone_number,))
        conn.commit()

# Initialize DB on module import
init_db()
