import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from model import vk_flood_check, vk_stories
from model.vk_flood_check import (
    MAX_FLOOD_CHECKS,
    cancel_vk_flood_check,
    flood_check_delay_minutes,
    has_vk_flood_check,
    schedule_vk_flood_check,
)
from model.vk_stories import VkFloodError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise vk_stories.requests.HTTPError(f"status {self.status_code}")


class FloodCheckDelayTest(unittest.TestCase):
    def test_delay_grows_by_five_minutes(self):
        self.assertEqual(flood_check_delay_minutes(1), 5)
        self.assertEqual(flood_check_delay_minutes(2), 10)
        self.assertEqual(flood_check_delay_minutes(3), 15)
        self.assertEqual(flood_check_delay_minutes(12), 60)

    def test_delay_floors_non_positive_attempt(self):
        self.assertEqual(flood_check_delay_minutes(0), 5)
        self.assertEqual(flood_check_delay_minutes(-3), 5)


class FloodCheckScheduleTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SESSION_DIR": self.temp_dir.name})
        self.env.start()
        self.bot = MagicMock()
        cancel_vk_flood_check(42)

    def tearDown(self):
        cancel_vk_flood_check(42)
        self.env.stop()
        self.temp_dir.cleanup()

    def test_schedule_returns_delay_and_tracks_job(self):
        with patch.object(vk_flood_check.threading, "Timer") as timer_cls:
            timer = MagicMock()
            timer_cls.return_value = timer
            delay = schedule_vk_flood_check(self.bot, 42, 42, attempt=1)
        self.assertEqual(delay, 5)
        self.assertTrue(has_vk_flood_check(42))
        timer_cls.assert_called_once()
        args, kwargs = timer_cls.call_args
        self.assertEqual(args[0], 5 * 60)
        timer.start.assert_called_once()

    def test_schedule_caps_at_max_attempts(self):
        self.assertIsNone(
            schedule_vk_flood_check(self.bot, 42, 42, attempt=MAX_FLOOD_CHECKS + 1)
        )
        self.assertFalse(has_vk_flood_check(42))

    def test_cancel_stops_timer(self):
        with patch.object(vk_flood_check.threading, "Timer") as timer_cls:
            timer = MagicMock()
            timer_cls.return_value = timer
            schedule_vk_flood_check(self.bot, 42, 42, attempt=2)
            self.assertTrue(cancel_vk_flood_check(42))
        timer.cancel.assert_called_once()
        self.assertFalse(has_vk_flood_check(42))
        self.assertFalse(cancel_vk_flood_check(42))

    def _arm_job(self, attempt: int = 1) -> None:
        with patch.object(vk_flood_check.threading, "Timer") as timer_cls:
            timer_cls.return_value = MagicMock()
            schedule_vk_flood_check(self.bot, 42, 99, attempt=attempt)

    def test_run_ok_notifies_chat(self):
        def fake_post(url, data=None, files=None, timeout=None):
            return FakeResponse(
                {
                    "response": [
                        {
                            "id": 7,
                            "first_name": "Ivan",
                            "last_name": "Petrov",
                            "screen_name": "ivan",
                        }
                    ]
                }
            )

        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            vk_stories.save_vk_token(42, "vk-access-token-value-12345")
            self._arm_job(attempt=1)
            vk_flood_check._run_vk_flood_check(self.bot, 42, 99, attempt=1)
        self.bot.send_message.assert_called()
        text = self.bot.send_message.call_args[0][1]
        self.assertIn("Ivan Petrov", text)
        self.assertIn("доступен", text)

    def test_run_flood_reschedules_with_plus_five(self):
        def fake_post(url, data=None, files=None, timeout=None):
            return FakeResponse(
                {"error": {"error_code": 9, "error_msg": "Flood control"}}
            )

        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            with self.assertRaises(VkFloodError):
                vk_stories.save_vk_token(42, "vk-access-token-value-12345")
            self._arm_job(attempt=1)
            with patch.object(
                vk_flood_check,
                "schedule_vk_flood_check",
                return_value=10,
            ) as schedule:
                vk_flood_check._run_vk_flood_check(self.bot, 42, 99, attempt=1)
        schedule.assert_called_once_with(self.bot, 42, 99, 2)
        text = self.bot.send_message.call_args[0][1]
        self.assertIn("10", text)
        self.assertIn("попытка 2", text)


class RefreshVkProfileTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SESSION_DIR": self.temp_dir.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_refresh_updates_name_after_success(self):
        def fake_post(url, data=None, files=None, timeout=None):
            return FakeResponse(
                {
                    "response": [
                        {
                            "id": 7,
                            "first_name": "Ivan",
                            "last_name": "Petrov",
                            "screen_name": "ivan",
                        }
                    ]
                }
            )

        from model.session_files import write_session

        write_session(
            vk_stories.PLATFORM,
            5,
            {
                "access_token": "vk-access-token-value-12345",
                "user_id": None,
                "name": "VK",
            },
        )
        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            result = vk_stories.refresh_vk_profile(5)
        self.assertTrue(result["ok"])
        self.assertEqual(result["name"], "Ivan Petrov (@ivan)")
        self.assertEqual(vk_stories.vk_account_label(5), "Ivan Petrov (@ivan)")

    def test_refresh_marks_flood_retryable(self):
        def fake_post(url, data=None, files=None, timeout=None):
            return FakeResponse(
                {"error": {"error_code": 9, "error_msg": "Flood control"}}
            )

        from model.session_files import write_session

        write_session(
            vk_stories.PLATFORM,
            6,
            {
                "access_token": "vk-access-token-value-12345",
                "user_id": None,
                "name": "VK",
            },
        )
        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            result = vk_stories.refresh_vk_profile(6)
        self.assertFalse(result["ok"])
        self.assertTrue(result["retryable"])
        self.assertIn("Flood control", result["error"])


if __name__ == "__main__":
    unittest.main()
