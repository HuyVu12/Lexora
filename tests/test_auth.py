"""Accounts, roles, sessions and lockout for the local workspace."""

from contextlib import closing
from datetime import timedelta
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legal_ai import auth
from legal_ai.auth import AccountStore, AuthError, check_password, hash_password
from legal_ai.kb.import_review import ReviewStore


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "store.sqlite"
        fast = mock.patch.dict(auth.SCRYPT, {"n": 2 ** 4})  # Same code path, test-speed cost.
        fast.start()
        self.addCleanup(fast.stop)
        ReviewStore(self.path)  # Accounts live beside the knowledge bases in one file.
        self.accounts = AccountStore(self.path)
        self.admin = self.accounts.create("Admin", "Quản trị", "admin", "correct horse battery")

    def tearDown(self):
        self.temp.cleanup()

    def test_password_hash_is_salted_scrypt_and_verifies(self):
        first, second = hash_password("mật khẩu dài"), hash_password("mật khẩu dài")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("scrypt$"))
        self.assertTrue(check_password("mật khẩu dài", first))
        self.assertFalse(check_password("mật khẩu sai", first))
        self.assertFalse(check_password("x", "not-a-hash"))

    def test_usernames_are_case_insensitive_unique_and_validated(self):
        self.assertEqual(self.admin["username"], "admin")
        with self.assertRaises(ValueError):
            self.accounts.create("ADMIN", "x", "reader", "another long pass")
        for bad in ("ab", "có dấu cách", "a/b"):
            with self.assertRaises(ValueError):
                self.accounts.create(bad, "x", "reader", "another long pass")
        with self.assertRaises(ValueError):
            self.accounts.create("short", "x", "reader", "short")
        with self.assertRaises(ValueError):
            self.accounts.create("someone", "x", "owner", "another long pass")

    def test_login_session_and_logout(self):
        token, account = self.accounts.login("ADMIN", "correct horse battery")
        self.assertEqual(account["role"], "admin")
        self.assertEqual(self.accounts.session(token)["username"], "admin")
        with closing(sqlite3.connect(self.path)) as db:
            stored = db.execute("SELECT digest FROM sessions").fetchone()[0]
        self.assertNotEqual(stored, token)
        self.accounts.logout(token)
        self.assertIsNone(self.accounts.session(token))
        self.assertIsNone(self.accounts.session(""))

    def test_wrong_password_and_unknown_user_share_one_message_and_lock_after_five(self):
        with self.assertRaises(AuthError) as unknown:
            self.accounts.login("nobody", "whatever password")
        for _ in range(auth.MAX_FAILURES):
            with self.assertRaises(AuthError) as wrong:
                self.accounts.login("admin", "wrong password!!")
        self.assertEqual(str(unknown.exception), str(wrong.exception))
        with self.assertRaises(AuthError) as locked:
            self.accounts.login("admin", "correct horse battery")
        self.assertIn("tạm khóa", str(locked.exception))
        later = auth.now() + timedelta(minutes=auth.LOCK_MINUTES + 1)
        with mock.patch.object(auth, "now", return_value=later):
            self.assertEqual(self.accounts.login("admin", "correct horse battery")[1]["username"], "admin")

    def test_expired_session_is_rejected(self):
        token, _ = self.accounts.login("admin", "correct horse battery")
        later = auth.now() + timedelta(hours=auth.SESSION_HOURS + 1)
        with mock.patch.object(auth, "now", return_value=later):
            self.assertIsNone(self.accounts.session(token))

    def test_admin_updates_revoke_sessions_and_keep_one_active_admin(self):
        reader = self.accounts.create("hr.lan", "Nhân sự", "reader", "reader password 1")
        token, _ = self.accounts.login("hr.lan", "reader password 1")
        self.accounts.update(reader["id"], actor_id=self.admin["id"], role="reviewer")
        self.assertIsNone(self.accounts.session(token))
        token, account = self.accounts.login("hr.lan", "reader password 1")
        self.assertEqual(account["role"], "reviewer")
        self.accounts.update(reader["id"], actor_id=self.admin["id"], active=False)
        self.assertIsNone(self.accounts.session(token))
        with self.assertRaises(AuthError):
            self.accounts.login("hr.lan", "reader password 1")
        with self.assertRaises(ValueError):
            self.accounts.update(self.admin["id"], actor_id=self.admin["id"], role="reader")
        other = self.accounts.create("admin2", "Quản trị 2", "admin", "second admin pass")
        with self.assertRaises(ValueError):
            self.accounts.update(other["id"], actor_id=other["id"], active=False)
        self.accounts.update(other["id"], actor_id=self.admin["id"], active=False)
        with self.assertRaises(ValueError):
            self.accounts.update(self.admin["id"], actor_id=other["id"], active=False)

    def test_password_reset_clears_lockout(self):
        for _ in range(auth.MAX_FAILURES):
            with self.assertRaises(AuthError):
                self.accounts.login("admin", "wrong password!!")
        helper = self.accounts.create("admin2", "Quản trị 2", "admin", "second admin pass")
        self.accounts.update(self.admin["id"], actor_id=helper["id"], password="brand new password")
        self.assertEqual(self.accounts.login("admin", "brand new password")[1]["username"], "admin")

    def test_chat_sessions_belong_to_their_account(self):
        reader = self.accounts.create("hr.lan", "Nhân sự", "reader", "reader password 1")
        self.accounts.own_chat("c1", reader["id"])
        self.accounts.own_chat("c1", self.admin["id"])  # The first owner keeps it.
        self.assertEqual(self.accounts.chats_of(reader["id"]), {"c1"})
        self.assertEqual(self.accounts.chats_of(self.admin["id"]), set())

    def test_review_store_still_opens_the_shared_file(self):
        self.assertEqual(ReviewStore(self.path).knowledge_bases(), [])
        self.assertEqual(AccountStore(self.path).count(), 1)


if __name__ == "__main__":
    unittest.main()
