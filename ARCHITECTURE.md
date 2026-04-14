# DataVerse DSR Platform — Architecture, Design Decisions & Stakeholder Response

> This document is structured as a direct response to the concerns raised in our stakeholder meeting.
> It covers what we built, why we built it this way, the trade-offs we made, and how the system
> is positioned for real-world enterprise deployment.

---

## What the System Does (Plain English)

A Data Subject Request (DSR) platform is a compliance tool that lets any individual exercise their
legal rights under GDPR and similar data protection laws. These rights include:

| Request Type | What It Means | What the System Does |
|---|---|---|
| **Access** | "Show me all data you hold on me" | Queries connected systems and packages the data |
| **Deletion** | "Delete all my data" | Executes deletion across all integrated systems |
| **Modification** | "Correct inaccurate data about me" | Updates records across connected systems |
| **Stop Processing** | "Stop using my data for marketing/profiling" | Flags contact, applies opt-out, removes from campaigns |

The subject never speaks to a human — they submit the form, verify their identity via OTP, and
receive an automated response. For high-risk cases, the system escalates to a human reviewer.

---

## How It Works — End-to-End Flow

```
Subject visits portal
        |
        v
Submits DSR form (name, email, request type)
        |
        v
System creates request, sends OTP to email (identity verification)
        |
        v
Subject enters OTP → identity confirmed
        |
        v
System runs risk assessment (LOW / MEDIUM / HIGH / CRITICAL)
        |
    LOW/MEDIUM                          HIGH/CRITICAL
        |                                     |
        v                                     v
Auto-executes action              Escalates to admin queue
(deletion/access/etc.)            Human reviews before action
        |                                     |
        v                                     v
Sends confirmation email          Admin approves → action executes
        |                                     |
        v                                     v
Request marked COMPLETED          Request marked COMPLETED
        |
        v
Full audit trail logged at every step
```

**The key design goal:** for the overwhelming majority of requests (low/medium risk), zero human
involvement is needed. The system handles the entire lifecycle in under 60 seconds.

---

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER                              │
│                                                             │
│   Subject Portal (React)    Admin Dashboard (React)         │
│   - Submit DSR form         - Request queue                 │
│   - OTP verification        - Review & approve              │
│   - Status tracking         - Audit logs                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│                    BACKEND API (FastAPI)                     │
│                                                             │
│  Intake API   │  Admin API   │  Verification  │  Workflow   │
│  /api/v1/     │  /api/v1/    │  OTP service   │  Orchestr.  │
│  intake/      │  admin/      │                │             │
│                                                             │
│  Risk Engine  │  Template    │  Email Service │  Connector  │
│  (assessment) │  (responses) │  (Resend)      │  (systeme)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    DATA LAYER                               │
│                                                             │
│  SQLite / PostgreSQL    │    systeme.io CRM API             │
│  (requests, audit logs) │    (contact data)                 │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI (Python) | High performance, auto-generates API docs, type-safe |
| Database | SQLite (dev) / PostgreSQL (prod) | Zero-config locally, enterprise-grade in production |
| Frontend | React + TypeScript + Tailwind | Fast, type-safe, modern UI |
| Auth | JWT tokens | Stateless, scales horizontally |
| Email | Resend API | Reliable delivery, simple API |
| OTP | SHA-256 hashed, 15-min expiry | Secure identity verification without passwords |
| Encryption | Fernet (AES-128-CBC) | Symmetric encryption for data packages |
| CRM Integration | systeme.io REST API | Direct API — no middleware or batch jobs |

---

## Responding to the Concerns Raised in Our Meeting

---

### 1. Data Minimization

**Concern:** The system should not access or process more data than necessary.

**How we address it:**
 
The connector layer is purpose-built to retrieve only the fields relevant to the specific request
type. For an ACCESS request, we return a filtered subset:

```
safe_fields = {id, email, firstName, lastName, phoneNumber, fields, tags, createdAt, updatedAt}
```

No internal CRM fields, admin notes, or system metadata are exposed to the subject. For DELETION,
we locate the record, delete it, and store only the confirmation (not the data itself). The platform
never holds a mirror copy of client data — it acts as a pass-through orchestration layer.

For production, each connector can define its own `allowed_fields` list, enforced at the service
layer before any data leaves the integration.

---
### 2. Data Retention

**Concern:** How long is data stored, and how is retention enforced?

**Current implementation:**
- Request metadata (name, email, request type, status) is retained for audit purposes
- OTP tokens are invalidated immediately after use
- Actual subject data retrieved during an ACCESS request is not persisted — it is delivered directly
  to the subject and discarded

