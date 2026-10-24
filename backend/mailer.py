import os
import re
import ipaddress
import logging
import httpx
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

logger = logging.getLogger("civicpro.mail")
EMAIL_BASE_URL = "https://integrations.emergentagent.com"

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")


async def send_email(*, to: list[str], subject: str, html: str) -> str | None:
    """Returns the provider id, or None when the send was refused/failed (logged)."""
    _assert_safe_email(subject, html)
    payload = {"to": to, "subject": subject, "html": html, "from_name": os.environ["EMAIL_FROM_NAME"]}
    if os.environ.get("EMAIL_REPLY_TO"):
        payload["contact_email"] = os.environ["EMAIL_REPLY_TO"]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}, json=payload)
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        try:
            info = e.response.json()
        except ValueError:
            info = {}
        if info.get("code") in ("insufficient_credits", "integration_disabled", "daily_limit_reached"):
            logger.warning(f"Email paused: {info.get('code')} ({e.response.status_code}): {info.get('message', '')}")
        else:
            logger.error(f"Email send failed: {e.response.status_code} {e.response.text}")
    except Exception as e:
        logger.error(f"Email send error: {e}")
    return None


def overdue_email(issue, project_name, recipient_name, app_url, for_manager):
    brand = escape(os.environ["EMAIL_FROM_NAME"])
    who = f"assigned to {escape(issue.get('owner') or 'no one yet')}" if for_manager else "assigned to you"
    link = f'<p style="margin:24px 0"><a href="{escape(app_url)}/issues" style="background:#d97706;color:#ffffff;padding:11px 18px;text-decoration:none;font-weight:bold">Open issues & risks</a></p>' if app_url.startswith("https://") else ""
    rows = "".join(f'<tr><td style="padding:6px 12px 6px 0;color:#64748b;font-size:13px">{k}</td><td style="padding:6px 0;font-size:13px;color:#0f172a"><b>{escape(str(v))}</b></td></tr>'
                   for k, v in (("Project", project_name), ("Severity", issue.get("severity", "")), ("Type", issue.get("category", "")), ("Action owner", issue.get("owner") or "Unassigned"), ("Was due", issue.get("due_date", "")), ("Status", issue.get("status", ""))))
    details = f'<p style="font-size:13px;color:#334155;line-height:1.5;white-space:pre-wrap">{escape(issue["description"])}</p>' if issue.get("description") else ""
    subject = f"Overdue follow-up: {issue['title']} ({project_name})"
    html = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8fb"><tr><td style="padding:28px">'
            f'<table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border-top:4px solid #d97706"><tr><td style="padding:28px;font-family:Arial,sans-serif">'
            f'<p style="font-size:11px;letter-spacing:1px;color:#d97706;margin:0 0 8px">{brand} · OVERDUE FOLLOW-UP</p>'
            f'<h2 style="margin:0 0 12px;color:#0f172a;font-size:20px">{escape(issue["title"])}</h2>'
            f'<p style="font-size:14px;color:#334155">Hi {escape(recipient_name)}, this follow-up {who} passed its due date and is still {escape(issue.get("status", "Open").lower())}.</p>'
            f'<table role="presentation" style="margin:12px 0">{rows}</table>{details}{link}'
            f'<p style="font-size:11px;color:#94a3b8;margin-top:24px">Sent by {brand} because this issue is overdue. You will get one reminder per due date.</p>'
            f'</td></tr></table></td></tr></table>')
    return subject, html
