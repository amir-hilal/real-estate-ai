"""
GET /versions — List available prompt versions.

Scans the prompts directory for versioned subdirectories (v1/, v2/, v3/…)
and returns the list of versions with metadata.
"""

import re

from fastapi import APIRouter

from app.config import resolve_prompt_version, settings

router = APIRouter()

# Version descriptions (shown in the frontend version selector dropdown)
_VERSION_NOTES: dict[str, str] = {
    "v1": "Original — the classic conversation style",
    "v2": "Improved — asks for the most important details first",
    "v3": "Recommended — uses full neighborhood names throughout",
}


@router.get("/versions")
async def list_versions():
    """
    Return available prompt versions and the current server default.

    A version directory is valid if it contains at least chat.md and explanation.md.
    """
    prompts_dir = settings.prompts_dir
    pattern = re.compile(r"^v\d+$")

    versions = []
    for path in sorted(prompts_dir.iterdir()):
        if path.is_dir() and pattern.match(path.name):
            # Only list versions that have both chat and explanation prompts
            if (path / "chat.md").exists() and (path / "explanation.md").exists():
                ver = path.name
                versions.append({
                    "version": ver,
                    "description": _VERSION_NOTES.get(ver, ""),
                })

    return {
        "default": resolve_prompt_version(settings.prompt_version),
        "versions": versions,
    }