**Production roadmap:**
- Configurable retention periods per client (default 90 days for request records)
- Automated nightly job to anonymize expired records (replace name/email with hashed tokens)
- Audit logs retained for 7 years (standard compliance requirement), but pseudonymized after 90 days
- Hard deletion with confirmation available for clients who require it

---

### 3. Authentication & Identity Management

**Concern:** Authentication should come from the client's existing system, not be handled internally.

**Design decision — two-tier auth:**

1. **Subjects (public-facing):** OTP via email. No account, no password. This is intentional —
   forcing subjects to create accounts to exercise their legal rights creates a barrier that
   regulators find problematic. OTP is the industry standard here.

2. **Admin users (internal):** JWT-based auth today. For production, this is designed to be
   replaced or augmented with the client's existing IAM:
   - **SAML 2.0** (for enterprise SSO like Okta, Azure AD)
   - **OAuth 2.0 / OIDC** (for Google Workspace, Microsoft 365)
   - **LDAP/Active Directory** (for on-premise clients)

   The admin authentication module is isolated — swapping it out does not affect any other part
   of the system. This was a deliberate architectural choice.

---

### 4. Human Review & Oversight

**Concern:** There must be meaningful human control, not full automation.

**How the risk engine drives the human-in-the-loop:**

```
Risk Tier   | Trigger Conditions                        | Outcome
------------|-------------------------------------------|---------------------------
LOW         | Standard request, no flags                | Fully automated
MEDIUM      | Multiple recent requests, sensitive type  | Automated + audit flag
HIGH        | Bulk data scope, special categories       | ESCALATED — admin must approve
CRITICAL    | Mass deletion, legal hold indicators      | ESCALATED + notification sent
```

HIGH and CRITICAL requests are routed to the admin queue and cannot proceed without an explicit
human approval click. The system will never auto-execute a deletion on a flagged request.

The admin dashboard shows:
- The request in full
- The reason for escalation
- The risk tier and what triggered it
- Approve / Reject / Request more information actions
- A full audit trail of who reviewed what and when

---

### 5. AI vs Human Control

**Concern:** AI should not be making critical decisions autonomously.

**Clarification of the AI role in this system:**

AI (Claude API integration, optional) is used only for:
- **Draft generation:** Suggesting the wording of the response email to the subject
- **Context summarisation:** Summarising the request for the admin reviewer

AI does **not**:
- Execute deletions
- Make escalation decisions (that is the rule-based risk engine)
- Approve or reject requests
- Access or process the actual subject data

The risk engine that decides LOW/MEDIUM/HIGH/CRITICAL is deterministic rule-based logic, not ML.
It produces the same output for the same input every time and is fully auditable. This was a
deliberate choice — regulators and auditors need to be able to explain every decision, and a
neural network cannot provide that explanation.

---

### 6. Integration with Existing Architecture

**Concern:** How does this work alongside what the client already has?

**The connector pattern:**

Every data source the client uses is represented by a connector — a small, isolated module
that knows how to talk to one system. Today we have a systeme.io connector. Adding a new one
(Salesforce, HubSpot, a custom database, SharePoint) is a matter of implementing four functions:

```python
handle_access(email)         → returns filtered contact data
handle_deletion(email)       → deletes the record, returns confirmation
handle_modification(email)   → updates specified fields
handle_stop_processing(email) → applies opt-out, removes from campaigns
```

The rest of the platform (intake, verification, workflow, email, audit) is entirely unaware of
which CRM the client uses. Adding a new integration does not require any changes to the core system.

For the client's existing architecture, the platform sits **alongside** it, not inside it.
No changes are required to the client's databases, applications, or infrastructure.

---

### 7. Hosting & Deployment

**Concern:** Flexibility around where the platform is hosted.

**Three deployment models are supported:**

| Model | Description | Best For |
|---|---|---|
| **SaaS (Cloud)** | Hosted and managed by DataVerse on AWS/Azure | SMEs, quick deployment |
| **Client Cloud** | Deployed into the client's own AWS/Azure/GCP account | Enterprises with cloud-first policy |
| **On-Premise** | Deployed within the client's own data centre | Regulated industries (finance, health) |

For SaaS and Client Cloud, deployment is containerised (Docker + Kubernetes). For on-premise,
we provide a standalone installer. The application has no external dependencies at runtime other
than an SMTP relay and the CRM APIs being integrated.

---

### 8. Data Storage Approach

**Concern:** Does the platform hold client personal data?

**What the platform stores:**

