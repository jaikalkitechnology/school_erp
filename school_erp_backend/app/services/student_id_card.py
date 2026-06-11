"""Render a student ID card to a PDF.

One A6-ish card per page (we'll just use A4 portrait with the card drawn
centered for now — schools usually print on cardstock and trim). Pulls
everything off `StudentProfileView` so the renderer doesn't re-query the
DB.
"""

from __future__ import annotations

import io
import secrets
import uuid
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.config import settings
from app.core.file_storage import ensure_tenant_dirs


def _safe_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _draw_card(c: canvas.Canvas, *, profile, photo_path: Optional[Path], logo_path: Optional[Path]) -> None:
    page_w, page_h = A4
    card_w = 86 * mm
    card_h = 54 * mm
    x = (page_w - card_w) / 2
    y = (page_h - card_h) / 2

    # Frame.
    c.setFillColor(colors.HexColor("#FFF7E6"))
    c.setStrokeColor(colors.HexColor("#1F1248"))
    c.setLineWidth(1.2)
    c.roundRect(x, y, card_w, card_h, 5 * mm, fill=1, stroke=1)

    # Top band: school name + logo.
    c.setFillColor(colors.HexColor("#1F1248"))
    c.rect(x, y + card_h - 12 * mm, card_w, 12 * mm, fill=1, stroke=0)
    if logo_path is not None and logo_path.is_file():
        try:
            c.drawImage(
                str(logo_path),
                x + 2 * mm, y + card_h - 11 * mm,
                width=10 * mm, height=10 * mm,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            pass
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    name = _safe_text(profile.school_name) or "School"
    c.drawString(x + 14 * mm, y + card_h - 6 * mm, name[:36])
    c.setFont("Helvetica", 7)
    c.drawString(x + 14 * mm, y + card_h - 10 * mm, "STUDENT IDENTITY CARD")

    # Photo box (left).
    photo_x = x + 4 * mm
    photo_y = y + 6 * mm
    photo_w = 22 * mm
    photo_h = 28 * mm
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#1F1248"))
    c.setLineWidth(0.8)
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)
    if photo_path is not None and photo_path.is_file():
        try:
            c.drawImage(
                str(photo_path),
                photo_x, photo_y,
                width=photo_w, height=photo_h,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            c.setFillColor(colors.HexColor("#FFF7E6"))
            c.setFont("Helvetica", 7)
            c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, "Photo")
    else:
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#888888"))
        c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, "Photo")

    # Details column (right of photo).
    text_x = photo_x + photo_w + 4 * mm
    text_w = card_w - (text_x - x) - 4 * mm

    def line(label: str, value: str, baseline_y: float) -> None:
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 6)
        c.drawString(text_x, baseline_y + 3, label.upper())
        c.setFillColor(colors.HexColor("#1F1248"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(text_x, baseline_y - 4, value[:32] if value else "—")

    line("Name", _safe_text(profile.full_name), photo_y + photo_h - 4)
    line("Adm. No.", _safe_text(profile.admission_number), photo_y + photo_h - 14)
    class_line = "/".join(
        v for v in (_safe_text(profile.class_label),
                    _safe_text(profile.section_name)) if v
    ) or "—"
    line("Class · Section", class_line, photo_y + photo_h - 24)
    dob = profile.date_of_birth.isoformat() if profile.date_of_birth else "—"
    line(
        f"DOB · Blood",
        f"{dob}   {_safe_text(profile.blood_group) or '—'}",
        photo_y + 6,
    )

    # Footer strip.
    c.setFillColor(colors.HexColor("#FFE4B8"))
    c.rect(x, y, card_w, 5 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1F1248"))
    c.setFont("Helvetica", 6)
    parent_phone = _safe_text(profile.parent_phone) or _safe_text(profile.emergency_phone)
    footer_parts = [p for p in [
        f"Parent: {parent_phone}" if parent_phone else None,
        f"School: {_safe_text(profile.school_phone)}" if profile.school_phone else None,
    ] if p]
    c.drawString(x + 3 * mm, y + 1.5 * mm, "  ·  ".join(footer_parts)[:80])


def render_id_card_pdf(profile, *, tenant_id: int) -> Path:
    """Render `profile` to a PDF on disk and return the absolute path."""
    ensure_tenant_dirs(tenant_id)
    base = Path(settings.UPLOAD_DIR) / f"tenant_{tenant_id}" / "students" / "id_cards"
    base.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{secrets.token_hex(2)}.pdf"
    target = base / filename

    photo_path: Optional[Path] = None
    if profile.photo_url:
        # photo_url is a relative path like "tenant_X/students/photos/abc.jpg"
        candidate = (Path(settings.UPLOAD_DIR) / profile.photo_url).resolve()
        upload_root = Path(settings.UPLOAD_DIR).resolve()
        if str(candidate).startswith(str(upload_root) + "/") and candidate.is_file():
            photo_path = candidate

    logo_path: Optional[Path] = None
    if profile.school_logo_url:
        candidate = (Path(settings.UPLOAD_DIR) / profile.school_logo_url).resolve()
        upload_root = Path(settings.UPLOAD_DIR).resolve()
        if str(candidate).startswith(str(upload_root) + "/") and candidate.is_file():
            logo_path = candidate

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _draw_card(c, profile=profile, photo_path=photo_path, logo_path=logo_path)
    c.showPage()
    c.save()
    target.write_bytes(buf.getvalue())
    return target
