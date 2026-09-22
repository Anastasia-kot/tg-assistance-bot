import os
import tempfile
import unittest
from unittest.mock import patch

from model import vk_stories
from model.vk_stories import VkFloodError, VkStoriesError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise vk_stories.requests.HTTPError(f"status {self.status_code}")


class VkStoriesTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SESSION_DIR": self.temp_dir.name})
        self.env.start()
        self.calls = []

        def fake_post(url, data=None, files=None, timeout=None):
            self.calls.append({"url": url, "data": data, "files": files})
            if url.endswith("users.get"):
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
            if url.endswith("account.getAppPermissions"):
                return FakeResponse(
                    {"response": vk_stories.VK_STORIES_PERMISSION | 65536}
                )
            if url.endswith("stories.getPhotoUploadServer"):
                return FakeResponse({"response": {"upload_url": "https://upload.vk/story"}})
            if url == "https://upload.vk/story":
                return FakeResponse({"upload_result": "uploaded-token"})
            if url.endswith("stories.save"):
                return FakeResponse({"response": {"story_id": 99}})
            return FakeResponse({"response": {}})

        self.post = patch.object(vk_stories.requests, "post", side_effect=fake_post)
        self.post.start()

    def tearDown(self):
        self.post.stop()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_saves_token_and_publishes_photo_story(self):
        profile = vk_stories.save_vk_token(1, "vk-access-token-value-12345")
        self.assertEqual(profile["first_name"], "Ivan")
        result = vk_stories.publish_vk_photo(1, b"not-a-real-image", None)
        self.assertEqual(result, {"story_id": 99})
        permissions = next(
            call
            for call in self.calls
            if str(call["url"]).endswith("account.getAppPermissions")
        )
        self.assertTrue(permissions)

    def test_flood_on_users_get_keeps_token_and_explains_limit(self):
        def fake_post(url, data=None, files=None, timeout=None):
            return FakeResponse(
                {"error": {"error_code": 9, "error_msg": "Flood control"}}
            )

        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            with self.assertRaises(VkFloodError) as error:
                vk_stories.save_vk_token(2, "vk-access-token-value-12345")
        self.assertTrue(vk_stories.has_vk_session(2))
        text = error.exception.user_message
        self.assertIn("лимит запросов", text)
        self.assertIn("не про права на сторис", text)
        self.assertIn("Flood control", text)
        self.assertIn("10–15", text)

    def test_kate_mask_without_stories_bit_still_publishes(self):
        vk_stories.save_vk_token(3, "vk-access-token-value-12345")
        mask = 65600
        self.assertNotIn("stories", vk_stories.decode_vk_permissions(mask))
        self.assertIn("offline", vk_stories.decode_vk_permissions(mask))

        def fake_post(url, data=None, files=None, timeout=None):
            if str(url).endswith("account.getAppPermissions"):
                return FakeResponse({"response": mask})
            if str(url).endswith("stories.getPhotoUploadServer"):
                return FakeResponse({"response": {"upload_url": "https://upload.vk/story"}})
            if url == "https://upload.vk/story":
                return FakeResponse({"upload_result": "uploaded-token"})
            if str(url).endswith("stories.save"):
                return FakeResponse({"response": {"story_id": 99}})
            return FakeResponse({"response": {}})

        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            result = vk_stories.publish_vk_photo(3, b"image", None)
        self.assertEqual(result, {"story_id": 99})

    def test_check_vk_token_reports_upload_url(self):
        vk_stories.save_vk_token(4, "vk-access-token-value-12345")
        status = vk_stories.check_vk_token(4)
        self.assertTrue(status["ok"])
        self.assertTrue(status["has_upload_url"])

    def test_flood_error_is_retryable(self):
        error = VkFloodError("flood")
        self.assertTrue(error.retryable)

    def test_decode_permissions_includes_stories(self):
        scopes = vk_stories.decode_vk_permissions(
            vk_stories.VK_STORIES_PERMISSION | 65536
        )
        self.assertIn("stories", scopes)
        self.assertIn("offline", scopes)


if __name__ == "__main__":
    unittest.main()
