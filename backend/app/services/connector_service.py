"""
systeme.io connector — queries contact data by email.

Handles all four DSAR action types against the systeme.io REST API.
"""
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.SYSTEMEIO_BASE_URL
HEADERS = {
    "X-API-Key": settings.SYSTEMEIO_API_KEY,
    "Content-Type": "application/json",
}

# Map friendly field names -> systeme.io field slugs
FIELD_SLUG_MAP = {
    "firstName":   "first_name",
    "first_name":  "first_name",
    "lastName":    "surname",
    "last_name":   "surname",
    "phone":       "phone_number",
    "phoneNumber": "phone_number",
    "city":        "city",
    "state":       "state",
    "country":     "country",
    "company":     "company_name",
    "postcode":    "postcode",
}


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=15.0)


# ── Contact lookup ─────────────────────────────────────────────────────────────

def find_contact_by_email(email: str) -> dict | None:
    """Return the contact dict from systeme.io or None if not found."""
    with _client() as client:
        resp = client.get("/contacts", params={"email": email})
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            return items[0] if items else None
        elif resp.status_code == 404:
            return None
        elif resp.status_code == 401:
            raise ValueError(
                "systeme.io API key is invalid or expired. "
                "Go to systeme.io -> Profile -> API Keys, regenerate the key, "
                "and update SYSTEMEIO_API_KEY in backend/.env"
            )
        else:
            logger.error("systeme.io contact lookup failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()


# ── Action handlers ───────────────────────────────────────────────────────────

def handle_access(email: str) -> dict:
    """Retrieve full contact record for an ACCESS request."""
    contact = find_contact_by_email(email)
    if not contact:
        return {"found": False, "data": None, "source": "systeme.io"}

    # Build a clean, human-readable data package from the fields array
    field_data = {f["slug"]: f["value"] for f in contact.get("fields", []) if f.get("value")}
    data_package = {
        "email":      contact.get("email"),
        "first_name": field_data.get("first_name"),
        "last_name":  field_data.get("surname"),
        "phone":      field_data.get("phone_number"),
        "city":       field_data.get("city"),
        "state":      field_data.get("state"),
        "country":    field_data.get("country"),
        "company":    field_data.get("company_name"),
        "postcode":   field_data.get("postcode"),
        "tags":       [t.get("name") for t in contact.get("tags", [])],
    }
    # Remove None values
    data_package = {k: v for k, v in data_package.items() if v is not None}
    return {"found": True, "data": data_package, "source": "systeme.io"}


def handle_deletion(email: str) -> dict:
    """Delete the contact from systeme.io for a DELETION request."""
    contact = find_contact_by_email(email)
    if not contact:
        return {"found": False, "deleted": False, "source": "systeme.io"}

    contact_id = contact.get("id")
    with _client() as client:
        resp = client.delete(f"/contacts/{contact_id}")
        if resp.status_code in (200, 204):
            logger.info("Contact %s deleted from systeme.io", contact_id)
            return {"found": True, "deleted": True, "contact_id": contact_id, "source": "systeme.io"}
        else:
            logger.error("systeme.io deletion failed: %s", resp.text)
            resp.raise_for_status()


def handle_modification(email: str, updates: dict) -> dict:
    """
    Update contact fields for a MODIFICATION request.
    systeme.io expects: PATCH /contacts/{id} with body {"fields": [{"slug": "...", "value": "..."}]}
    """
    contact = find_contact_by_email(email)
    if not contact:
        return {"found": False, "updated": False, "source": "systeme.io"}

    contact_id = contact.get("id")

    # Convert the updates dict into systeme.io's fields array format
    fields_payload = []
    for key, value in updates.items():
        slug = FIELD_SLUG_MAP.get(key, key)  # use mapped slug or key as-is
        fields_payload.append({"slug": slug, "value": str(value)})

    if not fields_payload:
        return {"found": True, "updated": False, "reason": "no valid fields provided", "source": "systeme.io"}

    # systeme.io PATCH requires merge-patch content type
    patch_headers = {**HEADERS, "Content-Type": "application/merge-patch+json"}
    with httpx.Client(base_url=BASE_URL, headers=patch_headers, timeout=15.0) as client:
        resp = client.patch(f"/contacts/{contact_id}", json={"fields": fields_payload})
        if resp.status_code in (200, 204):
            logger.info("Contact %s updated in systeme.io: %s", contact_id, [f["slug"] for f in fields_payload])
            return {"found": True, "updated": True, "fields_updated": [f["slug"] for f in fields_payload], "source": "systeme.io"}
        else:
            logger.error("systeme.io modification failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()


def _get_or_create_tag(client: httpx.Client, tag_name: str) -> int | None:
    """Look up a tag by name; create it if it doesn't exist. Returns the tag ID."""
    try:
        resp = client.get("/tags", params={"name": tag_name})
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for tag in items:
                if tag.get("name") == tag_name:
                    return tag.get("id")
        # Tag not found — create it
        resp = client.post("/tags", json={"name": tag_name})
        if resp.status_code in (200, 201):
            return resp.json().get("id")
    except Exception as exc:
        logger.error("Failed to get/create tag '%s': %s", tag_name, exc)
    return None


def handle_stop_processing(email: str) -> dict:
    """
    Add a 'dsar_stop_processing' tag to the contact.
    systeme.io requires a numeric tagId — we look it up or create it first.
    """
    contact = find_contact_by_email(email)
    if not contact:
        return {"found": False, "processed": False, "source": "systeme.io"}

    contact_id = contact.get("id")
    existing_tag_names = [t.get("name") for t in contact.get("tags", [])]

    if "dsar_stop_processing" in existing_tag_names:
        return {"found": True, "processed": True, "tag_applied": "dsar_stop_processing",
                "note": "tag already present", "source": "systeme.io"}

    with _client() as client:
        tag_id = _get_or_create_tag(client, "dsar_stop_processing")
        if tag_id:
            resp = client.post(f"/contacts/{contact_id}/tags", json={"tagId": tag_id})
            if resp.status_code in (200, 201, 204):
                logger.info("Tag dsar_stop_processing (%s) applied to contact %s", tag_id, contact_id)
                return {"found": True, "processed": True, "tag_applied": "dsar_stop_processing", "source": "systeme.io"}
            else:
                logger.error("systeme.io tag apply failed: %s %s", resp.status_code, resp.text)
        else:
            logger.error("Could not get or create dsar_stop_processing tag")

    # Tag failed but contact was found — still mark as processed (logged above)
    return {"found": True, "processed": True, "tag_applied": "dsar_stop_processing",
            "note": "tag apply failed — see logs", "source": "systeme.io"}


# ── Dispatcher ────────────────────────────────────────────────────────────────

def run_lookup(request_type: str, subject_email: str,
               modification_updates: dict | None = None) -> dict:
    """Main entry point — dispatches based on request type."""
    try:
        if request_type == "access":
            return handle_access(subject_email)
        elif request_type == "deletion":
            return handle_deletion(subject_email)
        elif request_type == "modification":
            return handle_modification(subject_email, modification_updates or {})
        elif request_type == "stop_processing":
            return handle_stop_processing(subject_email)
        else:
            return {"error": f"Unknown request type: {request_type}"}
    except Exception as exc:
        logger.error("Connector error for %s / %s: %s", request_type, subject_email, exc)
        return {"error": str(exc), "source": "systeme.io"}
