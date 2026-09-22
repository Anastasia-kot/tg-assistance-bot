from __future__ import annotations

import html
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from model.stories import user_lock
from model.vk_oauth import VkOAuthError, decode_oauth_state, exchange_vk_code
from model.vk_stories import VkFloodError, VkStoriesError, save_vk_token, vk_account_label
from view.messages import MSG_VK_AUTH_DONE, MSG_VK_OAUTH_CALLBACK_FAIL, MSG_VK_OAUTH_CALLBACK_OK

logger = logging.getLogger("http_app")

_bot: Any = None


def set_bot(bot: Any) -> None:
    global _bot
    _bot = bot


def start_http_server() -> ThreadingHTTPServer:
    host = "0.0.0.0"
    port = int(os.getenv("PORT") or "8080")
    server = ThreadingHTTPServer((host, port), VkHttpHandler)
    thread = threading.Thread(target=server.serve_forever, name="http", daemon=True)
    thread.start()
    logger.info("HTTP server listening on %s:%s", host, port)
    return server


class VkHttpHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        logger.info("http %s", format % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/health"):
            self._send(200, "text/plain; charset=utf-8", "ok")
            return
        if parsed.path == "/vk/callback":
            self._handle_vk_callback(parse_qs(parsed.query))
            return
        self._send(404, "text/plain; charset=utf-8", "not found")

    def _handle_vk_callback(self, query: dict[str, list[str]]) -> None:
        error = _first(query, "error")
        if error:
            description = _first(query, "error_description") or error
            self._fail(f"VK отклонил вход: {description}")
            return
        code = _first(query, "code")
        state = _first(query, "state")
        if not code or not state:
            self._fail("Нет code или state. Нажмите /vk_login в боте ещё раз.")
            return
        telegram_id = None
        try:
            telegram_id = decode_oauth_state(state)
            token = exchange_vk_code(code)["access_token"]
            with user_lock(telegram_id):
                save_vk_token(telegram_id, token)
        except VkFloodError as flood_error:
            if telegram_id is not None:
                self._notify(
                    telegram_id,
                    MSG_VK_AUTH_DONE.format(name="VK") + "\n\n" + flood_error.user_message,
                )
            self._ok()
            return
        except (VkOAuthError, VkStoriesError) as auth_error:
            logger.warning("VK OAuth callback failed: %s", auth_error.user_message)
            self._fail(auth_error.user_message)
            return
        except Exception:
            logger.exception("VK OAuth callback crashed")
            self._fail("Не удалось завершить вход во VK. Нажмите /vk_login ещё раз.")
            return
        name = vk_account_label(telegram_id) or "VK"
        self._notify(telegram_id, MSG_VK_AUTH_DONE.format(name=name))
        self._ok()

    def _ok(self) -> None:
        self._send_html(200, MSG_VK_OAUTH_CALLBACK_OK)

    def _fail(self, message: str) -> None:
        self._send_html(400, MSG_VK_OAUTH_CALLBACK_FAIL.format(error=html.escape(message)))

    def _notify(self, telegram_id: int, text: str) -> None:
        if _bot is None:
            logger.error("bot is not attached, cannot notify telegram_id=%s", telegram_id)
            return
        try:
            _bot.send_message(telegram_id, text)
        except Exception:
            logger.exception("failed to notify telegram_id=%s after VK OAuth", telegram_id)

    def _send_html(self, status: int, body: str) -> None:
        self._send(status, "text/html; charset=utf-8", body)

    def _send(self, status: int, content_type: str, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return (values[0] if values else "").strip()
