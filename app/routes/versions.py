"""
GET /versions — List available chat prompt versions.

Scans the prompts directory for chat_v*.md files and returns
the list of versions with metadata.
"""

import re

from fastapi import APIRouter

from app.config import settings

router = APIRouter()

# Version descriptions (what changed in each)
_VERSION_NOTES: dict[str, str] = {
    "v1": "Initial chat prompt",
    "v2": "Stronger missing-field enforcement, no optional questions while required fields missing",
    "v3": "Neighborhood full names in replies (never codes)",
}


@router.get("/versions")
async def list_versions():
    """
    Return available chat prompt versions and the current server default.
    """
    prompts_dir = settings.prompts_dir
    pattern = re.compile(r"^chat_(v\d+)\.md$")

    versions = []
    for path in sorted(prompts_dir.glob("chat_v*.md")):
        match = pattern.match(path.name)
        if match:
            ver = match.group(1)
            versions.append({
                "version": ver,
                "description": _VERSION_NOTES.get(ver, ""),
            })

    return {
        "default": settings.chat_prompt_version,
        "versions": versions,
    }
