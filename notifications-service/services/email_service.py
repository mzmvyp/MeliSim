import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

log = logging.getLogger("notifications.email")

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render(template_name: str, **ctx: Any) -> str:
    tpl = _env.get_template(template_name)
    return tpl.render(**ctx)


def send_email(to_user_id: int, subject: str, body_html: str) -> None:
    # Simulated — print instead of shipping SMTP/SES in a demo system.
    log.info(
        "EMAIL to user=%s subject=%r body_chars=%d",
        to_user_id, subject, len(body_html),
    )
    print("=" * 60)
    print(f"[EMAIL] to=user:{to_user_id}")
    print(f"[EMAIL] subject={subject}")
    print(body_html[:500] + ("..." if len(body_html) > 500 else ""))
    print("=" * 60)
