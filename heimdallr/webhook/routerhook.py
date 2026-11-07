import json
from typing import Any, Dict, List, Tuple

from heimdallr.webhook.base import WebhookBase

MAX_BODY_LEN = 1800


def _fmt(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _present(value: Any) -> bool:
    return value not in (None, "", {}, [])


_WIFI_LABEL = {"24G": "2.4G", "5G1": "5G", "5G2": "5G2", "SmartConnect": "SmartConnect"}


class RouterHookWebhook(WebhookBase):
    """解析 RouterHook 插件推送的 JSON，只输出 payload 里实际存在的字段。"""

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

    @classmethod
    def _parse_status(cls, message: Dict[str, Any]) -> Tuple[str, str, str]:
        sysinfo = message.get("sysINFO") or {}
        temp = message.get("tempINFO") or {}
        net = message.get("netINFO") or {}
        lines: List[str] = []
        if sysinfo:
            lines.append(f"运行：{_fmt(sysinfo.get('routerUPTIME'))}")
            meta = []
            if _present(sysinfo.get("routerFIRMWARE")):
                meta.append(f"固件 {sysinfo['routerFIRMWARE']}")
            if _present(sysinfo.get("routerMODE")):
                meta.append(f"模式 {sysinfo['routerMODE']}")
            if meta:
                lines.append(" · ".join(meta))
            load = sysinfo.get("routerAVGLOAD") or []
            if load:
                lines.append("负载：" + " / ".join(_fmt(x) for x in load))
            mem = sysinfo.get("routerMEM") or {}
            if mem:
                unit = mem.get("unit", "MB")
                lines.append(f"内存：{_fmt(mem.get('free'))}/{_fmt(mem.get('all'))}{unit}")
            swap = sysinfo.get("routerSWAP") or {}
            if cls._to_float(swap.get("total")) > 0:
                lines.append(f"SWAP：{_fmt(swap.get('free'))}/{_fmt(swap.get('total'))}MB")
            jffs = sysinfo.get("routerJFFS") or {}
            if jffs and (_present(jffs.get("total")) or _present(jffs.get("used"))):
                lines.append(f"JFFS：{_fmt(jffs.get('used'))}/{_fmt(jffs.get('total'))}（{_fmt(jffs.get('use'))}）")
        if temp:
            unit = temp.get("unit", "°C")
            temps = []
            for key, label in (("CPU", "CPU"), ("24G", "2.4G"), ("5G1", "5G"), ("5G2", "5G2")):
                if _present(temp.get(key)):
                    temps.append(f"{label} {temp[key]}")
            if temps:
                lines.append(f"温度：{' · '.join(temps)}{unit}")
        wans = [w for w in (net.get("WAN") or []) if w]
        for index, wan in enumerate(wans):
            lines.extend(cls._format_wan(wan, index, len(wans)))
        if _present(net.get("DDNS")):
            lines.append(f"DDNS：{net['DDNS']}")
        if _present(net.get("routerLANIP")):
            lines.append(f"LAN：{net['routerLANIP']}")
        wifi = net.get("wifiINFO") or {}
        wifi_items = [f"{_WIFI_LABEL.get(k, k)} {v}" for k, v in wifi.items() if _present(v)]
        if wifi_items:
            lines.append("WiFi：" + " · ".join(wifi_items))
        guest = net.get("guestINFO") or {}
        guest_items = [f"{k} {v}" for k, v in guest.items() if k != "end" and _present(v)]
        if guest_items:
            lines.append("访客：" + " · ".join(guest_items))
        if _present(net.get("chinaSTATUS")):
            lines.append(str(net["chinaSTATUS"]))
        if _present(net.get("foreignSTATUS")):
            lines.append(str(net["foreignSTATUS"]))
        for index, dev in enumerate(message.get("usbINFO") or []):
            if dev and _present(dev.get("name")):
                lines.append(
                    f"USB{index + 1}：{dev['name']} {_fmt(dev.get('status'))} "
                    f"{_fmt(dev.get('used'))}/{_fmt(dev.get('total'))}（{_fmt(dev.get('use'))}）"
                )
        clients = [c for c in (message.get("cliINFO") or []) if c]
        if clients:
            names = [str(c.get("name") or c.get("ip") or "?") for c in clients]
            lines.append(cls._list_summary("在线设备", names))
        dhcp = [d for d in (message.get("dhcpINFO") or []) if d]
        if dhcp:
            lines.append(f"DHCP 租约：{len(dhcp)} 台")
        name = sysinfo.get("routerNAME")
        title = f"路由器状态 · {name}" if name else "路由器状态"
        body = "\n".join(lines) if lines else json.dumps(message, ensure_ascii=False)
        return title, cls._truncate(body), str(net.get("DDNS") or "")

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _format_wan(wan: Dict[str, Any], index: int, total: int) -> List[str]:
        prefix = f"WAN{index}" if total > 1 else "WAN"
        head = f"{prefix}：{_fmt(wan.get('pubIPv4'))}"
        if _present(wan.get("proto")):
            head += f"（{wan['proto']}）"
        out = [head]
        if _present(wan.get("pubIPv6")):
            out.append(f"  IPv6：{wan['pubIPv6']}")
        dns = [str(d) for d in (wan.get("wanDNS") or []) if _present(d)]
        if dns:
            out.append("  DNS：" + " / ".join(dns))
        if _present(wan.get("wanRX")) or _present(wan.get("wanTX")):
            out.append(f"  流量：↓{_fmt(wan.get('wanRX'))} ↑{_fmt(wan.get('wanTX'))}")
        return out

    @staticmethod
    def _list_summary(label: str, names: List[str]) -> str:
        head = "、".join(names[:5])
        if len(names) > 5:
            return f"{label}：{head} 等 {len(names)} 台"
        return f"{label}：{head}（{len(names)} 台）"

    @staticmethod
    def _truncate(body: str) -> str:
        if len(body) <= MAX_BODY_LEN:
            return body
        return body[: MAX_BODY_LEN - 3] + "..."

    @classmethod
    def _parse_ifup(cls, message: Dict[str, Any]) -> Tuple[str, str, str]:
        lines = [f"在线时间：{_fmt(message.get('upTIME'))}"]
        if _present(message.get("rebootTIME")):
            lines.append(f"重启时间：{message['rebootTIME']}")
        wans = [w for w in (message.get("netSTATE") or []) if w]
        for index, wan in enumerate(wans):
            lines.extend(cls._format_wan(wan, index, len(wans)))
        return "路由器重拨", cls._truncate("\n".join(lines)), ""

    @classmethod
    def _parse_dhcp(cls, message: Dict[str, Any]) -> Tuple[str, str, str]:
        lines = [f"设备：{_fmt(message.get('cliNAME'))}", f"IP：{_fmt(message.get('cliIP'))}"]
        if _present(message.get("cliMAC")):
            lines.append(f"MAC：{message['cliMAC']}")
        if _present(message.get("upTIME")):
            lines.append(f"上线：{message['upTIME']}")
        if _present(message.get("expTIME")):
            lines.append(f"租约到期：{message['expTIME']}")
        lists = [c for c in (message.get("cliLISTS") or []) if c]
        if lists:
            lines.append(f"DHCP 租约：{len(lists)} 台")
        return "设备上线", cls._truncate("\n".join(lines)), ""

    @staticmethod
    def _parse_unknown(message: Dict[str, Any], msg_type: str) -> Tuple[str, str, str]:
        body = json.dumps(message, ensure_ascii=False)
        if len(body) > MAX_BODY_LEN:
            body = body[: MAX_BODY_LEN - 3] + "..."
        return f"RouterHook · {msg_type}", body, ""
