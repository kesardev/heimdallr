import json
import logging
from typing import Tuple

import requests

from heimdallr.channel.base import Channel, Message
from heimdallr.config.config import get_config_str
from heimdallr.config.definition import SUFFIX_SYNOLOGY_URL
from heimdallr.exception import ParamException

logger = logging.getLogger(__name__)


class SynologyChatMessage(Message):
    def __init__(self, title: str, body: str, **kwargs) -> None:
        super().__init__(title, body)

    def render_message(self) -> str:
        return json.dumps({"text": f"{self.title}\n{self.body}"})


class SynologyChat(Channel):
    def __init__(self, name: str, type: str) -> None:
        super().__init__(name, type)
        self.url: str = ""
        self._build_channel()

    def _build_channel(self) -> None:
        self.url = get_config_str(self.get_name(), SUFFIX_SYNOLOGY_URL, "")
        if self.url == "":
            raise ParamException("Synology Chat webhook url cannot be empty.")

    def send(self, message: Message) -> Tuple[bool, str]:
        if not isinstance(message, SynologyChatMessage):
            raise ParamException("Synology Chat only supports SynologyChatMessage.")
        rs = requests.post(self.url, data={"payload": message.render_message()}, timeout=30)
        if rs.status_code != 200:
            logger.error(f"Synology Chat send failed: {rs.text}")
            return False, rs.text
        try:
            result = rs.json()
        except ValueError:
            return True, "success"
        if result.get("success") is False:
            logger.error(f"Synology Chat error: {rs.text}")
            return False, rs.text
        return True, "success"
