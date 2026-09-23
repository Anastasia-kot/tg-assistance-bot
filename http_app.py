from __future__ import annotations

import html
import logging
import os
import threading
import time
from typing import Any
from urllib.parse import parse_qs

import telebot
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from requests.exceptions import ReadTimeout
import uvicorn

from model.stories import user_lock
from model.vk_oauth import (
    VkOAuthError,
    decode_oauth_state,
    exchange_vk_code,
    parse_vk_callback,
)
from model.vk_stories import VkFloodError, VkStoriesError, save_vk_token, vk_account_label
from view.messages import MSG_VK_AUTH_DONE, MSG_VK_OAUTH_CALLBACK_FAIL, MSG_VK_OAUTH_CALLBACK_OK

logger = logging.getLogger("http_app")

_bot: Any = None
app = FastAPI()


def set_bot(bot: Any) -> None:
    global _bot
    _bot = bot


def start_polling_thread(bot: telebot.TeleBot) -> None:
    thread = threading.Thread(target=_poll_forever, args=(bot,), name="polling", daemon=True)
    thread.start()


def serve_http() -> None:
    # Bothost panel default / docs example is 3000; PORT must match the panel.
    port = int(os.getenv("PORT") or "3000")
    logger.info("HTTP server listening on 0.0.0.0:%s", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def _poll_forever(bot: telebot.TeleBot) -> None:
    while True:
        try:
            bot.polling(
                none_stop=True,
                interval=0,
                timeout=20,
                long_polling_timeout=20,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "business_connection",
                    "business_message",
                ],
            )
        except ReadTimeout:
            logger.warning("Telegram long poll timed out, retrying")
            time.sleep(2)


@app.get("/")
@app.get("/health")
def health() -> PlainTextResponse:
    return PlainTextResponse("ok")


@app.api_route("/vk/callback", methods=["GET", "POST"])
@app.api_route("/vk/callback/", methods=["GET", "POST"])
async def vk_callback(request: Request) -> HTMLResponse:
    if request.method == "POST":
        content_type = (request.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            payload = await request.json()
            query = {key: [str(value)] for key, value in dict(payload or {}).items()}
        else:
            form = await request.form()
            query = {key: [str(value)] for key, value in form.multi_items()}
        # Prefer query string when present (some VK flows mix both).
        if request.url.query:
            query = {**query, **parse_qs(request.url.query, keep_blank_values=True)}
    else:
        query = parse_qs(request.url.query, keep_blank_values=True)
    status, body = handle_vk_callback(query)
    return HTMLResponse(content=body, status_code=status)


def handle_vk_callback(query: dict[str, list[str]]) -> tuple[int, str]:
    try:
        callback = parse_vk_callback(query)
    except VkOAuthError as auth_error:
        return 400, _fail_html(auth_error.user_message)
    error = callback.get("error") or ""
    if error:
        description = callback.get("error_description") or error
        return 400, _fail_html(f"VK отклонил вход: {description}")
    code = callback.get("code") or ""
    state = callback.get("state") or ""
    device_id = callback.get("device_id") or ""
    if not code or not state:
        return 400, _fail_html("Нет code или state. Нажмите /vk_login в боте ещё раз.")
    telegram_id = None
    try:
        telegram_id = decode_oauth_state(state)
        token = exchange_vk_code(
            code,
            device_id=device_id,
            state=state,
        )["access_token"]
        with user_lock(telegram_id):
            save_vk_token(telegram_id, token)
    except VkFloodError as flood_error:
        if telegram_id is not None:
            _notify(
                telegram_id,
                MSG_VK_AUTH_DONE.format(name="VK") + "\n\n" + flood_error.user_message,
            )
        return 200, MSG_VK_OAUTH_CALLBACK_OK
    except (VkOAuthError, VkStoriesError) as auth_error:
        logger.warning("VK OAuth callback failed: %s", auth_error.user_message)
        return 400, _fail_html(auth_error.user_message)
    except Exception:
        logger.exception("VK OAuth callback crashed")
        return 400, _fail_html("Не удалось завершить вход во VK. Нажмите /vk_login ещё раз.")
    name = vk_account_label(telegram_id) or "VK"
    _notify(telegram_id, MSG_VK_AUTH_DONE.format(name=name))
    return 200, MSG_VK_OAUTH_CALLBACK_OK


def _fail_html(message: str) -> str:
    return MSG_VK_OAUTH_CALLBACK_FAIL.format(error=html.escape(message))


def _notify(telegram_id: int, text: str) -> None:
    if _bot is None:
        logger.error("bot is not attached, cannot notify telegram_id=%s", telegram_id)
        return
    try:
        _bot.send_message(telegram_id, text)
    except Exception:
        logger.exception("failed to notify telegram_id=%s after VK OAuth", telegram_id)
