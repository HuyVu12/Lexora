"""Local accounts, roles and sessions for the Lexora workspace (standard library only).

Four roles: `admin` manages accounts and can do everything, `reviewer` imports, reviews and
publishes, `reader` asks questions over published knowledge bases, `dev` asks questions like a reader and
monitors the system (model calls, usage, results report) and sets the model-call limits and switches. Passwords are hashed with
scrypt and a per-user salt; sessions are random tokens stored only as SHA-256 digests with an
expiry. Repeated failed logins lock an account for a short time. There is no self sign-up: the
first admin is created on the machine with `python -m legal_ai.auth create-admin`.
"""

import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import getpass
import hashlib
import hmac
import secrets
import sqlite3
import sys
import threading

ROLES = ("admin", "reviewer", "reader", "dev")
SESSION_HOURS = 12
MAX_FAILURES = 5
LOCK_MINUTES = 5
SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
MIN_PASSWORD = 10


class AuthError(ValueError):
    """Login refused; the message never says whether the user exists."""


def now():
    return datetime.now(timezone.utc)


def stamp(moment):
    return moment.isoformat(timespec="seconds")


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, maxmem=64 * 1024 * 1024, **SCRYPT)
    return f"scrypt${SCRYPT['n']}${SCRYPT['r']}${SCRYPT['p']}${salt.hex()}${digest.hex()}"


def check_password(password, stored):
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    candidate = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                               dklen=len(bytes.fromhex(digest)), maxmem=64 * 1024 * 1024)
    return hmac.compare_digest(candidate.hex(), digest)