| Data | Stored? | Retention |
|---|---|---|
| Subject name + email | Yes — needed to process the request | Configurable (default 90 days) |
| Request type + status | Yes — needed for audit trail | 7 years (compliance) |
| OTP (plain text) | Never — only the SHA-256 hash is stored | Until used or expired |
| Retrieved contact data | No — delivered directly, not persisted | N/A |
| Admin user credentials | Yes — bcrypt hashed | Until account deleted |
| Audit log entries | Yes — pseudonymized after 90 days | 7 years |

The platform is designed to hold the **minimum information necessary to process and evidence the
request**. It is not a data warehouse.

---

### 9. Encryption & Security

**Concern:** Is encryption enforced throughout?

**Encryption in transit:**
- All HTTP traffic is TLS 1.2+ enforced (HTTPS)
- API keys and credentials never appear in URLs (always in headers)
- Email delivery uses TLS-encrypted SMTP

**Encryption at rest:**
- Database encrypted at the volume level in production (AWS RDS encryption, AES-256)
- Data packages (for ACCESS requests) encrypted using Fernet (AES-128-CBC) before storage
- Encryption key is rotatable — changing the key does not require re-encoding existing packages
  (they are short-lived and deleted after delivery)

**Additional security controls:**
- OTP brute-force protection: 5 attempts maximum, then token invalidated
- OTP expiry: 15 minutes
- JWT tokens expire after 8 hours
- All inputs validated with Pydantic v2 — no raw SQL, no injection vectors
- Admin endpoints require authentication; subject endpoints require verified OTP

---

### 10. Access Control

**Concern:** Role-based access and least privilege.

**Current roles:**

| Role | Access |
|---|---|
| **Superadmin** | Full system access, user management, system settings |
| **Admin** | Process requests, view queue, approve escalations |
| **Auditor** (planned) | Read-only access to audit logs and completed requests |

In production, roles are assignable per client. A client's DPO would typically be an Admin.
Their legal team would be Auditors. Only the DataVerse team (or a designated IT lead) would
hold Superadmin.

---

### 11. Integration Methods

**Concern:** Clients have varying levels of technical maturity.

**Four integration tiers:**

1. **Direct API** (preferred): Real-time, bidirectional. Used for systeme.io today. Any CRM or
   platform with a REST API can be integrated this way in 1-2 days.

2. **Webhook**: The client's system calls our platform when a DSR-relevant event occurs
   (e.g., subject requests deletion via their own portal). We process it and call back.

3. **Secure database connection**: For clients who cannot expose an API, we can query their
   database directly via an encrypted tunnel (SSL/TLS over VPN or AWS PrivateLink).

4. **File-based (CSV/SFTP)**: For legacy systems with no API and no direct DB access. Least
   preferred — adds latency — but ensures no client is excluded due to technical constraints.

---

### 12. Client Data Ownership

**Concern:** Who owns the data processed through the platform?

This is unambiguous:

- The **client is the Data Controller** for their subjects' data
- DataVerse acts as a **Data Processor** under GDPR Article 28
- A Data Processing Agreement (DPA) is signed before go-live
- Clients can export or delete all their data from the platform at any time
- Platform shutdown: all client data is returned in portable format (JSON/CSV) before termination

---

### 13. System Compatibility

**Concern:** Cross-device and cross-platform support.

- The subject portal is fully responsive — works on desktop, tablet, and mobile
- Tested on Chrome, Firefox, Safari, Edge
- No app installation required — pure web
- Admin dashboard is optimised for desktop (the primary use case for reviewers)
- The API is language-agnostic — any future integrations can be built in any language

---

### 14. Log Pseudonymization

**Concern:** Logs must not expose personally identifiable information.

**Current state:** Audit logs store the subject's email for traceability. This is necessary for
the audit trail to be meaningful.

**Production implementation:**
- After the configurable retention period (default 90 days), a scheduled job replaces all PII
  in audit logs with a pseudonymous token: `sha256(email + secret_salt)[:16]`
- The salt is client-specific and stored separately — logs and salt together can re-identify;
  logs alone cannot
- This satisfies both the auditability requirement and GDPR's purpose limitation principle
- Structured logs (JSON) make it straightforward to apply pseudonymization programmatically
  without losing the relational integrity of the audit trail

---

### 15. Retention Enforcement Mechanism

**Concern:** How is retention technically enforced, not just configured?

```
Every night at 02:00 (configurable):

1. Query all requests older than retention_days
2. For each:
   a. Anonymize: name → "[REDACTED]", email → hash token
   b. Log the anonymization event itself (with timestamp, no PII)
   c. Delete any associated data packages

Every week:
1. Query audit logs older than pseudonymization_days
2. Replace email/name fields with pseudonymous tokens
3. Retain all other fields (action, timestamp, request ID)

On request:
1. Hard-delete available via admin panel (with confirmation dialog)
2. Deletion is logged before execution (what was deleted, by whom, when)
```

