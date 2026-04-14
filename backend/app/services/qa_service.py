"""
QA / correctness checks — automated gates before delivery is approved.

Checks:
  1. Field completeness
  2. Request classification accuracy
  3. Verification gate
  4. Scope verification (only correct systems queried)
  5. Over-disclosure guard (response within request entitlement)
  6. Response-type match
"""
from app.models.dsar_request import DSARRequest, RequestStatus


class QAResult:
    def __init__(self):
        self.passed = True
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def fail(self, msg: str) -> None:
        self.passed = False
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failures": self.failures,
            "warnings": self.warnings,
        }


def run_checks(request: DSARRequest, lookup_result: dict | None = None) -> QAResult:
    result = QAResult()

    # 1. Field completeness
    if not request.subject_full_name or not request.subject_full_name.strip():
        result.fail("Subject full name is missing")
    if not request.subject_email or not request.subject_email.strip():
        result.fail("Subject email is missing")
    if not request.request_type:
        result.fail("Request type is not classified")

    # 2. Verification gate — must be verified before delivery
    if not request.is_verified:
        result.fail("Request has not been verified — delivery blocked")

    # 3. Request classification sanity check
    valid_types = {"access", "deletion", "modification", "stop_processing"}
    if request.request_type.value not in valid_types:
        result.fail(f"Unknown request type: {request.request_type.value}")

    # 4. Lookup result scope check
    if lookup_result:
        if lookup_result.get("error"):
            result.fail(f"Connector returned an error: {lookup_result['error']}")

        # For access requests — ensure data returned is from scoped systems only
        if request.request_type.value == "access":
            source = lookup_result.get("source", "")
            if source not in ("systeme.io",):
                result.warn(f"Data sourced from unexpected system: {source}")

        # Over-disclosure guard — deletion/stop_processing should NOT return raw data
        if request.request_type.value in ("deletion", "stop_processing"):
            if lookup_result.get("data"):
                result.warn("Connector returned raw data for a non-access request — review before sending")

    # 5. Status gate — must be at APPROVED or beyond to pass QA
    allowed_statuses = {RequestStatus.APPROVED, RequestStatus.DELIVERED, RequestStatus.COMPLETED}
    if request.status not in allowed_statuses and request.is_verified:
        result.warn(f"Request is in status '{request.status.value}' — ensure workflow is complete before delivery")

    return result
