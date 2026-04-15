"""
GET / — Serves the single-page React UI.

Reads the static HTML file once per request (file is ~10KB, sync read is fine).
The HTML file loads React, ReactDOM, and Babel from CDN — no build step required.
"""

import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def ui():
    with open(_HTML_PATH) as f:
        return f.read()
