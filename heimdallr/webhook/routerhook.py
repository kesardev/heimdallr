import json
from typing import Any, Dict, Tuple

from heimdallr.webhook.base import WebhookBase


class RouterHookWebhook(WebhookBase):
    """解析 RouterHook 插件推送的 JSON。"""

    def parse(self) -> Tuple[str, str, str]:
        message = self.message if isinstance(self.message, dict) else {}
        msg_type = str(message.get("msgTYPE", "unknown"))
        if msg_type in ("manuINFO", "cronINFO"):
            return self._parse_status(message)
        if msg_type == "ifUP":
            return self._parse_ifup(message)
        if msg_type == "newDHCP":
            return self._parse_dhcp(message)
        return self._parse_unknown(message, msg_type)

    @staticmethod
    def _parse_status(message: Dict[str, Any]) -> Tuple[str, str, str]:
        sysinfo = message.get("sysINFO") or {}
        temp = message.get("tempINFO") or {}
        net = message.get("netINFO") or {}
        wans = net.get("WAN") or []
        wan = wans[0] if wans else {}
        name = sysinfo.get("routerNAME") or "Router"
        load = sysinfo.get("routerAVGLOAD") or []
        lines = [
            f"运行时间：{sysinfo.get('routerUPTIME', '-')}",
            f"负载：{' / '.join(str(x) for x in load) or '-'}",
            f"CPU：{temp.get('CPU', '-')}°C",
        ]
        mem = sysinfo.get("routerMEM") or {}
        if mem:
            lines.append(f"内存：{mem.get('free', '-')}/{mem.get('all', '-')}{mem.get('unit', '')}")
        if wan:
            lines.append(f"WAN IPv4：{wan.get('pubIPv4', '-')}")
            lines.append(f"WAN IPv6：{wan.get('pubIPv6', '-')}")
        return f"路由器状态 · {name}", "\n".join(lines), str(net.get("DDNS") or "")

    @staticmethod
    def _parse_ifup(message: Dict[str, Any]) -> Tuple[str, str, str]:
        nets = message.get("netSTATE") or []
        wan = nets[0] if nets else {}
        lines = [
            f"在线时间：{message.get('upTIME', '-')}",
            f"IPv4：{wan.get('pubIPv4', '-')}",
            f"IPv6：{wan.get('pubIPv6', '-')}",
        ]
        return "路由器重拨", "\n".join(lines), ""

    @staticmethod
    def _parse_dhcp(message: Dict[str, Any]) -> Tuple[str, str, str]:
        lines = [
            f"设备：{message.get('cliNAME', '-')}",
            f"IP：{message.get('cliIP', '-')}",
            f"MAC：{message.get('cliMAC', '-')}",
            f"上线时间：{message.get('upTIME', '-')}",
        ]
        return "设备上线", "\n".join(lines), ""

    @staticmethod
    def _parse_unknown(message: Dict[str, Any], msg_type: str) -> Tuple[str, str, str]:
        body = json.dumps(message, ensure_ascii=False)
        if len(body) > 1500:
            body = body[:1500] + "..."
        return f"RouterHook · {msg_type}", body, ""
