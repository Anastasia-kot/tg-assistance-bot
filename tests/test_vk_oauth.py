import os
import unittest
from unittest.mock import patch

from model import vk_oauth
from model.vk_oauth import (
    VkOAuthError,
    decode_oauth_state,
    encode_oauth_state,
    exchange_vk_code,
    vk_authorize_url,
    vk_oauth_ready,
)


class VkOAuthTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "VK_APP_ID": "12345",
                "VK_CLIENT_SECRET": "secret-app",
                "VK_PUBLIC_BASE": "https://bot-1778084510-9776-anastasia-kot-ramble.bothost.tech",
                "VK_OAUTH_STATE_SECRET": "state-secret",
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_oauth_is_ready_with_app_credentials(self):
        self.assertTrue(vk_oauth_ready())

    def test_authorize_url_uses_code_flow_and_own_redirect(self):
        url = vk_authorize_url(42)
        self.assertIn("client_id=12345", url)
        self.assertIn("response_type=code", url)
        self.assertIn("bothost.tech", url)
        self.assertIn("vk%2Fcallback", url)
        self.assertIn("scope=stories", url)
        self.assertNotIn("blank.html", url)

    def test_state_roundtrip(self):
        now = 1_700_000_000
        state = encode_oauth_state(42, now=now)
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

    def test_exchange_code_posts_secret_on_server(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"access_token": "user-token", "user_id": 7}

        def fake_get(url, params=None, timeout=None):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

        with patch.object(vk_oauth.requests, "get", side_effect=fake_get):
            result = exchange_vk_code("auth-code")
        self.assertEqual(result["access_token"], "user-token")
        self.assertEqual(captured["params"]["client_secret"], "secret-app")
        self.assertEqual(captured["params"]["code"], "auth-code")
        self.assertTrue(captured["params"]["redirect_uri"].endswith("/vk/callback"))


if __name__ == "__main__":
    unittest.main()
