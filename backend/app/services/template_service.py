"""
Loads and renders response templates.
Templates live in app/templates/ as .txt files with {placeholder} variables.
"""
import os
from pathlib import Path
from app.models.dsar_request import DSARRequest, RequestType

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

TEMPLATE_MAP = {
    RequestType.ACCESS: "access_response",
    RequestType.DELETION: "deletion_response",
    RequestType.MODIFICATION: "modification_response",
    RequestType.STOP_PROCESSING: "stop_processing_response",
}


def _load(name: str) -> str:
    path = TEMPLATE_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {name}")
    return path.read_text(encoding="utf-8")


def render(template_name: str, context: dict) -> str:
    raw = _load(template_name)
    for key, value in context.items():
        raw = raw.replace(f"{{{key}}}", str(value) if value else "")
    return raw


def get_response_template(request: DSARRequest, lookup_result: dict | None = None) -> str:
    template_name = TEMPLATE_MAP.get(request.request_type, "acknowledgement")
    context = {
        "subject_name": request.subject_full_name,
        "reference": request.reference,
        "request_type": request.request_type.value.replace("_", " ").title(),
        "due_date": request.due_date.strftime("%d %B %Y") if request.due_date else "",
        "org_name": "DataVerse Solutions",
    }
    if lookup_result:
        context["data_found"] = "yes" if lookup_result.get("found") else "no"
    return render(template_name, context)


def get_acknowledgement(request: DSARRequest) -> str:
    return render("acknowledgement", {
        "subject_name": request.subject_full_name,
        "reference": request.reference,
        "request_type": request.request_type.value.replace("_", " ").title(),
        "due_date": request.due_date.strftime("%d %B %Y") if request.due_date else "",
        "org_name": "DataVerse Solutions",
    })


def get_rejection(request: DSARRequest, reason: str) -> str:
    return render("rejection_response", {
        "subject_name": request.subject_full_name,
        "reference": request.reference,
        "rejection_reason": reason,
        "org_name": "DataVerse Solutions",
    })
