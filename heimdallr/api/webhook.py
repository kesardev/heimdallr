import json
import logging

from fastapi import APIRouter, Request

from heimdallr.api.base import serve_channels_async
from heimdallr.webhook.github_star import GithubStarWebhook
from heimdallr.webhook.routerhook import RouterHookWebhook

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/webhook")


@webhook_router.post("/github/star/{key}")
async def github_star(key: str, req: Request):
    body = await req.body()
    webhook = GithubStarWebhook(json.loads(body))
    title, msg_body, jump_url = webhook.parse()
    return await serve_channels_async(key, title, msg_body, jump_url=jump_url)


@webhook_router.post("/rsspush/{key}")
async def rsspush(key: str, req: Request):
    form = await req.form()
    task_title = form.get("task_title")
    title = form.get("title")
    desp = form.get("desp")
    jump_url = form.get("link")
    return await serve_channels_async(key, f"{task_title}", f"{title}\n{desp}", jump_url=jump_url)


@webhook_router.post("/routerhook/{key}")
async def routerhook(key: str, req: Request):
    body = await req.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {}
    webhook = RouterHookWebhook(payload)
    title, msg_body, jump_url = webhook.parse()
    return await serve_channels_async(key, title, msg_body, jump_url=jump_url)