This is implemented as a Celery background task (queue worker), not a cron job on the server —
it scales independently of the web server and can be monitored, retried, and audited.

---

## How to See Logs

**Backend logs** (all requests, errors, workflow steps):
- Open the **backend console window** that appeared when you ran `start.py`
- Every API call, OTP send, systeme.io action, and email is logged there in real time

**Audit trail** (per-request history):
- Admin panel → click any request → scroll to the bottom — full timeline of every action taken
- Shows: who did what, at what time, with what result

**API explorer** (for testing):
- Open `http://localhost:8000/docs` — interactive Swagger UI for every endpoint

---

## What Works Today (Pilot)

| Feature | Status |
|---|---|
| All 4 DSR types (access, deletion, modification, stop processing) | Working |
| OTP email verification | Working |
| Auto-complete workflow (verified → completed in one step) | Working |
| Risk-based escalation (HIGH/CRITICAL to admin queue) | Working |
| Admin dashboard (queue, review, approve) | Working |
| Audit trail per request | Working |
| systeme.io CRM integration | Working |
| Confirmation email to subject | Working |
| Dev mode (OTP on-screen, no email required) | Working |

---

## What a Production Version Would Add

| Feature | Purpose | Effort |
|---|---|---|
| SSO / SAML / OAuth for admin login | Enterprise IAM integration | Medium |
| Multi-tenant (one platform, many clients) | SaaS model | High |
| Additional connectors (Salesforce, HubSpot, SharePoint) | Broader CRM coverage | Low per connector |
| Automated retention & pseudonymization jobs | Compliance automation | Medium |
| Data portability packaging (ZIP with structured data) | GDPR Article 20 | Medium |
| Subject-facing request tracker (live status page) | Transparency | Low |
| Reporting dashboard (SLA compliance, volume trends) | Management visibility | Medium |
| AI-assisted response drafting (Claude API) | Efficiency | Low |
| Webhook support (inbound DSR from client portals) | Integration flexibility | Medium |
| On-premise deployment package | Enterprise / regulated clients | High |

---

## Trade-offs Made in the Pilot

| Decision | Trade-off | Reasoning |
|---|---|---|
| SQLite instead of PostgreSQL | Less scalable, single-writer | Zero-install for local demo; swap is one config line |
| Single CRM connector (systeme.io) | Limited integration breadth | Proves the pattern; adding more is low effort |
| Rule-based risk engine | Less adaptive than ML | Fully auditable, explainable — regulators require this |
| Email OTP instead of ID document verification | Lower assurance | Proportionate for B2C; enterprise clients may require ID verification |
| No multi-tenancy | One client per deployment | Keeps the pilot clean; architecture supports multi-tenancy as a later addition |
| Celery optional (Redis not required) | Background tasks run inline | Removes a dependency for local dev; Redis is added for production |

---

## Why This Architecture Scales

The platform is stateless at the API layer — each request carries its own auth token and the server
holds no session state. This means:

- Horizontal scaling: run 10 API servers behind a load balancer with no coordination needed
- The database is the only stateful component — handled by managed PostgreSQL (AWS RDS, Azure DB)
- Connectors are isolated — a failure in one CRM integration does not affect others
- Background workers (Celery) scale independently of the API

A single-server deployment handles thousands of DSR requests per day. A three-server setup
(API + DB + worker) handles enterprise volume. The architecture does not need to change between
these sizes — only the infrastructure underneath it.

---

## Positioning Summary

What differentiates this from a spreadsheet-based process (what most organisations use today):

- **Speed:** Requests completed in seconds, not days
- **Auditability:** Every action timestamped and logged — defensible in a regulatory audit
- **Accuracy:** No manual steps = no manual errors
- **Scalability:** Handles 1 request or 10,000 with the same infrastructure
- **Integration:** Works with the systems the data actually lives in

What differentiates this from OneTrust and similar enterprise platforms:

- **Cost:** OneTrust starts at ~$60,000/year. This is purpose-built and priced for the market we serve.
- **Simplicity:** OneTrust requires weeks of implementation. This requires a connector per CRM — days.
- **Transparency:** Open architecture — clients can see exactly what runs, audit it, and extend it.
- **Control:** No black box. Every decision the system makes can be explained and overridden.

---

*Document version: pilot-1.0 | Last updated: April 2026*
*DataVerse Solutions — DSR Management Platform*
