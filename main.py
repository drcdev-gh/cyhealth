from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import asyncio
import configparser
import httpx
import logging
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


def validate_config():
    for section_name in config.sections():
        section = config[section_name]
        for key in ("name", "type", "timeout"):
            if key not in section:
                logger.error("Config error: section [%s] missing '%s'",
                             section_name, key)
                sys.exit(1)

        if section["type"] not in ("incoming_ping", "outgoing_ping"):
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
        last_ping[name] = startup_time

        if cfg.get("type") != "incoming_ping":
            continue

        path = f"/{name}"

        async def endpoint(_name=name):
            return await handle_incoming_ping(_name)

        app.post(path)(endpoint)


async def handle_incoming_ping(name: str):
    now = datetime.now(timezone.utc)
    last_ping[name] = now

    logger.info("[INCOMING PING] %s at %s", name, now.isoformat())

    return {
        "name": name,
        "last_ping": now.isoformat(),
    }


async def do_outgoing_ping(name: str, url: str):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            r.raise_for_status()
        last_ping[name] = datetime.now(timezone.utc)
        logger.info("[OUTGOING PING SUCCESS] %s at %s",
                    name, last_ping[name].isoformat())
    except Exception as e:
        logger.warning("[OUTGOING PING FAILED] %s: %s", name, e)


def is_expired(name: str) -> bool:
    for section in config.sections():
        cfg = config[section]
        if cfg["name"] != name:
            continue

        timeout = int(cfg.get("timeout"))
        ts = last_ping.get(name)

        if ts is None:
            return True

        expired = datetime.now(timezone.utc) - ts > timedelta(seconds=timeout)
        if expired:
            logger.warning("[EXPIRED]: %s at %s", name, ts.isoformat())
        return expired

    return True


@app.get("/health")
async def healthcheck():
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
        await asyncio.gather(*tasks)

    # ... and then check if anything is expired
    return await check_only()


@app.get("/status")
async def check_only():
    for section in config.sections():
        cfg = config[section]
        name = cfg["name"]
        if is_expired(name):
            raise HTTPException(
                status_code=503,
                detail=f"Pinger '{name}' expired"
            )
    return {"status": "ok"}

# --------

validate_config()
init()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
