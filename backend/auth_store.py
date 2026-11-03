"""Persistent authentication store for Crediclass.

The application previously kept login credentials in source code.  This module
uses SQLite for users, one-time invitations, revocable sessions and audit logs.
Passwords are never stored directly; PBKDF2-HMAC-SHA256 hashes are used with a
unique salt per user.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
AUTH_DB_PATH = Path(__import__("os").getenv("AUTH_DB_PATH", str(BASE_DIR / "data" / "auth.sqlite3")))
PBKDF2_ITERATIONS = 310_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUTH_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def _public_user(row: sqlite3.Row | dict) -> dict:
    source = dict(row)
    return {
        "id": source["id"],
        "usuario": source["username"],
        "nome": source["name"],
        "email": source["email"],
        "whatsapp": source["whatsapp"],
        "perfil": source["role"],
        "status": source["status"],
        "ultimo_acesso": source["last_login"] or "",
        "criado_em": source["created_at"],
        "convite_expira_em": source["invite_expires_at"] or "",
    }


def init_auth_store(legacy_users: dict[str, dict] | None = None) -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                whatsapp TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'Operador',
                status TEXT NOT NULL DEFAULT 'Ativo',
                password_hash TEXT,
                session_version INTEGER NOT NULL DEFAULT 1,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                last_login TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                invite_token_hash TEXT,
                invite_expires_at TEXT,
                reset_token_hash TEXT,
                reset_expires_at TEXT
            );
            """
        )
        for column in ("reset_token_hash TEXT", "reset_expires_at TEXT"):
            try:
                db.execute(f"ALTER TABLE auth_users ADD COLUMN {column}")
            except sqlite3.OperationalError:
                pass
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES auth_users(id),
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                ip TEXT,
                user_agent TEXT
            );
            CREATE TABLE IF NOT EXISTS auth_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER,
                target_user_id INTEGER,
                action TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_token ON auth_sessions(token_hash);
            CREATE INDEX IF NOT EXISTS idx_auth_audit_created ON auth_audit(created_at);
            """
        )
        now = _now()
        for username, legacy in (legacy_users or {}).items():
            email = f"{username}@crediclass.local"
            existing = db.execute("SELECT id FROM auth_users WHERE username = ?", (username,)).fetchone()
            if existing:
                continue
            db.execute(
                """INSERT INTO auth_users
                (username, name, email, role, status, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Ativo', ?, ?, ?)""",
                (username, legacy["name"], email, legacy["role"], _hash_password(legacy["password"]), now, now),
            )


def authenticate(username: str, password: str) -> sqlite3.Row | None:
    with _connect() as db:
        row = db.execute("SELECT * FROM auth_users WHERE username = ? OR lower(email) = lower(?)", (username, username)).fetchone()
        if not row or row["status"] != "Ativo" or not row["password_hash"] or not _verify_password(password, row["password_hash"]):
            if row:
                next_attempts = int(row["failed_attempts"] or 0) + 1
                status = "Bloqueado" if next_attempts >= 5 else row["status"]
                db.execute("UPDATE auth_users SET failed_attempts = ?, status = ?, updated_at = ? WHERE id = ?", (next_attempts, status, _now(), row["id"]))
            return None
        db.execute("UPDATE auth_users SET failed_attempts = 0, last_login = ?, updated_at = ? WHERE id = ?", (_now(), _now(), row["id"]))
        return db.execute("SELECT * FROM auth_users WHERE id = ?", (row["id"],)).fetchone()


def create_session(user_id: int, ip: str = "", user_agent: str = "", hours: int = 12) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with _connect() as db:
        db.execute("INSERT INTO auth_sessions (user_id, token_hash, created_at, expires_at, ip, user_agent) VALUES (?, ?, ?, ?, ?, ?)", (user_id, token_hash, now.isoformat(), (now.timestamp() + hours * 3600), ip, user_agent[:300]))
    return raw


def get_session(raw_token: str | None) -> sqlite3.Row | None:
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with _connect() as db:
        return db.execute(
            """SELECT s.*, u.username, u.name, u.email, u.whatsapp, u.role, u.status, u.last_login, u.created_at, u.invite_expires_at
               FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.revoked_at IS NULL AND u.status = 'Ativo' AND s.expires_at > ?""",
            (token_hash, str(datetime.now(timezone.utc).timestamp())),
        ).fetchone()


def revoke_session(raw_token: str | None) -> None:
    if not raw_token:
        return
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with _connect() as db:
        db.execute("UPDATE auth_sessions SET revoked_at = ? WHERE token_hash = ?", (_now(), token_hash))


def list_users() -> list[dict]:
    with _connect() as db:
        return [_public_user(row) for row in db.execute("SELECT * FROM auth_users ORDER BY name COLLATE NOCASE")]


def get_user(username: str) -> sqlite3.Row | None:
    with _connect() as db:
        return db.execute("SELECT * FROM auth_users WHERE username = ?", (username,)).fetchone()


def create_invitation(name: str, email: str, whatsapp: str, role: str, actor_id: int) -> tuple[dict, str]:
    username = email.strip().lower()
    token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(now.timestamp() + 48 * 3600, timezone.utc).isoformat()
    with _connect() as db:
        try:
            cursor = db.execute("""INSERT INTO auth_users (username, name, email, whatsapp, role, status, created_at, updated_at, invite_token_hash, invite_expires_at)
                VALUES (?, ?, ?, ?, ?, 'Convite pendente', ?, ?, ?, ?)""", (username, name.strip(), email.strip().lower(), whatsapp.strip(), role, now.isoformat(), now.isoformat(), token_hash, expires))
        except sqlite3.IntegrityError as error:
            raise ValueError("Já existe um usuário com este e-mail.") from error
        user_id = cursor.lastrowid
        db.execute("INSERT INTO auth_audit (actor_user_id, target_user_id, action, detail, created_at) VALUES (?, ?, 'convite_criado', ?, ?)", (actor_id, user_id, email.strip().lower(), now.isoformat()))
        row = db.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row), token


