import os
import tempfile
import unittest
from unittest.mock import patch

from model import vk_stories
from model.vk_stories import VkStoriesError


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
        self.assertTrue(vk_stories.has_vk_session(1))
        self.assertEqual(vk_stories.vk_account_label(1), "Ivan Petrov (@ivan)")

        result = vk_stories.publish_vk_photo(1, b"not-a-real-image", None)
        self.assertEqual(result, {"story_id": 99})
        upload = next(call for call in self.calls if call["url"] == "https://upload.vk/story")
        self.assertEqual(upload["files"]["file"][0], "story.jpg")
        save = next(call for call in self.calls if str(call["url"]).endswith("stories.save"))
        self.assertEqual(save["data"]["upload_results"], "uploaded-token")
        upload_server = next(
            call
            for call in self.calls
            if str(call["url"]).endswith("stories.getPhotoUploadServer")
        )
        self.assertEqual(upload_server["data"]["add_to_news"], 1)

    def test_expired_token_is_mapped(self):
        def fake_post(url, data=None, files=None, timeout=None):
            return FakeResponse(
                {"error": {"error_code": 5, "error_msg": "User authorization failed"}}
            )

        with patch.object(vk_stories.requests, "post", side_effect=fake_post):
            with self.assertRaises(VkStoriesError) as error:
                vk_stories.save_vk_token(2, "dead-token-value-123456")
        self.assertIn("/vk_login", error.exception.user_message)

    def test_oauth_url_contains_stories_scope(self):
        url = vk_stories.vk_oauth_url()
        self.assertIn("client_id=", url)
        self.assertIn("stories", url)
        self.assertIn("response_type=token", url)


if __name__ == "__main__":
    unittest.main()
