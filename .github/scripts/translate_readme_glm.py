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
    glossary = (
        "Mandatory glossary — use these translations exactly:\n"
        "- channel plugin → 频道插件\n"
        "- channel → 频道 (when referring to messaging channels)\n"
        "- group channel → 群组频道\n"
        "- group policy → 群组策略\n"
        "- DM → 私信\n"
        "- access control → 访问控制\n"
        "- allowlist → 白名单\n"
        "- mention gating → @mention 门控\n"
        "- pairing → 配对\n"
        "- node → 节点\n"
        "- gateway → 网关\n"
        "- mesh network → mesh 网络\n"
        "- transport → 传输方式\n"
        "- repository → 仓库\n"
        "- pull request → Pull Request (keep English)\n"
        "- issue → issue (keep English)\n"
        "- broker → broker (keep English, MQTT term)\n"
        "- Serial → Serial (keep English in transport context)\n"
        "- AI Agent → AI Agent (keep English)\n"
        "- MeshClaw → MeshClaw (keep English)\n"
        "- OpenClaw → OpenClaw (keep English)\n"
        "- Meshtastic → Meshtastic (keep English)\n"
        "- LoRa → LoRa (keep English)\n"
    )

    system_prompt = (
        "You are a native Simplified Chinese technical writer translating an open-source README. "
        "Write like a Chinese developer writing docs for other Chinese developers — concise, direct, natural. "
        "DO NOT produce literal/mechanical translation. Rephrase for natural Chinese reading flow. "
        "Examples of BAD vs GOOD translations:\n"
        "  BAD:  此存储库是一个 OpenClaw 通道插件，不是一个独立的应用程序。\n"
        "  GOOD: 这是 OpenClaw 的频道插件，不是独立应用。\n"
        "  BAD:  您需要一个正在运行的 OpenClaw 网关（Node.js 22+）才能使用它。\n"
        "  GOOD: 需要先安装并运行 OpenClaw 网关（Node.js 22+）。\n"
        "  BAD:  在提交问题时要包括传输模式、编辑后的配置。\n"
        "  GOOD: 提 issue 时请附上传输方式、配置（隐去密钥）。\n"
        "  BAD:  欢迎拉取请求\n"
        "  GOOD: 欢迎提交 Pull Request\n"
        "Rules:\n"
        "- Use 你 not 您\n"
        "- Omit unnecessary 的、了、一个、进行 — keep sentences tight\n"
        "- Preserve markdown structure exactly: headings, links, tables, code fences, inline code, image paths\n"
        "- Do not translate URLs, package names, commands, code blocks, file paths, env vars, or link anchors\n"
        "- Keep line breaks and section order identical\n"
        "- Return only the translated markdown, no explanation\n\n"
        + glossary
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
