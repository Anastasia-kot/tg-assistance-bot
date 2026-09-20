import unittest

from model.max_auth import (
    MAX_AUTH_CODE,
    MAX_AUTH_METHOD,
    MAX_AUTH_PASSWORD,
    MAX_AUTH_PHONE,
    MAX_AUTH_QR,
    begin_max_auth,
    clear_max_auth,
    get_max_auth,
    select_max_qr_auth,
    select_max_sms_auth,
    set_max_code_requested,
    set_max_password_requested,
)
from model.pending import (
    clear_pending,
    get_pending,
    mark_target_published,
    remove_caption,
    set_caption,
    set_pending,
    wait_for_caption,
)


class MaxAuthStateTest(unittest.TestCase):
    telegram_id = 1001

    def tearDown(self):
        clear_max_auth(self.telegram_id)

    def test_auth_flow_does_not_retain_code_or_password(self):
        self.assertEqual(begin_max_auth(self.telegram_id).step, MAX_AUTH_METHOD)
        self.assertEqual(select_max_sms_auth(self.telegram_id).step, MAX_AUTH_PHONE)

        state = set_max_code_requested(self.telegram_id, "+79001234567", "token")
        self.assertEqual(state.step, MAX_AUTH_CODE)
        self.assertEqual(state.auth_token, "token")

        state = set_max_password_requested(self.telegram_id, "track")
        self.assertEqual(state.step, MAX_AUTH_PASSWORD)
        self.assertIsNone(state.auth_token)
        self.assertEqual(get_max_auth(self.telegram_id).track_id, "track")

    def test_qr_auth_can_be_selected_after_start(self):
        begin_max_auth(self.telegram_id)

        self.assertEqual(select_max_qr_auth(self.telegram_id).step, MAX_AUTH_QR)


class PendingStoryStateTest(unittest.TestCase):
    telegram_id = 1002

    def tearDown(self):
        clear_pending(self.telegram_id)

    def test_caption_and_partial_targets_are_preserved(self):
        set_pending(self.telegram_id, "photo")
        self.assertTrue(wait_for_caption(self.telegram_id).is_waiting_for_caption)
        self.assertEqual(set_caption(self.telegram_id, "text").caption, "text")

        story = mark_target_published(self.telegram_id, "telegram")
        self.assertEqual(story.published_targets, frozenset({"telegram"}))
        self.assertEqual(get_pending(self.telegram_id).caption, "text")

        story = remove_caption(self.telegram_id)
        self.assertIsNone(story.caption)
        self.assertEqual(story.published_targets, frozenset({"telegram"}))


if __name__ == "__main__":
    unittest.main()
