from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Header
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import asyncio
import configparser
import httpx
import logging
import os
import sys

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"]
)

logger = logging.getLogger("uvicorn")

last_ping: Dict[str, datetime] = {}

config = configparser.ConfigParser()
read = config.read("/etc/cyhealth.ini")

if not read:
    raise FileNotFoundError("/etc/cyhealth.ini not found")

if "API_KEY" not in os.environ:
    logger.error("No API key variable found")
    sys.exit(1)

API_KEY = os.environ["API_KEY"]


def validate_config():
    for section_name in config.sections():
        section = config[section_name]
        for key in ("name", "type", "timeout"):
            if key not in section:
                logger.error("Config error: section [%s] missing '%s'",
                             section_name, key)
                sys.exit(1)

        if section["type"] not in ("incoming_ping", "outgoing_ping", "error_ping"):
            logger.error("Config error: section [%s] has invalid type '%s'",
                         section_name, section["type"])
            sys.exit(1)

        if section["type"] == "outgoing_ping":
            if "url" not in section:
                logger.error("Config error: section [%s] needs to have an URL",
                             section_name)
                sys.exit(1)

        try:
            timeout_val = int(section["timeout"])
            if timeout_val <= 0:
                raise ValueError()
        except ValueError:
            logger.error("Config error: section [%s] has invalid timeout '%s'",
                         section_name, section["timeout"])
            sys.exit(1)


def init():
    startup_time = datetime.now(timezone.utc)

    for section in config.sections():
        cfg = config[section]
        name = cfg["name"]
        if cfg["type"] != "error_ping":
            last_ping[name] = startup_time
        else:
            last_ping[name] = None

        if cfg.get("type") == "incoming_ping":
            path = f"/{name}"

            async def endpoint(_name=name, x_api_key: str = Header(...)):
                return await handle_incoming_ping(_name, x_api_key)

            app.post(path)(endpoint)

        if cfg.get("type") == "error_ping":
            path = f"/{name}"

            async def endpoint(_name=name, x_api_key: str = Header(...)):
                return await handle_error_ping(_name, x_api_key)

            app.post(path)(endpoint)


async def handle_incoming_ping(name: str, x_api_key: str):
    if x_api_key != API_KEY:
        logger.warning("Invalid API Key: %s", x_api_key)
        raise HTTPException(status_code=403)

    now = datetime.now(timezone.utc)
    last_ping[name] = now

    logger.debug("[INCOMING PING] %s at %s", name, now.isoformat())

    return {
        "name": name,
        "last_ping": now.isoformat(),
    }


async def handle_error_ping(name: str, x_api_key: str):
    if x_api_key != API_KEY:
        logger.warning("Invalid API Key: %s", x_api_key)
        raise HTTPException(status_code=403)

    now = datetime.now(timezone.utc)
    last_ping[name] = now

    logger.debug("[INCOMING ERROR PING] %s at %s", name, now.isoformat())

    return {
        "name": name,
        "last_ping": now.isoformat(),
    }


async def do_outgoing_ping(name: str, url: str):
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(url)
                r.raise_for_status()

            last_ping[name] = datetime.now(timezone.utc)
            logger.debug(
                "[OUTGOING PING SUCCESS] %s at %s",
                name,
                last_ping[name].isoformat(),
            )
            return

        except Exception:
            if attempt == 1:
                logger.warning(
                    "[OUTGOING PING FAILED] %s — retrying once...",
                    name,
                )
                await asyncio.sleep(1)
            else:
                logger.exception(
                    "[OUTGOING PING FAILED AFTER RETRY] %s",
                    name,
                )


def is_faulty(name: str) -> bool:
    for section in config.sections():
        cfg = config[section]
        if cfg["name"] != name:
            continue

        timeout = int(cfg.get("timeout"))
        ts = last_ping.get(name)

        if ts is None:
            return True

        if cfg["type"] == "incoming_ping" or cfg["type"] == "outgoing_ping":
            expired = datetime.now(timezone.utc) - ts > timedelta(seconds=timeout)
            if expired:
                logger.warning("[EXPIRED]: %s at %s", name, ts.isoformat())
            return expired
        else:
            last_error_ping_expired = datetime.now(timezone.utc) - ts > timedelta(seconds=timeout)
            if not last_error_ping_expired:
                logger.warning("[FAULTY]: %s at %s", name, ts.isoformat())
            return not last_error_ping_expired

    return True


@app.post("/trigger")
async def trigger(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        logger.warning("Invalid API Key: %s", x_api_key)
        raise HTTPException(status_code=403)

    tasks = []
    for section in config.sections():
        cfg = config[section]
        name = cfg["name"]

        # First, re-run outgoing pings...
        if cfg.get("type") == "outgoing_ping":
            url = cfg.get("url")
            if url:
                tasks.append(do_outgoing_ping(name, url))

    if tasks:
        return await asyncio.gather(*tasks)

    return None


@app.get("/status")
async def check_only():
    full_list = []
    faulty_list = []

    for section in config.sections():
        cfg = config[section]

        name = cfg["name"]
        if not last_ping.get(name):
            continue

        ts = last_ping.get(name).isoformat()
        full_list.append({"name": name, "last_ping": ts})

        if is_faulty(name):
            if ts is not None:
                faulty_list.append({"name": name, "last_ping": ts})

    if faulty_list:
        raise HTTPException(
            status_code=503,
            detail={"faulty": faulty_list}
        )

    return {"status": "ok", "pingers": full_list}

# --------

validate_config()
init()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
