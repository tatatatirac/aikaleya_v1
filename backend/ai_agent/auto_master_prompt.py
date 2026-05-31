"""Auto-generate a tenant-specific master_prompt by scraping their website
and asking Claude to write a tailored receptionist persona.

The result is saved to ClientApiSettings.master_prompt and gets injected
into every voice/SMS/WhatsApp turn (see ai_agent.prompts.build_voice_prompt
and the planner prompts).

Usage (via management command):
  python manage.py generate_master_prompt --client-id 1 --website-url https://mikesbarber.com
"""

import json
import logging
import re
from html.parser import HTMLParser
from urllib import error, request as urllib_request

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Website scraper ────────────────────────────────────────────────────────────
class _TextHarvester(HTMLParser):
    """Strip HTML, keep <title>, <meta description>, and visible body text."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "iframe"}

    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False
        self._skip_depth = 0
        self._text_chunks = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attrs_dict = dict(attrs)
            name = (attrs_dict.get("name") or attrs_dict.get("property") or "").lower()
            if name in {"description", "og:description"}:
                self.description = (attrs_dict.get("content") or "").strip()

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = text
            return
        self._text_chunks.append(text)

    def body_text(self, max_chars: int = 4000) -> str:
        joined = " ".join(self._text_chunks)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined[:max_chars]


def fetch_website_snapshot(url: str, timeout: int = 15) -> dict:
    """
    Returns {'title': ..., 'description': ..., 'body': ..., 'url': resolved_url}.
    Returns {} on failure — caller decides what to do.
    """
    if not url:
        return {}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    req = urllib_request.Request(
        url,
        headers={
            "User-Agent": "KaleyaBot/1.0 (+https://aikaleya.com)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                html = raw.decode(charset, errors="replace")
            except LookupError:
                html = raw.decode("utf-8", errors="replace")
            resolved = resp.geturl()
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        logger.warning("Website fetch failed for %s: %s", url, exc)
        return {}

    harvester = _TextHarvester()
    try:
        harvester.feed(html)
    except Exception as exc:
        logger.warning("HTML parse failed for %s: %s", url, exc)
        return {"url": resolved, "title": "", "description": "", "body": ""}

    return {
        "url": resolved,
        "title": harvester.title.strip(),
        "description": harvester.description.strip(),
        "body": harvester.body_text(),
    }


# ── Claude call ────────────────────────────────────────────────────────────────
GENERATOR_SYSTEM = """\
You write short, focused receptionist-persona briefs that get fed into Kaleya
(an AI phone/WhatsApp receptionist) as her per-salon personality overlay.

You will receive raw website content for one specific business. From that
content, derive:
  - Business type (barbershop, hair salon, spa, dental, nail studio, etc.)
  - Tone the brand uses (luxury / casual / family-friendly / clinical / etc.)
  - Any specific quirks the owner is proud of (signature service, mascot,
    in-jokes the regulars know, languages spoken)
  - Hard constraints worth knowing (no card on file, walk-ins only, etc.)

Output ONLY the persona brief itself — no preamble, no markdown headers,
no "Here is...". 6–10 short bullet lines max. Address Kaleya directly in
imperative voice ("Keep replies under one sentence — this is a fast-paced
barbershop").

If the website content is too thin or off-topic, return the single line:
  (skip: insufficient website signal)
"""


def _call_claude(system: str, user: str, max_tokens: int = 500) -> str:
    api_key = getattr(settings, "KALEYA_ANTHROPIC_API_KEY", "")
    model = getattr(settings, "KALEYA_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    if not api_key:
        raise RuntimeError("KALEYA_ANTHROPIC_API_KEY is not configured.")
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib_request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data.get("content") or []
    texts = [item.get("text", "") for item in content if item.get("type") == "text"]
    return "\n".join(t for t in texts if t).strip()


# ── Public API ────────────────────────────────────────────────────────────────
def generate_master_prompt_from_website(business_client, website_url: str, save: bool = True) -> str:
    """
    Fetches the salon's website, asks Claude to draft a tailored persona
    brief, and (by default) persists it to ClientApiSettings.master_prompt.
    Returns the generated brief (or empty string if generation was skipped).
    """
    snapshot = fetch_website_snapshot(website_url)
    if not snapshot or not (snapshot.get("title") or snapshot.get("description") or snapshot.get("body")):
        logger.info("No usable website content for %s — skipping", website_url)
        return ""

    user_payload = (
        f"Business name (from DB): {business_client.public_name or business_client.name}\n"
        f"Website URL: {snapshot.get('url', website_url)}\n"
        f"Page title: {snapshot.get('title','')}\n"
        f"Meta description: {snapshot.get('description','')}\n"
        f"---\nPage text excerpt:\n{snapshot.get('body','')}\n"
    )

    brief = _call_claude(GENERATOR_SYSTEM, user_payload).strip()
    if not brief or brief.lower().startswith("(skip"):
        logger.info("Claude opted to skip persona for %s", business_client)
        return ""

    if save:
        try:
            from clients.models import ClientApiSettings
            api_settings, _ = ClientApiSettings.objects.get_or_create(business_client=business_client)
            api_settings.master_prompt = brief
            api_settings.save(update_fields=["master_prompt"])
        except Exception as exc:
            logger.exception("Failed to save master_prompt for %s: %s", business_client, exc)
            raise

    return brief