def resend_invitation(user_id: int, actor_id: int) -> str | None:
    token = secrets.token_urlsafe(36)
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(now.timestamp() + 48 * 3600, timezone.utc).isoformat()
    with _connect() as db:
        row = db.execute("SELECT id, status FROM auth_users WHERE id = ?", (user_id,)).fetchone()
        if not row or row["status"] != "Convite pendente":
            return None
        db.execute("UPDATE auth_users SET invite_token_hash = ?, invite_expires_at = ?, updated_at = ? WHERE id = ?", (hashlib.sha256(token.encode()).hexdigest(), expires, now.isoformat(), user_id))
        db.execute("INSERT INTO auth_audit (actor_user_id, target_user_id, action, detail, created_at) VALUES (?, ?, 'convite_reenviado', 'novo link gerado', ?)", (actor_id, user_id, now.isoformat()))
    return token


def update_user(user_id: int, name: str, email: str, whatsapp: str, role: str, actor_id: int) -> dict | None:
    if role not in {"Operador", "Administrador"}:
        raise ValueError("Perfil inválido.")
    with _connect() as db:
        row = db.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        try:
            db.execute("UPDATE auth_users SET name = ?, email = ?, username = ?, whatsapp = ?, role = ?, updated_at = ? WHERE id = ?", (name.strip(), email.strip().lower(), email.strip().lower(), whatsapp.strip(), role, _now(), user_id))
        except sqlite3.IntegrityError as error:
            raise ValueError("Já existe um usuário com este e-mail.") from error
        db.execute("INSERT INTO auth_audit (actor_user_id, target_user_id, action, detail, created_at) VALUES (?, ?, 'dados_alterados', ?, ?)", (actor_id, user_id, email.strip().lower(), _now()))
        return _public_user(db.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,)).fetchone())


def create_password_reset(user_id: int, actor_id: int) -> str | None:
    token = secrets.token_urlsafe(36)
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(now.timestamp() + 60 * 60, timezone.utc).isoformat()
    with _connect() as db:
        row = db.execute("SELECT id FROM auth_users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        db.execute("UPDATE auth_users SET reset_token_hash = ?, reset_expires_at = ?, updated_at = ? WHERE id = ?", (hashlib.sha256(token.encode()).hexdigest(), expires, now.isoformat(), user_id))
        db.execute("INSERT INTO auth_audit (actor_user_id, target_user_id, action, detail, created_at) VALUES (?, ?, 'redefinicao_solicitada', 'link administrativo', ?)", (actor_id, user_id, now.isoformat()))
    return token


def reset_password(token: str, password: str) -> sqlite3.Row | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    with _connect() as db:
        row = db.execute("SELECT * FROM auth_users WHERE reset_token_hash = ? AND reset_expires_at > ?", (token_hash, now.isoformat())).fetchone()
        if not row:
            return None
        db.execute("UPDATE auth_users SET password_hash = ?, status = 'Ativo', failed_attempts = 0, reset_token_hash = NULL, reset_expires_at = NULL, session_version = session_version + 1, updated_at = ? WHERE id = ?", (_hash_password(password), now.isoformat(), row["id"]))
        db.execute("UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (now.isoformat(), row["id"]))
        db.execute("INSERT INTO auth_audit (target_user_id, action, detail, created_at) VALUES (?, 'senha_redefinida', 'link utilizado', ?)", (row["id"], now.isoformat()))
        return db.execute("SELECT * FROM auth_users WHERE id = ?", (row["id"],)).fetchone()


def activate_invitation(token: str, password: str) -> sqlite3.Row | None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with _connect() as db:
        row = db.execute("SELECT * FROM auth_users WHERE invite_token_hash = ? AND status = 'Convite pendente' AND invite_expires_at > ?", (token_hash, now.isoformat())).fetchone()
        if not row:
            return None
        db.execute("UPDATE auth_users SET password_hash = ?, status = 'Ativo', invite_token_hash = NULL, invite_expires_at = NULL, updated_at = ? WHERE id = ?", (_hash_password(password), now.isoformat(), row["id"]))
        db.execute("INSERT INTO auth_audit (target_user_id, action, detail, created_at) VALUES (?, 'convite_ativado', ?, ?)", (row["id"], row["email"], now.isoformat()))
        return db.execute("SELECT * FROM auth_users WHERE id = ?", (row["id"],)).fetchone()


def set_user_status(user_id: int, status: str, actor_id: int) -> dict | None:
    if status not in {"Ativo", "Inativo", "Bloqueado"}:
        raise ValueError("Status de usuário inválido.")
    with _connect() as db:
        row = db.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        db.execute("UPDATE auth_users SET status = ?, session_version = session_version + 1, updated_at = ? WHERE id = ?", (status, _now(), user_id))
        db.execute("UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (_now(), user_id))
        db.execute("INSERT INTO auth_audit (actor_user_id, target_user_id, action, detail, created_at) VALUES (?, ?, 'status_alterado', ?, ?)", (actor_id, user_id, status, _now()))
        return _public_user(db.execute("SELECT * FROM auth_users WHERE id = ?", (user_id,)).fetchone())


def audit_events(limit: int = 100) -> list[dict]:
    with _connect() as db:
        rows = db.execute("SELECT * FROM auth_audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


def public_user(row: sqlite3.Row) -> dict:
    return _public_user(row)
