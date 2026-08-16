from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import urlparse, parse_qs
import re
import os
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")


def check_steam_url(url: str):
    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        return {
            "valid": False,
            "type": "INVALID",
            "details": "URL inválido."
        }

    if parsed.scheme not in ("http", "https"):
        return {
            "valid": False,
            "type": "INVALID",
            "details": "O URL precisa começar por http:// ou https://."
        }

    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()

    # =========================
    # STEAM WORKSHOP
    # =========================
    if host == "steamcommunity.com":
        if path == "/sharedfiles/filedetails":
            query = parse_qs(parsed.query)
            workshop_id = query.get("id", [None])[0]

            if workshop_id and workshop_id.isdigit():
                result = {
                    "valid": True,
                    "type": "STEAM WORKSHOP",
                    "details": f"Workshop ID: {workshop_id}",
                    "id": workshop_id
                }

                send_discord(url, result)
                return result

            return {
                "valid": False,
                "type": "STEAM WORKSHOP",
                "details": "Workshop encontrado, mas o ID é inválido."
            }

    # =========================
    # STEAM GAME
    # =========================
    if host == "store.steampowered.com":
        match = re.search(r"/app/(\d+)(?:/([^/?#]+))?", parsed.path)

        if match:
            app_id = match.group(1)
            name = match.group(2)

            if name:
                name = name.replace("_", " ")
            else:
                name = "Desconhecido"

            result = {
                "valid": True,
                "type": "STEAM GAME",
                "details": f"App ID: {app_id}",
                "name": name,
                "id": app_id
            }

            send_discord(url, result)
            return result

    # =========================
    # STEAM DESCONHECIDO
    # =========================
    if host in ("steamcommunity.com", "store.steampowered.com"):
        return {
            "valid": False,
            "type": "UNKNOWN STEAM LINK",
            "details": "É um link Steam, mas não é um formato suportado."
        }

    # =========================
    # NÃO STEAM
    # =========================
    return {
        "valid": False,
        "type": "NOT STEAM",
        "details": "Este URL não pertence à Steam."
    }


def send_discord(url, result):
    if not DISCORD_WEBHOOK:
        return

    fields = [
        {
            "name": "Tipo",
            "value": result["type"],
            "inline": True
        },
        {
            "name": "URL",
            "value": url,
            "inline": False
        },
        {
            "name": "Informação",
            "value": result["details"],
            "inline": False
        }
    ]

    payload = {
        "embeds": [
            {
                "title": "Steam Link Checker",
                "description": (
                    "Link válido"
                    if result["valid"]
                    else "Link inválido ou desconhecido"
                ),
                "fields": fields,
                "footer": {
                    "text": "Steam Link Checker"
                }
            }
        ]
    }

    try:
        requests.post(
            DISCORD_WEBHOOK,
            json=payload,
            timeout=5
        )
    except requests.RequestException:
        pass


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.get("/check")
async def check(url: str):
    return JSONResponse(check_steam_url(url))


@app.get("/health")
async def health():
    return {"status": "online"}