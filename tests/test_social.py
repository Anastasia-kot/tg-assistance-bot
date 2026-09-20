import os
import tempfile
import unittest
from unittest.mock import patch

from model.accounts import accounts_status
from model.session_files import write_session
from model.social_auth import (
    IG_PASSWORD,
    IG_USERNAME,
    begin_social_auth,
    clear_social_auth,
    get_social_auth,
    set_social_auth,
)
from view import BTN_STATUS, main_keyboard


class AccountsStatusTest(unittest.TestCase):
    telegram_id = 4242

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.session_dir = self.tempdir.name
        self.env = patch.dict(os.environ, {"SESSION_DIR": self.session_dir}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tempdir.cleanup()
        clear_social_auth(self.telegram_id)

    def test_status_lists_all_platforms_as_disconnected(self):
        with patch("model.accounts.business_connection_id", return_value=None):
            text = accounts_status(self.telegram_id)
        self.assertIn("Telegram:", text)
        self.assertIn("MAX:", text)
        self.assertIn("WhatsApp:", text)
        self.assertIn("VK:", text)
        self.assertIn("Instagram:", text)
        self.assertIn("не подключён", text)

    def test_status_shows_saved_vk_name(self):
        write_session(
            "vk",
            self.telegram_id,
            {"access_token": "token", "name": "Ivan (@ivan)"},
        )
        with (
            patch("model.accounts.business_connection_id", return_value="conn"),
            patch("model.accounts.has_max_session", return_value=False),
            patch("model.accounts.has_wa_session", return_value=False),
            patch("model.accounts.has_ig_session", return_value=False),
        ):
            text = accounts_status(self.telegram_id)
        self.assertIn("VK: подключён — Ivan (@ivan)", text)
        self.assertIn("Telegram: подключён", text)

    def test_status_button_is_on_main_keyboard(self):
        labels = set()
        for row in main_keyboard().keyboard:
            for button in row:
                labels.add(getattr(button, "text", None) or button.get("text"))
        self.assertIn(BTN_STATUS, labels)

    def test_instagram_auth_keeps_username_until_password(self):
        begin_social_auth(self.telegram_id, "instagram", IG_USERNAME)
        state = set_social_auth(self.telegram_id, username="user", step=IG_PASSWORD)
        self.assertEqual(state.step, IG_PASSWORD)
        self.assertEqual(get_social_auth(self.telegram_id).username, "user")
        self.assertIsNone(get_social_auth(self.telegram_id).password)


if __name__ == "__main__":
    unittest.main()
