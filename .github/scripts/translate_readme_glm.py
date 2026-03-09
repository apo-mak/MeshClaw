#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "README.md"
TARGET = ROOT / "README.zh-CN.md"
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = os.environ.get("GLM_MODEL", "glm-4-flash")


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:markdown|md)?\n([\s\S]*?)\n```$", stripped, re.IGNORECASE)
    if match:
        return match.group(1).strip() + "\n"
    return text


def _request_translation(source_markdown: str, api_key: str) -> str:
    system_prompt = (
        "You are a professional technical translator for open-source projects. "
        "Translate English README markdown to Simplified Chinese. "
        "Preserve markdown structure exactly: headings, links, tables, code fences, inline code, and image paths. "
        "Do not translate URLs, package names, commands, code blocks, file paths, environment variables, or anchors in markdown links. "
        "Keep line breaks and section order as close as possible. "
        "Return only translated markdown content."
    )

    payload = {
        "model": MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Translate the following README markdown to Simplified Chinese:\n\n"
                + source_markdown,
            },
        ],
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GLM API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GLM API request failed: {exc}") from exc

    parsed = json.loads(body)
    choices = parsed.get("choices")
    if not choices:
        raise RuntimeError(f"GLM API returned no choices: {body}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"GLM API returned empty content: {body}")

    return _strip_markdown_fence(content)


def main() -> int:
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        print("GLM_API_KEY is not set; skipping translation.")
        return 0

    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source file: {SOURCE}")

    source_markdown = SOURCE.read_text(encoding="utf-8")
    translated = _request_translation(source_markdown, api_key)
    TARGET.write_text(translated, encoding="utf-8")

    print(f"Translated {SOURCE.name} -> {TARGET.name} using model {MODEL}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Translation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
