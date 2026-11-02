import json
import logging
from typing import Dict, Tuple

import requests

from heimdallr.channel.base import Channel, Message
from heimdallr.config.config import get_config_str
from heimdallr.config.definition import (
    SUFFIX_WEBHOOK_BODY,
    SUFFIX_WEBHOOK_CONTENT_TYPE,
    SUFFIX_WEBHOOK_HEADERS,
    SUFFIX_WEBHOOK_METHOD,
    SUFFIX_WEBHOOK_URL,
)
from heimdallr.exception import ParamException

logger = logging.getLogger(__name__)


class WebhookMessage(Message):
    def __init__(self, title: str, body: str, msg_type: str = "text", jump_url: str = "", **kwargs) -> None:
        super().__init__(title, body)
        self.msg_type = msg_type
        self.jump_url = jump_url

    def render_message(self) -> str:
        return json.dumps({"title": self.title, "body": self.body})


class Webhook(Channel):
    def __init__(self, name: str, type: str) -> None:
        super().__init__(name, type)
        self.url: str = ""
        self.method: str = "POST"
        self.headers: Dict[str, str] = {}
        self.body_template: str = ""
        self.content_type: str = "application/json"
        self._build_channel()

    def _build_channel(self) -> None:
        self.url = get_config_str(self.get_name(), SUFFIX_WEBHOOK_URL, "")
        if self.url == "":
            raise ParamException("Webhook url cannot be empty.")
        self.method = get_config_str(self.get_name(), SUFFIX_WEBHOOK_METHOD, "POST").upper()
        if self.method not in ("POST", "PUT"):
            raise ParamException("Webhook method must be POST or PUT.")
        self.content_type = get_config_str(self.get_name(), SUFFIX_WEBHOOK_CONTENT_TYPE, "application/json")
        raw_headers = get_config_str(self.get_name(), SUFFIX_WEBHOOK_HEADERS, "")
        if raw_headers != "":
            try:
                self.headers = json.loads(raw_headers)
            except json.JSONDecodeError as e:
                raise ParamException(f"Webhook headers is not valid json: {e}")
            if not isinstance(self.headers, dict):
                raise ParamException("Webhook headers must be a json object.")
        self.body_template = get_config_str(self.get_name(), SUFFIX_WEBHOOK_BODY, "")

    def _escape(self, value: str) -> str:
        # JSON 模板里直接放裸值会破坏结构，按 content-type 决定是否转义
        if "json" in self.content_type:
            return json.dumps(value, ensure_ascii=False)[1:-1]
        return value

    def _render_body(self, message: WebhookMessage) -> str:
        if self.body_template == "":
            return message.render_message()
        body = self.body_template
        body = body.replace("{{title}}", self._escape(message.title))
        body = body.replace("{{body}}", self._escape(message.body))
        body = body.replace("{{msg_type}}", self._escape(message.msg_type))
        body = body.replace("{{jump_url}}", self._escape(message.jump_url))
        return body

    def send(self, message: Message) -> Tuple[bool, str]:
        if not isinstance(message, WebhookMessage):
            raise ParamException("Webhook only supports WebhookMessage.")
        headers = {"Content-Type": self.content_type}
        headers.update(self.headers)
        body = self._render_body(message)
        try:
            rs = requests.request(self.method, self.url, data=body.encode("utf-8"), headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook request failed: {e}")
            return False, str(e)
        if rs.status_code < 200 or rs.status_code >= 300:
            logger.error(f"Webhook send failed: {rs.status_code} {rs.text}")
            return False, f"HTTP {rs.status_code}: {rs.text}"
        return True, "success"
