#!/usr/bin/env python
"""
Simple image proxy server to bypass hotlinking restrictions.
Run: python image_proxy.py --host 0.0.0.0 --port 8000

Endpoint: GET /image?url=<url-encoded-image-url>
Caching: stores images in `data/image_cache` by default (sha256 filename).
"""
import argparse
import asyncio
import hashlib
import logging
import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote_plus

import aiohttp
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("image_proxy")

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "image_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
}

async def fetch_and_cache(session: aiohttp.ClientSession, url: str, cache_path: Path):
    async with session.get(url, headers=DEFAULT_HEADERS, timeout=30) as resp:
        if resp.status != 200:
            raise web.HTTPBadGateway(text=f"Upstream returned status {resp.status}")
        content = await resp.read()
        ctype = resp.headers.get("Content-Type", "application/octet-stream")
        # determine extension
        ext = mimetypes.guess_extension(ctype.split(";")[0].strip()) or ""
        final_path = cache_path.with_suffix(ext)
        with open(final_path, "wb") as f:
            f.write(content)
        return final_path, ctype

async def handle_image(request: web.Request):
    q = request.query.get("url")
    if not q:
        raise web.HTTPBadRequest(text="Missing url parameter")
    url = unquote_plus(q)

    # hash url for caching
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    cache_path_base = CACHE_DIR / h

    # If cached file exists (any extension), serve it
    for f in CACHE_DIR.glob(f"{h}.*"):
        logger.info("Serving from cache: %s", f)
        mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        return web.FileResponse(path=str(f), headers={"Cache-Control": "public, max-age=86400"}, content_type=mime)

    # Fetch and cache
    async with aiohttp.ClientSession() as session:
        try:
            final_path, ctype = await fetch_and_cache(session, url, cache_path_base)
        except web.HTTPError as e:
            logger.error("Upstream error when fetching %s: %s", url, e)
            raise
        except Exception as e:
            logger.exception("Failed to fetch %s: %s", url, e)
            raise web.HTTPBadGateway(text=str(e))

    return web.FileResponse(path=str(final_path), headers={"Cache-Control": "public, max-age=86400"}, content_type=ctype)


def main():
    parser = argparse.ArgumentParser(description="Run image proxy server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = web.Application()
    app.add_routes([web.get("/image", handle_image)])

    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
