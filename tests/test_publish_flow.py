import unittest
from types import SimpleNamespace
from unittest.mock import patch

from controller import callbacks
from model.max_stories import MaxStoriesError
from model.pending import clear_pending, get_pending, set_pending
from view import (
    CB_PUBLISH_ALL,
    CB_PUBLISH_BOTH,
    CB_PUBLISH_INSTAGRAM,
    CB_PUBLISH_MAX,
    CB_PUBLISH_TELEGRAM,
    CB_PUBLISH_VK,
    CB_PUBLISH_WHATSAPP,
    preview_keyboard,
    publish_keyboard,
)


class FakeBot:
    def __init__(self):
        self.callback_handlers = {}
        self.post_story_calls = []
        self.sent_messages = []
        self.sent_photos = []

    def callback_query_handler(self, **_filters):
        def decorator(handler):
            self.callback_handlers[handler.__name__] = handler
            return handler

        return decorator

    def answer_callback_query(self, *_args, **_kwargs):
        return None

    def get_file(self, _file_id):
        return SimpleNamespace(file_path="photo.jpg")

    def download_file(self, _file_path):
        return b"image"

    def post_story(self, **kwargs):
        self.post_story_calls.append(kwargs)

    def edit_message_text(self, text, **_kwargs):
        self.sent_messages.append(text)

    def edit_message_caption(self, caption, **_kwargs):
        self.sent_messages.append(caption)

    def edit_message_reply_markup(self, **_kwargs):
        return None

    def send_message(self, _chat_id, text, **_kwargs):
        self.sent_messages.append(text)

    def send_photo(self, _chat_id, photo, **kwargs):
        self.sent_photos.append((photo, kwargs.get("caption")))


def make_call(data):
    return SimpleNamespace(
        id="callback",
        data=data,
        from_user=SimpleNamespace(id=777),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=777),
            message_id=10,
            content_type="text",
        ),
    )


class PublishFlowTest(unittest.TestCase):
    telegram_id = 777

    def setUp(self):
        self.bot = FakeBot()
        callbacks.register_callback_handlers(self.bot)
        self.handle_publish = self.bot.callback_handlers["handle_publish"]

    def tearDown(self):
        clear_pending(self.telegram_id)

    def test_keyboards_offer_each_publish_target(self):
        callbacks_data = {
            button.callback_data
            for keyboard in (publish_keyboard(), preview_keyboard())
            for row in keyboard.keyboard
            for button in row
        }
        self.assertTrue(
            {
                CB_PUBLISH_TELEGRAM,
                CB_PUBLISH_MAX,
                CB_PUBLISH_WHATSAPP,
                CB_PUBLISH_VK,
                CB_PUBLISH_INSTAGRAM,
                CB_PUBLISH_ALL,
            }.issubset(callbacks_data)
        )

    def test_both_retries_only_failed_max_target(self):
        set_pending(self.telegram_id, "photo")
        call = make_call(CB_PUBLISH_BOTH)

        with (
            patch.object(callbacks, "business_connection_id", return_value="connection"),
            patch.object(
                callbacks,
                "publish_max_photo",
                side_effect=[MaxStoriesError("MAX unavailable"), {"storyId": 42}],
            ) as publish_max,
        ):
            self.handle_publish(call)
            pending = get_pending(self.telegram_id)
            self.assertEqual(pending.published_targets, frozenset({"telegram"}))

            self.handle_publish(call)

        self.assertEqual(len(self.bot.post_story_calls), 1)
        self.assertEqual(publish_max.call_count, 2)
        self.assertIsNone(get_pending(self.telegram_id))
        self.assertEqual(self.bot.sent_photos[-1], ("photo", None))


if __name__ == "__main__":
    unittest.main()
