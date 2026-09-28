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


def _stories_ok(url, data=None, files=None, timeout=None):
    if str(url).endswith("stories.getPhotoUploadServer"):
        return FakeResponse({"response": {"upload_url": "https://upload.vk/story"}})
    if str(url).endswith("account.getAppPermissions"):
        return FakeResponse({"response": vk_stories.VK_STORIES_PERMISSION | 65536})
    if str(url).endswith("users.get"):
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
    return FakeResponse({"response": {}})


def _stories_flood(url, data=None, files=None, timeout=None):
    return FakeResponse({"error": {"error_code": 9, "error_msg": "Flood control"}})


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

    def test_run_ok_probes_stories_not_users_get(self):
        calls = []

        def fake_post(url, data=None, files=None, timeout=None):
            calls.append(str(url))
            return _stories_ok(url, data, files, timeout)

        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            vk_stories.save_vk_token(
                42,
                "vk-access-token-value-12345",
                auth_method="kate",
            )
            self._arm_job(attempt=1)
            vk_flood_check._run_vk_flood_check(self.bot, 42, 99, attempt=1)
        self.assertTrue(any(u.endswith("stories.getPhotoUploadServer") for u in calls))
        self.assertFalse(any(u.endswith("users.get") for u in calls))
        text = self.bot.send_message.call_args[0][1]
        self.assertIn("stories", text)
        self.assertIn("доступны", text)

    def test_run_flood_reschedules_with_plus_five(self):
        with patch.object(vk_stories.requests, "post", side_effect=_stories_flood):
            with self.assertRaises(VkFloodError):
                vk_stories.save_vk_token(
                    42,
                    "vk-access-token-value-12345",
                    auth_method="kate",
                )
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


class KateStoriesProbeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SESSION_DIR": self.temp_dir.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_kate_save_skips_users_get(self):
        calls = []

        def fake_post(url, data=None, files=None, timeout=None):
            calls.append(str(url))
            return _stories_ok(url, data, files, timeout)

        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            profile = vk_stories.save_vk_token(
                7,
                "vk-access-token-value-12345",
                auth_method="kate",
            )
        self.assertEqual(profile["first_name"], "VK")
        self.assertTrue(vk_stories.has_vk_session(7))
        self.assertTrue(any(u.endswith("stories.getPhotoUploadServer") for u in calls))
        self.assertFalse(any(u.endswith("users.get") for u in calls))

    def test_kate_flood_on_stories_keeps_token(self):
        with patch.object(vk_stories.requests, "post", side_effect=_stories_flood):
            with self.assertRaises(VkFloodError) as error:
                vk_stories.save_vk_token(
                    8,
                    "vk-access-token-value-12345",
                    auth_method="kate",
                )
        self.assertTrue(vk_stories.has_vk_session(8))
        self.assertIn("Flood control", error.exception.user_message)

    def test_stories_ready_ok(self):
        from model.session_files import write_session

        write_session(
            vk_stories.PLATFORM,
            9,
            {
                "access_token": "vk-access-token-value-12345",
                "user_id": None,
                "name": "Kate",
                "auth_method": "kate",
            },
        )
        with patch.object(vk_stories.requests, "post", side_effect=_stories_ok):
            result = vk_stories.check_vk_stories_ready(9)
        self.assertTrue(result["ok"])
        self.assertTrue(result["has_upload_url"])
        self.assertEqual(result["name"], "Kate")

    def test_stories_ready_marks_flood_retryable(self):
        from model.session_files import write_session

        write_session(
            vk_stories.PLATFORM,
            10,
            {
                "access_token": "vk-access-token-value-12345",
                "user_id": None,
                "name": "VK",
            },
        )
        with patch.object(vk_stories.requests, "post", side_effect=_stories_flood):
            result = vk_stories.check_vk_stories_ready(10)
        self.assertFalse(result["ok"])
        self.assertTrue(result["retryable"])
        self.assertIn("Flood control", result["error"])


if __name__ == "__main__":
    unittest.main()
