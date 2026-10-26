import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import login


class LoginTest(unittest.TestCase):
    def test_wifi_name_must_match_exactly(self):
        self.assertTrue(login.is_srmist_wifi("    SSID : srmist\n", "nt"))
        self.assertFalse(login.is_srmist_wifi("    SSID : srmist-guest\n", "nt"))
        self.assertTrue(login.is_srmist_wifi("no:other\nyes:srmist\n", "posix"))
        self.assertFalse(login.is_srmist_wifi("yes:srmist-guest\n", "posix"))

    def test_password_can_contain_equals_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".env").write_text("SRM_USERNAME=student\nSRM_PASSWORD=a=b#c\n", encoding="utf-8")
            with patch.object(login, "ROOT", Path(directory)):
                self.assertEqual(login.credentials(), ("student", "a=b#c"))

    def test_login_after_two_failed_checks(self):
        with patch.object(login, "credentials", return_value=("student", "secret")), \
             patch.object(login, "wifi_connected", return_value=True), \
             patch.object(login, "internet_works", return_value=False), \
             patch.object(login, "login") as sign_in, \
             patch.object(login.time, "sleep", side_effect=[None, KeyboardInterrupt]):
            with self.assertRaises(KeyboardInterrupt):
                login.main()
        sign_in.assert_called_once_with("student", "secret")

    def test_portal_redirect_is_not_internet_access(self):
        class Redirect:
            status = 200
            url = login.PORTAL

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, count):
                return b"login page"

        with patch.object(login.urllib.request, "urlopen", return_value=Redirect()):
            self.assertFalse(login.internet_works())


if __name__ == "__main__":
    unittest.main()
