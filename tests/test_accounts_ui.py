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

    def test_accounts_message_skips_empty_intro(self):
        text = accounts_message(
            "",
            [PlatformStatus("telegram", "Telegram", True, "бизнес")],
        )
        self.assertTrue(text.startswith("Соцсети\n"))
        self.assertNotIn("\n\n", text)

    def test_accounts_keyboard_status_and_single_action(self):
        markup = accounts_keyboard(
            [
                PlatformStatus("telegram", "Telegram", True, "бизнес"),
                PlatformStatus("vk", "VK", False, "не подключено"),
            ]
        )
        rows = [[button.text for button in row] for row in markup.keyboard]
        self.assertEqual(
            rows,
            [
                ["✅ Telegram", "Выйти из Telegram"],
                ["❌ VK", "Войти в VK"],
            ],
        )
        self.assertEqual(markup.keyboard[0][0].callback_data, "acc:info:telegram")
        self.assertEqual(markup.keyboard[1][1].callback_data, "acc:vk:login")
        self.assertEqual(markup.keyboard[0][1].callback_data, "acc:telegram:logout")

    def test_vk_auth_method_keyboard(self):
        from view.keyboards import (
            CB_ACC_VK_METHOD_CANCEL,
            CB_ACC_VK_METHOD_KATE,
            CB_ACC_VK_METHOD_OWN,
            vk_auth_method_keyboard,
        )

        markup = vk_auth_method_keyboard()
        labels = [button.text for row in markup.keyboard for button in row]
        self.assertEqual(labels, ["Kate Mobile", "Своё приложение", "Отмена"])
        self.assertEqual(markup.keyboard[0][0].callback_data, CB_ACC_VK_METHOD_KATE)
        self.assertEqual(markup.keyboard[0][1].callback_data, CB_ACC_VK_METHOD_OWN)
        self.assertEqual(markup.keyboard[1][0].callback_data, CB_ACC_VK_METHOD_CANCEL)

    def test_main_keyboard_has_start(self):
        from view.keyboards import BTN_START, main_keyboard

        markup = main_keyboard()
        labels = [
            button["text"] if isinstance(button, dict) else button.text
            for row in markup.keyboard
            for button in row
        ]
        self.assertEqual(labels, [BTN_START])

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

    def test_callback_filters_accept_query_object(self):
        from types import SimpleNamespace

        from view.keyboards import (
            is_account_info_callback,
            is_locked_callback,
            is_toggle_callback,
        )

        toggle = SimpleNamespace(data="story:toggle:vk")
        locked = SimpleNamespace(data="story:locked:vk")
        info = SimpleNamespace(data="acc:info:telegram")
        other = SimpleNamespace(data="vk:flood:cancel")

        self.assertTrue(is_toggle_callback(toggle))
        self.assertTrue(is_toggle_callback("story:toggle:vk"))
        self.assertFalse(is_toggle_callback(other))
        self.assertTrue(is_locked_callback(locked))
        self.assertTrue(is_account_info_callback(info))
        self.assertFalse(is_account_info_callback(toggle))


if __name__ == "__main__":
    unittest.main()