def validate_password(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise ValueError(f"Mật khẩu cần ít nhất {MIN_PASSWORD} ký tự")


def validate_username(username):
    if not isinstance(username, str) or not 3 <= len(username) <= 64 or not all(c.isalnum() or c in "._-" for c in username):
        raise ValueError("Tên đăng nhập gồm 3 đến 64 ký tự chữ, số, dấu chấm, gạch dưới hoặc gạch ngang")
    return username.lower()


def session_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountStore:
    """Accounts and sessions in the same SQLite file as the knowledge bases, in their own tables."""

    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.Lock()
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'reviewer', 'reader', 'dev')),
                    password TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    failures INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    digest TEXT PRIMARY KEY,
                    account_id INTEGER NOT NULL REFERENCES accounts(id),
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_owners (
                    chat_id TEXT PRIMARY KEY,
                    account_id INTEGER NOT NULL REFERENCES accounts(id)
                );
            """)
        self._allow_all_roles()

    def _allow_all_roles(self):
        """Stores made before the `dev` role have a CHECK constraint without it; rebuild the table, keeping every row and ID."""
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            sql = db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'accounts'").fetchone()[0]
            if all(f"'{role}'" in sql for role in ROLES):
                return
            allowed = ", ".join(f"'{role}'" for role in ROLES)
            new_sql = sql.replace(sql[sql.index("CHECK (role IN"):sql.index(")", sql.index("CHECK (role IN")) + 2], f"CHECK (role IN ({allowed}))")
            # Sessions and chat owners reference accounts(id) by name; keep those references while the table is swapped.
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute("PRAGMA legacy_alter_table = ON")
            with db:
                db.execute(new_sql.replace("CREATE TABLE accounts", "CREATE TABLE accounts_roles", 1))
                db.execute("INSERT INTO accounts_roles SELECT * FROM accounts")
                db.execute("DROP TABLE accounts")
                db.execute("ALTER TABLE accounts_roles RENAME TO accounts")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return closing_commit(db)

    @staticmethod
    def public(row):
        return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "role": row["role"],
                "active": bool(row["active"]), "created_at": row["created_at"]}

    def count(self):
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    def create(self, username, display_name, role, password):
        username = validate_username(username)
        if role not in ROLES:
            raise ValueError("Vai trò không hợp lệ")
        display_name = (display_name or "").strip()
        if not 1 <= len(display_name) <= 100:
            raise ValueError("Tên hiển thị gồm 1 đến 100 ký tự")
        validate_password(password)
        with self.lock, self.connect() as db:
            if db.execute("SELECT 1 FROM accounts WHERE username = ?", (username,)).fetchone():
                raise ValueError("Tên đăng nhập đã tồn tại")
            cursor = db.execute("INSERT INTO accounts (username, display_name, role, password, created_at) VALUES (?, ?, ?, ?, ?)",
                                (username, display_name, role, hash_password(password), stamp(now())))
            return self.public(db.execute("SELECT * FROM accounts WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def list(self):
        with self.connect() as db:
            return [self.public(r) for r in db.execute("SELECT * FROM accounts ORDER BY role, username")]

    def update(self, account_id, *, actor_id, role=None, active=None, password=None, display_name=None):
        with self.lock, self.connect() as db:
            row = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if row is None:
                raise ValueError("Không tìm thấy tài khoản")
            if account_id == actor_id and (role not in (None, row["role"]) or active is False):
                raise ValueError("Không thể tự đổi vai trò hoặc tự khóa tài khoản của mình")
            if role is not None and role not in ROLES:
                raise ValueError("Vai trò không hợp lệ")
            demoting_admin = row["role"] == "admin" and ((role is not None and role != "admin") or active is False)
            if demoting_admin and db.execute("SELECT COUNT(*) FROM accounts WHERE role = 'admin' AND active = 1").fetchone()[0] <= 1:
                raise ValueError("Phải còn ít nhất một quản trị đang hoạt động")
            if role is not None:
                db.execute("UPDATE accounts SET role = ? WHERE id = ?", (role, account_id))
            if display_name is not None:
                name = display_name.strip()
                if not 1 <= len(name) <= 100:
                    raise ValueError("Tên hiển thị gồm 1 đến 100 ký tự")
                db.execute("UPDATE accounts SET display_name = ? WHERE id = ?", (name, account_id))
            if active is not None:
                db.execute("UPDATE accounts SET active = ? WHERE id = ?", (1 if active else 0, account_id))
            if password is not None:
                validate_password(password)
                db.execute("UPDATE accounts SET password = ?, failures = 0, locked_until = NULL WHERE id = ?", (hash_password(password), account_id))
            if active is False or password is not None or role is not None:
                db.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))  # Changes take effect immediately.
            return self.public(db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone())

    def login(self, username, password):
        """Return (session token, account) or raise AuthError with one generic message.

        Failure counters are committed before the error is raised, so a refused login is never rolled back."""
        refused = "Tên đăng nhập hoặc mật khẩu không đúng"
        try:
            username = validate_username(username)
        except ValueError:
            raise AuthError(refused) from None
        failure = None
        with self.lock, self.connect() as db:
            row = db.execute("SELECT * FROM accounts WHERE username = ?", (username,)).fetchone()
            if row is None:
                check_password(password or "", hash_password("timing-equaliser"))
                failure = refused
            elif row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > now():
                failure = "Tài khoản tạm khóa do đăng nhập sai nhiều lần; thử lại sau ít phút"
            elif not check_password(password or "", row["password"]) or not row["active"]:
                failures = row["failures"] + 1
                locked = stamp(now() + timedelta(minutes=LOCK_MINUTES)) if failures >= MAX_FAILURES else None
                db.execute("UPDATE accounts SET failures = ?, locked_until = ? WHERE id = ?", (0 if locked else failures, locked, row["id"]))
                failure = refused
            else:
                db.execute("UPDATE accounts SET failures = 0, locked_until = NULL WHERE id = ?", (row["id"],))
                db.execute("DELETE FROM sessions WHERE expires_at < ?", (stamp(now()),))
                token = secrets.token_urlsafe(32)
                db.execute("INSERT INTO sessions (digest, account_id, expires_at) VALUES (?, ?, ?)",
                           (session_digest(token), row["id"], stamp(now() + timedelta(hours=SESSION_HOURS))))
        if failure:
            raise AuthError(failure)
        return token, self.public(row)

    def session(self, token):
        if not token:
            return None
        with self.connect() as db:
            row = db.execute("""SELECT a.*, s.expires_at FROM sessions s JOIN accounts a ON a.id = s.account_id
                                WHERE s.digest = ?""", (session_digest(token),)).fetchone()
            if row is None or not row["active"] or datetime.fromisoformat(row["expires_at"]) < now():
                return None
            return self.public(row)

    def activity(self):
        """Counts only: accounts by role and active state, and sessions that have not expired."""
        with self.connect() as db:
            roles = {f"{r['role']}{'' if r['active'] else '_inactive'}": r["n"] for r in db.execute(
                "SELECT role, active, COUNT(*) AS n FROM accounts GROUP BY role, active")}
            live = db.execute("SELECT COUNT(*) FROM sessions WHERE expires_at > ?", (stamp(now()),)).fetchone()[0]
        return {"accounts": roles, "active_sessions": live}

    def own_chat(self, chat_id, account_id):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO chat_owners (chat_id, account_id) VALUES (?, ?)", (chat_id, account_id))

    def chats_of(self, account_id):
        """Chat session ids this account owns; chats started before accounts existed belong to nobody."""
        with self.connect() as db:
            return {r[0] for r in db.execute("SELECT chat_id FROM chat_owners WHERE account_id = ?", (account_id,))}

    def logout(self, token):
        if token:
            with self.connect() as db:
                db.execute("DELETE FROM sessions WHERE digest = ?", (session_digest(token),))


class closing_commit:
    """`with store.connect() as db`: commit on success, roll back on error, always close."""

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, kind, *_):
        with closing(self.db):
            if kind is None:
                self.db.commit()
            else:
                self.db.rollback()


def main():
    parser = argparse.ArgumentParser(description="Manage Lexora accounts on this machine")
    parser.add_argument("command", choices=["create-admin", "list"])
    parser.add_argument("--store", required=True, help="The workspace SQLite store, as passed to legal_ai.web")
    parser.add_argument("--username")
    parser.add_argument("--name", help="Display name")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Vietnamese display names on a Windows console.
    accounts = AccountStore(args.store)
    if args.command == "list":
        for account in accounts.list():
            print(f"{account['username']}\t{account['role']}\t{'active' if account['active'] else 'locked'}\t{account['display_name']}")
        return
    if not args.username:
        parser.error("create-admin needs --username")
    password = getpass.getpass("Mật khẩu (ít nhất 10 ký tự): ")
    if password != getpass.getpass("Nhập lại mật khẩu: "):
        parser.error("Hai lần nhập mật khẩu không khớp")
    account = accounts.create(args.username, args.name or args.username, "admin", password)
    print(f"Đã tạo quản trị {account['username']}")


if __name__ == "__main__":
    main()
