import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from model import max_stories
from maxion.raw.errors import TwoFactorRequired
from maxion.raw.session import Session


class FakeSession:
    def __init__(self):
        self.saved = False

    def save(self):
        self.saved = True


class FakeProfile:
    name = "Test MAX"


class FakeMaxClient:
    instances = []
    require_password = False

    def __init__(self, path, **_kwargs):
        self.path = path
        self.session = FakeSession()
        self.is_connected = True
        self.story_payload = None
        self.__class__.instances.append(self)

    @classmethod
    def mobile(cls, path, **kwargs):
        instance = cls(path, **kwargs)
        instance.is_mobile = True
        return instance

    @classmethod
    def web(cls, path, **_kwargs):
        instance = cls(path)
        instance.is_web = True
        return instance

    async def connect(self):
        return None

    async def disconnect(self):
        return None

    async def request_code(self, phone, **kwargs):
        self.phone = phone
        self.request_kwargs = kwargs
        return {"token": "auth-token"}

    async def sign_in(self, code, auth_token):
        self.code = code
        self.auth_token = auth_token
        if self.require_password:
            raise TwoFactorRequired({"trackId": "2fa-track"})
        return FakeProfile()

    async def login_check_password(self, password, track_id):
        self.password = password
        self.track_id = track_id
        return FakeProfile()

    async def login_by_token(self):
        return {"profile": {"name": "Test MAX"}}

    async def upload_photo(self, image_bytes, filename):
        self.upload = (image_bytes, filename)
        return {"_type": "PHOTO", "photoToken": "photo-token"}

    async def request_video_upload(self, count=1, **_kwargs):
        return {
            "info": [
                {"videoId": 7, "url": "http://example", "token": "slot-token"}
            ]
        }

    async def _post_upload(self, url, file, filename, mimetype):
        self.upload = (file, filename)
        return None

    def _attach_waiter(self, key, value):
        future = asyncio.get_running_loop().create_future()
        future.set_result({"videoId": value, "token": "video-token"})
        return future

    async def _await_attach(self, future, timeout):
        return await future

    async def send_story(self, **payload):
        self.story_payload = payload
        return {"storyId": 42}

    async def invoke(self, opcode, payload=None, **_kwargs):
        self.story_opcode = opcode
        self.story_payload = payload
        return {"storyId": 42}

    async def logout(self):
        return None


class MaxStoriesServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_patch = patch.dict(
            os.environ,
            {"MAX_SESSION_DIR": self.temp_dir.name},
        )
        self.client_patch = patch.object(max_stories, "MaxClient", FakeMaxClient)
        self.env_patch.start()
        self.client_patch.start()
        self.convert_patch = patch.object(
            max_stories,
            "_image_to_story_mp4",
            return_value=b"mp4",
        )
        self.convert_patch.start()
        FakeMaxClient.instances.clear()
        FakeMaxClient.require_password = False

    def tearDown(self):
        self.convert_patch.stop()
        self.client_patch.stop()
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def _write_session(self, telegram_id):
        path = max_stories.max_session_path(telegram_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"token": "login-token", "device_id": "device"}),
            encoding="utf-8",
        )

    def test_requests_code_and_saves_device_session(self):
        token = max_stories.request_max_login_code(1, "+79001234567")
        client = FakeMaxClient.instances[-1]
        self.assertEqual(token, "auth-token")
        self.assertTrue(client.session.saved)
        self.assertIsNone(client.request_kwargs["mode"])
        self.assertEqual(
            client.request_kwargs["auth_type"],
            max_stories.AuthType.START_AUTH,
        )

    def test_resends_code_and_requests_call(self):
        max_stories.request_max_login_code(1, "+79001234567", resend=True)
        resend_client = FakeMaxClient.instances[-1]
        self.assertIsNone(resend_client.request_kwargs["mode"])
        self.assertEqual(
            resend_client.request_kwargs["auth_type"],
            max_stories.AuthType.RESEND_CODE,
        )

        max_stories.request_max_login_code(1, "+79001234567", call=True)
        call_client = FakeMaxClient.instances[-1]
        self.assertIsNone(call_client.request_kwargs["mode"])
        self.assertEqual(
            call_client.request_kwargs["auth_type"],
            max_stories.AuthType.CALL_RESET,
        )

    def test_publishes_uploaded_photo_without_caption(self):
        self._write_session(2)
        result = max_stories.publish_max_photo(2, b"image", None)
        client = FakeMaxClient.instances[-1]

        self.assertEqual(result, {"storyId": 42})
        self.assertEqual(client.upload, (b"mp4", "story.mp4"))
        stories = client.story_payload["stories"]
        self.assertEqual(len(stories), 1)
        self.assertEqual(
            stories[0]["media"],
            {"_type": "VIDEO", "videoId": 7, "token": "video-token"},
        )
        self.assertIn("cid", stories[0])
        self.assertEqual(stories[0]["expiration"], 86_400_000)
        self.assertNotIn("expiration", client.story_payload)

    def test_qr_session_cannot_publish_stories(self):
        path = max_stories.max_session_path(6)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "token": "login-token",
                    "device_id": "device",
                    "extra": {"auth_method": "qr", "device_type": "ANDROID"},
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaises(max_stories.MaxWebSessionUnsupported):
            max_stories.publish_max_photo(6, b"image", None)

    def test_sms_session_publishes_through_mobile_client(self):
        path = max_stories.max_session_path(7)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "token": "login-token",
                    "device_id": "device",
                    "extra": {"auth_method": "sms", "device_type": "ANDROID"},
                }
            ),
            encoding="utf-8",
        )

        max_stories.publish_max_photo(7, b"image", None)

        self.assertTrue(FakeMaxClient.instances[-1].is_mobile)

    def test_exposes_and_confirms_2fa_step(self):
        FakeMaxClient.require_password = True
        with self.assertRaises(max_stories.MaxPasswordRequired) as context:
            max_stories.confirm_max_login_code(5, "123456", "auth-token")
        self.assertEqual(context.exception.track_id, "2fa-track")

        name = max_stories.confirm_max_password(5, "secret", "2fa-track")
        self.assertEqual(name, "Test MAX")

    def test_rejects_caption_until_layer_schema_is_verified(self):
        self._write_session(3)
        with self.assertRaises(max_stories.MaxCaptionUnsupported):
            max_stories.publish_max_photo(3, b"image", "caption")

    def test_session_file_is_not_a_database(self):
        path = max_stories.max_session_path(4)
        session = Session.load(path)
        session.token = "login-token"
        session.save()

        payload = json.loads(Path(path).read_text())
        self.assertEqual(payload["token"], "login-token")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
