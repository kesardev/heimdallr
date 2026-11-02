<h1>使用 Heimdallr 接收 RouterHook 推送</h1>

[RouterHook](https://github.com/sdlyfjx/rogsoft/tree/RouterHook/routerhook) 是运行在 koolshare / 梅林固件上的通知插件：路由器在定时任务、重拨、设备上线等事件发生时，会把固定结构的 JSON POST 到你配置的 URL。

## 配置

1. 在 Heimdallr 的 .env 里创建分组和渠道，拿到分组 token：

```
ENABLED_GROUPS=router
router_ENABLED_CHANNELS=ch_bark
router_TOKEN=<TOKEN>
```

2. 在 RouterHook 的「回调 URL」中填入：

```
http://<heimdallr地址>:9000/webhook/routerhook/<TOKEN>
```

URL 支持配置多条，也支持 `_PRM_EVENT` 等占位符；这个接口按请求体里的 `msgTYPE` 自动选择格式，不需要占位符。

## 支持的事件

| msgTYPE | 说明 | 标题 |
| --- | --- | --- |
| `manuINFO` / `cronINFO` | 手动、定时推送的路由器状态 | 路由器状态 · 设备名 |
| `ifUP` | 网络重拨上线 | 路由器重拨 |
| `newDHCP` | 设备上线 | 设备上线 |
| 其他（如 `rh_*`） | 原样 JSON，截断到 1500 字符 | RouterHook · 类型 |

## 示例

```bash
curl -X POST 'http://127.0.0.1:9000/webhook/routerhook/<TOKEN>' -H 'Content-Type: application/json' -d '{"msgTYPE":"newDHCP","cliNAME":"MI5C","cliIP":"192.168.0.10","cliMAC":"aa:bb:cc:dd:ee:ff","upTIME":"2026年11月02日 21点00分00秒"}'
```

返回 `{"code":0,"message":"success"}` 表示已分发到分组内的所有渠道。
