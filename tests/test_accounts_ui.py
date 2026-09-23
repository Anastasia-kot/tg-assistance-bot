import os
import tempfile
import unittest
from unittest.mock import patch

from model.pending import set_pending, toggle_pending_target
from model.platforms import PLATFORM_TELEGRAM, PLATFORM_VK, PlatformStatus
from view.keyboards import (
    EMOJI_CHECKED,
    EMOJI_LOCKED,
    EMOJI_UNCHECKED,
    accounts_keyboard,
    publish_keyboard,
)
from view.messages import accounts_message


class AccountsUiTest(unittest.TestCase):
    def test_accounts_message_lists_statuses(self):
        text = accounts_message(
            "intro",
            [
                PlatformStatus("telegram", "Telegram", True, "бизнес"),
                PlatformStatus("vk", "VK", False, "не подключено"),
            ],
        )
        self.assertIn("✅ Telegram: бизнес", text)
        self.assertIn("❌ VK: не подключено", text)

    def test_accounts_keyboard_has_login_and_logout(self):
        markup = accounts_keyboard(
            [
                PlatformStatus("telegram", "Telegram", True, "бизнес"),
                PlatformStatus(
                    "vk",
                    "VK",
                    False,
                    "не подключено",
                    login_url="https://id.vk.ru/authorize",
                ),
            ]
        )
        labels = [button.text for row in markup.keyboard for button in row]
        self.assertEqual(labels.count("Войти"), 2)
        self.assertEqual(labels.count("Выйти"), 2)
        vk_login = markup.keyboard[1][0]
        self.assertEqual(vk_login.url, "https://id.vk.ru/authorize")

    def test_publish_checklist_locks_unauthorized(self):
        story = set_pending(1, "file", selected=frozenset({PLATFORM_TELEGRAM}))
        markup = publish_keyboard(story, frozenset({PLATFORM_TELEGRAM}))
        labels = [row[0].text for row in markup.keyboard[:2]]
        self.assertEqual(labels[0], f"{EMOJI_CHECKED} Telegram")
        self.assertEqual(labels[1], f"{EMOJI_LOCKED} VK")

    def test_toggle_unchecks_authorized_platform(self):
        self.temp = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, {"SESSION_DIR": self.temp.name}):
            set_pending(
                9,
                "file",
                selected=frozenset({PLATFORM_TELEGRAM, PLATFORM_VK}),
            )
            story = toggle_pending_target(
                9,
                PLATFORM_VK,
                allowed=frozenset({PLATFORM_TELEGRAM, PLATFORM_VK}),
            )
            self.assertIsNotNone(story)
            self.assertEqual(story.selected, frozenset({PLATFORM_TELEGRAM}))
            markup = publish_keyboard(
                story,
                frozenset({PLATFORM_TELEGRAM, PLATFORM_VK}),
            )
            labels = [row[0].text for row in markup.keyboard[:2]]
            self.assertEqual(labels[0], f"{EMOJI_CHECKED} Telegram")
            self.assertEqual(labels[1], f"{EMOJI_UNCHECKED} VK")
        self.temp.cleanup()

    def test_toggle_ignores_unauthorized_platform(self):
        set_pending(3, "file", selected=frozenset({PLATFORM_TELEGRAM}))
        story = toggle_pending_target(
            3,
            PLATFORM_VK,
            allowed=frozenset({PLATFORM_TELEGRAM}),
        )
        self.assertEqual(story.selected, frozenset({PLATFORM_TELEGRAM}))


if __name__ == "__main__":
    unittest.main()
