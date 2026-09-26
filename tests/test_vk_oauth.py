import os
import tempfile
import unittest
from unittest.mock import patch

from model import vk_oauth
from model.vk_oauth import (
    VkOAuthError,
    decode_oauth_state,
    encode_oauth_state,
    exchange_vk_code,
    kate_authorize_url,
    own_app_auth_ready,
    parse_vk_callback,
    vk_authorize_url,
    vk_oauth_ready,
)


class VkOAuthTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "VK_APP_ID": "12345",
                "VK_CLIENT_SECRET": "secret-app",
                "VK_PUBLIC_BASE": "https://bot-1778084510-9776-anastasia-kot-ramble.bothost.tech",
                "VK_OAUTH_STATE_SECRET": "state-secret",
                "SESSION_DIR": self.temp_dir.name,
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_oauth_is_ready_with_app_credentials(self):
        self.assertTrue(vk_oauth_ready())
        self.assertTrue(own_app_auth_ready())

    def test_kate_authorize_url_uses_implicit_flow(self):
        url = kate_authorize_url()
        self.assertTrue(url.startswith("https://oauth.vk.com/authorize?"))
        self.assertIn("client_id=2685278", url)
        self.assertIn("response_type=token", url)
        self.assertIn("blank.html", url)
        self.assertIn("stories", url)
        self.assertIn("offline", url)

    def test_own_app_not_ready_without_public_base(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in ("VK_PUBLIC_BASE", "DOMAIN", "VK_REDIRECT_URI"):
                os.environ.pop(key, None)
            self.assertFalse(own_app_auth_ready())
            self.assertTrue(vk_oauth_ready())  # Kate always available

    def test_authorize_url_uses_vk_id_and_pkce(self):
        url = vk_authorize_url(42)
        self.assertTrue(url.startswith("https://id.vk.ru/authorize?"))
        self.assertIn("client_id=12345", url)
        self.assertIn("response_type=code", url)
        self.assertIn("code_challenge=", url)
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("bothost.tech", url)
        self.assertIn("vk%2Fcallback", url)
        self.assertNotIn("oauth.vk.com", url)
        self.assertNotIn("stories", url)

    def test_public_base_prefers_bothost_domain(self):
        from config import vk_public_base, vk_redirect_uri

        with patch.dict(
            os.environ,
            {
                "DOMAIN": "bot-live-user.bothost.tech",
            },
            clear=False,
        ):
            os.environ.pop("VK_PUBLIC_BASE", None)
            os.environ.pop("VK_REDIRECT_URI", None)
            self.assertEqual(vk_public_base(), "https://bot-live-user.bothost.tech")
            self.assertEqual(
                vk_redirect_uri(),
                "https://bot-live-user.bothost.tech/vk/callback",
            )

    def test_state_roundtrip(self):
        now = 1_700_000_000
        state = encode_oauth_state(42, now=now)
        self.assertNotIn(".", state)
        self.assertEqual(decode_oauth_state(state, now=now + 10), 42)

    def test_expired_state_rejected(self):
        now = 1_700_000_000
        state = encode_oauth_state(42, now=now)
        with self.assertRaises(VkOAuthError):
            decode_oauth_state(state, now=now + 601)

    def test_tampered_state_rejected(self):
        now = 1_700_000_000
        state = encode_oauth_state(42, now=now)
        with self.assertRaises(VkOAuthError):
            decode_oauth_state(state + "00", now=now)

    def test_exchange_code_posts_service_token(self):
        url = vk_authorize_url(42)
        state = url.split("state=")[1].split("&")[0]
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"access_token": "user-token", "user_id": 7}

        def fake_post(post_url, data=None, timeout=None):
            captured["url"] = post_url
            captured["data"] = data
            return FakeResponse()

        with patch.object(vk_oauth.requests, "post", side_effect=fake_post):
            result = exchange_vk_code("auth-code", device_id="dev-1", state=state)
        self.assertEqual(result["access_token"], "user-token")
        self.assertEqual(captured["url"], "https://id.vk.ru/oauth2/auth")
        self.assertEqual(captured["data"]["service_token"], "secret-app")
        self.assertEqual(captured["data"]["code"], "auth-code")
        self.assertEqual(captured["data"]["device_id"], "dev-1")
        self.assertTrue(captured["data"]["code_verifier"])

    def test_parse_payload_callback(self):
        parsed = parse_vk_callback(
            {
                "payload": [
                    '{"code":"abc","state":"st","type":"code_v2","device_id":"dev"}'
                ]
            }
        )
        self.assertEqual(parsed["code"], "abc")
        self.assertEqual(parsed["device_id"], "dev")


if __name__ == "__main__":
    unittest.main()
