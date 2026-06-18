import re
import sqlite3
from datetime import datetime, timedelta

REFERENCE_NOW = "2026-06-17T14:54:59.008-04:00"
DEMO_NOW = datetime.fromisoformat(REFERENCE_NOW)


def clean_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def at_offset(*, days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    return (DEMO_NOW - timedelta(days=days, hours=hours, minutes=minutes)).isoformat()


def build_seed_payload(base_url: str) -> dict[str, list[dict[str, object]]]:
    users = [
        {"id": "usr-001", "employee_number": "A1001", "full_name": "Mia Andersen", "email": "mia.andersen@autoliv.example", "title": "Support Analyst", "location": "Stockholm", "department": "IT Service Desk", "manager_name": "Lars Nyberg"},
        {"id": "usr-002", "employee_number": "A1002", "full_name": "Leo Bergstrom", "email": "leo.bergstrom@autoliv.example", "title": "Network Engineer", "location": "Gothenburg", "department": "Infrastructure", "manager_name": "Sofia Lind"},
        {"id": "usr-003", "employee_number": "A1003", "full_name": "Aisha Patel", "email": "aisha.patel@autoliv.example", "title": "Identity Engineer", "location": "Detroit", "department": "Identity and Access", "manager_name": "Marco Rossi"},
        {"id": "usr-004", "employee_number": "A1004", "full_name": "Jonas Eriksson", "email": "jonas.eriksson@autoliv.example", "title": "Data Platform Engineer", "location": "Bangalore", "department": "Data Platform", "manager_name": "Elena Popov"},
        {"id": "usr-005", "employee_number": "A1005", "full_name": "Priya Nair", "email": "priya.nair@autoliv.example", "title": "Collaboration Engineer", "location": "Chennai", "department": "Modern Workplace", "manager_name": "Marco Rossi"},
        {"id": "usr-006", "employee_number": "A1006", "full_name": "Noah Kim", "email": "noah.kim@autoliv.example", "title": "Warehouse Systems Analyst", "location": "Seoul", "department": "Operations IT", "manager_name": "Haruto Sato"},
        {"id": "usr-007", "employee_number": "A1007", "full_name": "Emilia Novak", "email": "emilia.novak@autoliv.example", "title": "Database Administrator", "location": "Prague", "department": "Database Services", "manager_name": "Elena Popov"},
        {"id": "usr-008", "employee_number": "A1008", "full_name": "Carlos Mendes", "email": "carlos.mendes@autoliv.example", "title": "Endpoint Engineer", "location": "Mexico City", "department": "Endpoint Management", "manager_name": "Sofia Lind"},
        {"id": "usr-009", "employee_number": "A1009", "full_name": "Sara Holm", "email": "sara.holm@autoliv.example", "title": "Plant IT Lead", "location": "Linkoping", "department": "Manufacturing IT", "manager_name": "Haruto Sato"},
        {"id": "usr-010", "employee_number": "A1010", "full_name": "Daniel Ortiz", "email": "daniel.ortiz@autoliv.example", "title": "BI Analyst", "location": "Monterrey", "department": "Business Intelligence", "manager_name": "Elena Popov"},
        {"id": "usr-011", "employee_number": "A1011", "full_name": "Hana Sato", "email": "hana.sato@autoliv.example", "title": "Service Desk Lead", "location": "Tokyo", "department": "IT Service Desk", "manager_name": "Lars Nyberg"},
        {"id": "usr-012", "employee_number": "A1012", "full_name": "Owen Walker", "email": "owen.walker@autoliv.example", "title": "Operations Supervisor", "location": "Auburn Hills", "department": "Plant Operations", "manager_name": "Haruto Sato"},
    ]

    assignment_groups = [
        {"id": "grp-network-ops", "name": "Network Operations", "description": "Owns VPN, remote access, and WAN incidents.", "escalation_email": "network-ops@autoliv.example"},
        {"id": "grp-identity-access", "name": "Identity and Access", "description": "Handles SSO, MFA, and entitlement issues.", "escalation_email": "identity-access@autoliv.example"},
        {"id": "grp-data-platform", "name": "Data Platform", "description": "Supports reporting, pipelines, and SQL platform issues.", "escalation_email": "data-platform@autoliv.example"},
        {"id": "grp-modern-workplace", "name": "Modern Workplace", "description": "Handles collaboration and messaging workloads.", "escalation_email": "modern-workplace@autoliv.example"},
        {"id": "grp-operations-it", "name": "Operations IT", "description": "Supports warehouse scanners, printers, and plant systems.", "escalation_email": "operations-it@autoliv.example"},
        {"id": "grp-endpoint-engineering", "name": "Endpoint Engineering", "description": "Owns device enrollment, configuration, and compliance.", "escalation_email": "endpoint-engineering@autoliv.example"},
    ]

    categories = [
        {"id": "cat-network-vpn", "name": "Network", "subcategory": "VPN"},
        {"id": "cat-identity-sso", "name": "Identity", "subcategory": "SSO"},
        {"id": "cat-data-reporting", "name": "Data Platform", "subcategory": "Reporting"},
        {"id": "cat-collaboration-mailbox", "name": "Collaboration", "subcategory": "Shared Mailbox"},
        {"id": "cat-operations-scanner", "name": "Operations", "subcategory": "Scanner"},
        {"id": "cat-database-sql", "name": "Database", "subcategory": "SQL Performance"},
        {"id": "cat-operations-print", "name": "Operations", "subcategory": "Label Printing"},
        {"id": "cat-endpoint-enrollment", "name": "Endpoint", "subcategory": "Device Enrollment"},
    ]

    kb_templates = [
        {
            "id": "kb-001",
            "number": "KB001001",
            "title": "Reset stale VPN certificates after password rotation",
            "category_id": "cat-network-vpn",
            "audience": "IT Support",
            "content_html": "<h1>VPN certificate repair</h1><p>Open the device certificate store, remove the stale certificate, and force a new registration before restarting the VPN agent.</p><ol><li>Clear cached credentials.</li><li>Sync the device certificate.</li><li>Validate MFA on reconnect.</li></ol>",
            "keywords": "vpn,certificate,mfa,remote access",
            "published_at": at_offset(days=45),
            "updated_at": at_offset(days=3),
        },
        {
            "id": "kb-002",
            "number": "KB001002",
            "title": "Fix browser SSO loops caused by stale tokens",
            "category_id": "cat-identity-sso",
            "audience": "IT Support",
            "content_html": "<h1>SSO loop recovery</h1><p>Sign out of the browser profile, remove cached identity tokens, and refresh the conditional access session from the device settings page.</p><p>Confirm the Entra session is rebuilt before retesting.</p>",
            "keywords": "sso,entra,token,browser",
            "published_at": at_offset(days=38),
            "updated_at": at_offset(days=5),
        },
        {
            "id": "kb-003",
            "number": "KB001003",
            "title": "Recover delayed Fabric and Power BI refresh jobs",
            "category_id": "cat-data-reporting",
            "audience": "Data Engineers",
            "content_html": "<h1>Reporting delay triage</h1><p>Check the ingestion queue depth, confirm gateway health, and rerun the Lakehouse refresh after stale compute sessions are cleared.</p><ul><li>Validate dataset credentials.</li><li>Restart the scheduled pipeline.</li></ul>",
            "keywords": "fabric,power bi,refresh,gateway",
            "published_at": at_offset(days=34),
            "updated_at": at_offset(days=2),
        },
        {
            "id": "kb-004",
            "number": "KB001004",
            "title": "Restore shared mailbox permissions after sync drift",
            "category_id": "cat-collaboration-mailbox",
            "audience": "Messaging Support",
            "content_html": "<h1>Shared mailbox repair</h1><p>Reapply full access and send-as permissions, trigger directory sync, and confirm Outlook auto-mapping after the mailbox cache refresh completes.</p>",
            "keywords": "mailbox,outlook,permissions,sync",
            "published_at": at_offset(days=29),
            "updated_at": at_offset(days=4),
        },
        {
            "id": "kb-005",
            "number": "KB001005",
            "title": "Stabilize handheld scanner queue latency in warehouse lanes",
            "category_id": "cat-operations-scanner",
            "audience": "Operations IT",
            "content_html": "<h1>Scanner latency playbook</h1><p>Restart the queue service on the lane controller, clear orphaned scan sessions, and validate barcode round-trip latency from the diagnostics screen.</p>",
            "keywords": "scanner,warehouse,latency,queue",
            "published_at": at_offset(days=26),
            "updated_at": at_offset(days=6),
        },
        {
            "id": "kb-006",
            "number": "KB001006",
            "title": "Resolve SQL timeout spikes after ETL contention",
            "category_id": "cat-database-sql",
            "audience": "Database Services",
            "content_html": "<h1>SQL timeout response</h1><p>Identify blocking ETL sessions, rebuild the affected index, and validate the report stored procedure with the reduced timeout window.</p>",
            "keywords": "sql,timeout,index,etl",
            "published_at": at_offset(days=21),
            "updated_at": at_offset(days=1),
        },
        {
            "id": "kb-007",
            "number": "KB001007",
            "title": "Repair Zebra label print spooler failures after patching",
            "category_id": "cat-operations-print",
            "audience": "Operations IT",
            "content_html": "<h1>Label print recovery</h1><p>Clear the print spooler backlog, reinstall the Zebra driver package, and replay one validated label job before reopening the production queue.</p>",
            "keywords": "printer,label,zebra,spooler",
            "published_at": at_offset(days=18),
            "updated_at": at_offset(days=7),
        },
        {
            "id": "kb-008",
            "number": "KB001008",
            "title": "Recover Intune enrollment after device record drift",
            "category_id": "cat-endpoint-enrollment",
            "audience": "Endpoint Engineering",
            "content_html": "<h1>Enrollment recovery</h1><p>Retire the duplicate device object, start a fresh Company Portal enrollment, and confirm compliance policy sync before user sign-in.</p>",
            "keywords": "intune,enrollment,company portal,compliance",
            "published_at": at_offset(days=16),
            "updated_at": at_offset(days=2),
        },
    ]

    kb_articles = []
    for article in kb_templates:
        kb_articles.append(
            {
                **article,
                "content_text": clean_html(article["content_html"]),
            }
        )

    change_requests = [
        {"id": "chg-001", "number": "CHG001001", "title": "Rotate VPN client certificate trust chain", "state": "Implemented", "risk": "Medium", "planned_start": at_offset(days=15, hours=6), "planned_end": at_offset(days=15, hours=2), "implemented_at": at_offset(days=15, hours=1)},
        {"id": "chg-002", "number": "CHG001002", "title": "Refresh browser SSO token handling policy", "state": "Review", "risk": "Low", "planned_start": at_offset(days=11, hours=4), "planned_end": at_offset(days=11), "implemented_at": None},
        {"id": "chg-003", "number": "CHG001003", "title": "Tune reporting gateway concurrency limits", "state": "Implemented", "risk": "Medium", "planned_start": at_offset(days=9, hours=8), "planned_end": at_offset(days=9, hours=2), "implemented_at": at_offset(days=9, hours=1)},
        {"id": "chg-004", "number": "CHG001004", "title": "Repair warehouse scanner queue service", "state": "Implemented", "risk": "High", "planned_start": at_offset(days=8, hours=7), "planned_end": at_offset(days=8, hours=3), "implemented_at": at_offset(days=8, hours=2)},
        {"id": "chg-005", "number": "CHG001005", "title": "Rebuild reporting indexes after ETL window", "state": "Implemented", "risk": "High", "planned_start": at_offset(days=6, hours=9), "planned_end": at_offset(days=6, hours=2), "implemented_at": at_offset(days=6, hours=1)},
        {"id": "chg-006", "number": "CHG001006", "title": "Roll forward Zebra print driver patch", "state": "Scheduled", "risk": "Medium", "planned_start": at_offset(days=2, hours=5), "planned_end": at_offset(days=2, hours=1), "implemented_at": None},
        {"id": "chg-007", "number": "CHG001007", "title": "Clean duplicate Intune device registrations", "state": "Implemented", "risk": "Low", "planned_start": at_offset(days=4, hours=6), "planned_end": at_offset(days=4, hours=2), "implemented_at": at_offset(days=4, hours=1)},
    ]

    scenarios = [
        {
            "slug": "vpn-cert-loop",
            "sites": ["Stockholm", "Gothenburg", "Detroit", "Linkoping"],
            "category_id": "cat-network-vpn",
            "assignment_group_id": "grp-network-ops",
            "kb_article_id": "kb-001",
            "change_request_id": "chg-001",
            "assignee_id": "usr-002",
            "summary_template": "VPN reconnect loop after password rotation in {site}",
            "description_template": "<p>Remote users in <strong>{site}</strong> report repeated VPN prompts after a password change.</p><ul><li>MFA succeeds.</li><li>The tunnel disconnects after fifteen seconds.</li><li>Device certificate shows an older thumbprint.</li></ul>",
            "resolution_html": "<p>Cleared cached credentials, re-registered the device certificate, and restarted the VPN agent service.</p>",
            "follow_up_reason": "Confirm the renewed certificate remains trusted through the next credential sync window.",
            "impact": "High",
            "urgency": "High",
            "reference_type": "monitoring",
            "reference_title": "Entra sign-in trace",
            "source_system": "Entra ID",
            "attachment_name": "vpn-debug.log",
            "attachment_type": "text/plain",
            "attachment_size": 248,
            "attachment_description": "VPN debug log showing repeated reconnect attempts.",
            "image_name": "vpn-login-loop.png",
            "image_type": "image/png",
            "image_width": 1280,
            "image_height": 720,
            "image_description": "Screenshot of repeated MFA prompts in the VPN client.",
            "document_name": "vpn-recovery-steps.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 384,
            "document_description": "Engineer handoff checklist for certificate recovery.",
        },
        {
            "slug": "sso-browser-loop",
            "sites": ["Detroit", "Monterrey", "Prague", "Tokyo"],
            "category_id": "cat-identity-sso",
            "assignment_group_id": "grp-identity-access",
            "kb_article_id": "kb-002",
            "change_request_id": "chg-002",
            "assignee_id": "usr-003",
            "summary_template": "Browser SSO loop blocks supplier portal access in {site}",
            "description_template": "<p>Users in <strong>{site}</strong> get redirected to sign-in repeatedly when opening the supplier portal.</p><ul><li>Conditional access succeeds.</li><li>Token refresh fails inside the browser profile.</li><li>Private window login works once.</li></ul>",
            "resolution_html": "<p>Signed out of the browser profile, removed stale tokens, and rebuilt the Entra session from device settings.</p>",
            "follow_up_reason": "Need confirmation from the requester after the browser profile completes its overnight sync.",
            "impact": "Medium",
            "urgency": "High",
            "reference_type": "identity",
            "reference_title": "Conditional access evaluation",
            "source_system": "Entra ID",
            "attachment_name": "sso-token-trace.har",
            "attachment_type": "application/json",
            "attachment_size": 164,
            "attachment_description": "Browser trace exported during the SSO redirect loop.",
            "image_name": "sso-loop-screenshot.png",
            "image_type": "image/png",
            "image_width": 1366,
            "image_height": 768,
            "image_description": "Portal screenshot showing the repeated sign-in redirect.",
            "document_name": "sso-browser-repair.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 276,
            "document_description": "Step-by-step browser token cleanup guide.",
        },
        {
            "slug": "fabric-refresh-delay",
            "sites": ["Bangalore", "Prague", "Monterrey", "Stockholm"],
            "category_id": "cat-data-reporting",
            "assignment_group_id": "grp-data-platform",
            "kb_article_id": "kb-003",
            "change_request_id": "chg-003",
            "assignee_id": "usr-004",
            "summary_template": "Fabric refresh backlog delays reporting dataset in {site}",
            "description_template": "<p>The reporting workspace tied to <strong>{site}</strong> is serving stale metrics.</p><ul><li>Gateway queue depth is elevated.</li><li>Scheduled refresh is timing out.</li><li>Lakehouse ingestion finished later than expected.</li></ul>",
            "resolution_html": "<p>Cleared stale compute sessions, restarted the gateway worker, and reran the refresh pipeline.</p>",
            "follow_up_reason": "Open until the next scheduled refresh completes inside the business window.",
            "impact": "High",
            "urgency": "Medium",
            "reference_type": "workspace",
            "reference_title": "Fabric pipeline run",
            "source_system": "Microsoft Fabric",
            "attachment_name": "refresh-execution-log.txt",
            "attachment_type": "text/plain",
            "attachment_size": 198,
            "attachment_description": "Gateway and refresh execution log snippet.",
            "image_name": "fabric-refresh-history.png",
            "image_type": "image/png",
            "image_width": 1440,
            "image_height": 900,
            "image_description": "Refresh history view showing delayed jobs.",
            "document_name": "reporting-recovery-checklist.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 412,
            "document_description": "Recovery checklist for reporting refresh incidents.",
        },
        {
            "slug": "shared-mailbox-drift",
            "sites": ["Stockholm", "Detroit", "Auburn Hills", "Chennai"],
            "category_id": "cat-collaboration-mailbox",
            "assignment_group_id": "grp-modern-workplace",
            "kb_article_id": "kb-004",
            "change_request_id": "chg-002",
            "assignee_id": "usr-005",
            "summary_template": "Shared mailbox permissions missing for shift lead in {site}",
            "description_template": "<p>The operations mailbox in <strong>{site}</strong> no longer auto-maps for the shift lead.</p><ul><li>Outlook reports the folder cannot be expanded.</li><li>Send-as fails.</li><li>Recent group membership change was completed earlier in the day.</li></ul>",
            "resolution_html": "<p>Reapplied mailbox permissions, forced directory sync, and refreshed the Outlook profile cache.</p>",
            "follow_up_reason": "Waiting for the next shift lead to confirm send-as behavior from Outlook desktop and web.",
            "impact": "Medium",
            "urgency": "Medium",
            "reference_type": "collaboration",
            "reference_title": "Mailbox permission audit",
            "source_system": "Exchange Online",
            "attachment_name": "mailbox-audit.csv",
            "attachment_type": "text/csv",
            "attachment_size": 92,
            "attachment_description": "Permission audit extract captured during triage.",
            "image_name": "mailbox-error.png",
            "image_type": "image/png",
            "image_width": 1100,
            "image_height": 780,
            "image_description": "Outlook screenshot showing the mailbox folder error.",
            "document_name": "mailbox-permission-repair.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 301,
            "document_description": "Support runbook for mailbox permission recovery.",
        },
        {
            "slug": "scanner-latency",
            "sites": ["Auburn Hills", "Monterrey", "Seoul", "Linkoping"],
            "category_id": "cat-operations-scanner",
            "assignment_group_id": "grp-operations-it",
            "kb_article_id": "kb-005",
            "change_request_id": "chg-004",
            "assignee_id": "usr-006",
            "summary_template": "Warehouse scanner queue latency spikes on lane controller in {site}",
            "description_template": "<p>Handheld scanners in <strong>{site}</strong> are taking more than thirty seconds to acknowledge scans.</p><ul><li>Users can reconnect after a delay.</li><li>Lane controller CPU spikes during wave picking.</li><li>Queue depth remains elevated.</li></ul>",
            "resolution_html": "<p>Restarted the queue service, cleared orphaned sessions, and validated sub-second barcode round-trip times.</p>",
            "follow_up_reason": "Keeping the ticket open until the next picking wave confirms lane controller stability.",
            "impact": "High",
            "urgency": "High",
            "reference_type": "operations",
            "reference_title": "Lane controller diagnostics",
            "source_system": "Warehouse Management",
            "attachment_name": "scanner-queue.log",
            "attachment_type": "text/plain",
            "attachment_size": 257,
            "attachment_description": "Queue service log captured from the lane controller.",
            "image_name": "scanner-latency-dashboard.png",
            "image_type": "image/png",
            "image_width": 1600,
            "image_height": 900,
            "image_description": "Dashboard view showing lane controller latency spikes.",
            "document_name": "scanner-lane-runbook.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 355,
            "document_description": "Warehouse lane service restart runbook.",
        },
        {
            "slug": "sql-timeout",
            "sites": ["Prague", "Bangalore", "Detroit", "Monterrey"],
            "category_id": "cat-database-sql",
            "assignment_group_id": "grp-data-platform",
            "kb_article_id": "kb-006",
            "change_request_id": "chg-005",
            "assignee_id": "usr-007",
            "summary_template": "SQL timeout blocks operational report generation in {site}",
            "description_template": "<p>Operational reporting in <strong>{site}</strong> is timing out during the shift change summary.</p><ul><li>The stored procedure exceeds the timeout window.</li><li>Blocking ETL sessions are visible.</li><li>Index fragmentation is above threshold.</li></ul>",
            "resolution_html": "<p>Stopped the blocking ETL session, rebuilt the affected index, and reran the reporting stored procedure.</p>",
            "follow_up_reason": "Need one more successful reporting cycle after the ETL maintenance window to close confidently.",
            "impact": "High",
            "urgency": "High",
            "reference_type": "database",
            "reference_title": "Query Store snapshot",
            "source_system": "SQL Server",
            "attachment_name": "report-timeout.sql",
            "attachment_type": "application/sql",
            "attachment_size": 76,
            "attachment_description": "Captured SQL statements used to reproduce the timeout.",
            "image_name": "query-store-top-waits.png",
            "image_type": "image/png",
            "image_width": 1500,
            "image_height": 820,
            "image_description": "Query Store screenshot highlighting wait categories.",
            "document_name": "sql-timeout-mitigation.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 337,
            "document_description": "Mitigation checklist for recurring report timeouts.",
        },
        {
            "slug": "label-print-spooler",
            "sites": ["Linkoping", "Auburn Hills", "Seoul", "Detroit"],
            "category_id": "cat-operations-print",
            "assignment_group_id": "grp-operations-it",
            "kb_article_id": "kb-007",
            "change_request_id": "chg-006",
            "assignee_id": "usr-006",
            "summary_template": "Zebra label print spooler backlog blocks shipping labels in {site}",
            "description_template": "<p>Shipping labels in <strong>{site}</strong> are queued but not printed.</p><ul><li>Spooler backlog keeps growing.</li><li>The Zebra driver was patched recently.</li><li>Manual test prints remain stuck.</li></ul>",
            "resolution_html": "<p>Cleared the spooler backlog, reinstalled the Zebra driver, and replayed a validated label job.</p>",
            "follow_up_reason": "Open until the post-patch driver package is approved for all packaging stations.",
            "impact": "High",
            "urgency": "Medium",
            "reference_type": "operations",
            "reference_title": "Packaging station print audit",
            "source_system": "Print Server",
            "attachment_name": "zebra-driver-report.txt",
            "attachment_type": "text/plain",
            "attachment_size": 121,
            "attachment_description": "Driver package and spooler status capture.",
            "image_name": "zebra-print-queue.png",
            "image_type": "image/png",
            "image_width": 1280,
            "image_height": 800,
            "image_description": "Print queue snapshot showing blocked label jobs.",
            "document_name": "zebra-driver-redeployment.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 289,
            "document_description": "Driver redeployment plan for packaging stations.",
        },
        {
            "slug": "intune-enrollment-drift",
            "sites": ["Chennai", "Detroit", "Gothenburg", "Prague"],
            "category_id": "cat-endpoint-enrollment",
            "assignment_group_id": "grp-endpoint-engineering",
            "kb_article_id": "kb-008",
            "change_request_id": "chg-007",
            "assignee_id": "usr-008",
            "summary_template": "Intune enrollment fails after duplicate device record in {site}",
            "description_template": "<p>Devices in <strong>{site}</strong> fail Company Portal enrollment after hardware refresh.</p><ul><li>Compliance state stays pending.</li><li>A duplicate device object exists.</li><li>Users cannot receive VPN and mail profiles.</li></ul>",
            "resolution_html": "<p>Retired the duplicate device object, started a fresh Company Portal enrollment, and confirmed compliance sync.</p>",
            "follow_up_reason": "Need the user to confirm policy delivery after the next device check-in window.",
            "impact": "Medium",
            "urgency": "Medium",
            "reference_type": "endpoint",
            "reference_title": "Intune device audit",
            "source_system": "Microsoft Intune",
            "attachment_name": "device-enrollment.json",
            "attachment_type": "application/json",
            "attachment_size": 88,
            "attachment_description": "Enrollment audit details exported from the device record.",
            "image_name": "company-portal-error.png",
            "image_type": "image/png",
            "image_width": 1170,
            "image_height": 760,
            "image_description": "Company Portal screenshot showing enrollment failure.",
            "document_name": "intune-reenrollment-guide.docx",
            "document_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document_size": 245,
            "document_description": "Field guide for device reenrollment and compliance validation.",
        },
    ]

    requesters = ["usr-001", "usr-009", "usr-010", "usr-011", "usr-012"]
    priorities = ["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"]

    incidents: list[dict[str, object]] = []
    work_notes: list[dict[str, object]] = []
    resolution_notes: list[dict[str, object]] = []
    incident_change_links: list[dict[str, object]] = []
    slas: list[dict[str, object]] = []
    attachments: list[dict[str, object]] = []
    images: list[dict[str, object]] = []
    documents: list[dict[str, object]] = []
    external_references: list[dict[str, object]] = []
    incident_kb_links: list[dict[str, object]] = []

    for scenario_index, scenario in enumerate(scenarios):
        for ticket_index, site in enumerate(scenario["sites"]):
            sequence = (scenario_index * 4) + ticket_index + 1
            incident_id = f"inc-{sequence:03d}"
            incident_number = f"INC{1000 + sequence:07d}"
            opened_at = at_offset(days=(scenario_index * 3) + ticket_index + 2, hours=8 - ticket_index)
            updated_at = at_offset(days=(scenario_index * 2) + ticket_index, hours=2 + ticket_index)

            if ticket_index == 0:
                state = "Resolved"
                resolved_at = at_offset(days=(scenario_index * 2) + ticket_index, hours=1)
                follow_up_required = 0
            elif ticket_index == 1:
                state = "Closed"
                resolved_at = at_offset(days=(scenario_index * 2) + ticket_index, hours=3)
                follow_up_required = 0
            elif ticket_index == 2:
                state = "In Progress"
                resolved_at = None
                follow_up_required = 1
            else:
                state = "On Hold"
                resolved_at = None
                follow_up_required = 1

            summary = scenario["summary_template"].format(site=site)
            description_html = scenario["description_template"].format(site=site)
            resolution_html = scenario["resolution_html"]
            resolution_text = clean_html(resolution_html)
            priority = priorities[(scenario_index + ticket_index) % len(priorities)]
            requester_id = requesters[(sequence - 1) % len(requesters)]
            follow_up_reason = scenario["follow_up_reason"] if follow_up_required else None

            incidents.append(
                {
                    "id": incident_id,
                    "number": incident_number,
                    "short_description": summary,
                    "description_html": description_html,
                    "description_text": clean_html(description_html),
                    "state": state,
                    "priority": priority,
                    "category_id": scenario["category_id"],
                    "assignment_group_id": scenario["assignment_group_id"],
                    "requester_id": requester_id,
                    "assignee_id": scenario["assignee_id"],
                    "impact": scenario["impact"],
                    "urgency": scenario["urgency"],
                    "opened_at": opened_at,
                    "updated_at": updated_at,
                    "resolved_at": resolved_at,
                    "follow_up_required": follow_up_required,
                    "follow_up_reason": follow_up_reason,
                    "resolution_summary_html": resolution_html if resolved_at else None,
                    "resolution_summary_text": resolution_text if resolved_at else None,
                }
            )

            work_note_one_html = f"<p>Initial triage for <strong>{site}</strong> confirms recurring pattern aligned to the {scenario['slug']} scenario.</p>"
            work_note_two_html = (
                "<p>Requester asked for proactive follow-up after the next business cycle because the issue is still being monitored.</p>"
                if follow_up_required
                else "<p>Service recovered after applying the known fix from the linked knowledge article and validating with the requester.</p>"
            )
            work_notes.extend(
                [
                    {
                        "id": f"wn-{sequence:03d}-1",
                        "incident_id": incident_id,
                        "author_id": scenario["assignee_id"],
                        "note_html": work_note_one_html,
                        "note_text": clean_html(work_note_one_html),
                        "created_at": at_offset(days=(scenario_index * 2) + ticket_index + 1, hours=6),
                    },
                    {
                        "id": f"wn-{sequence:03d}-2",
                        "incident_id": incident_id,
                        "author_id": "usr-011",
                        "note_html": work_note_two_html,
                        "note_text": clean_html(work_note_two_html),
                        "created_at": at_offset(days=(scenario_index * 2) + ticket_index, hours=5),
                    },
                ]
            )

            if resolved_at:
                resolution_note_html = f"<p>Resolution for <strong>{site}</strong>: {resolution_text}</p>"
                resolution_notes.append(
                    {
                        "id": f"rn-{sequence:03d}",
                        "incident_id": incident_id,
                        "author_id": scenario["assignee_id"],
                        "note_html": resolution_note_html,
                        "note_text": clean_html(resolution_note_html),
                        "created_at": resolved_at,
                    }
                )

            incident_change_links.append(
                {
                    "id": f"icl-{sequence:03d}",
                    "incident_id": incident_id,
                    "change_request_id": scenario["change_request_id"],
                    "relationship_type": "related_fix" if resolved_at else "candidate_fix",
                }
            )

            response_target = 2.0 if priority == "1 - Critical" else 4.0
            resolution_target = 8.0 if priority == "1 - Critical" else 24.0 if priority == "2 - High" else 48.0
            response_elapsed = 1.2 + (ticket_index * 0.6)
            resolution_elapsed = 6.0 + scenario_index + (ticket_index * 4.5)
            resolution_breached = int(bool(resolved_at and resolution_elapsed > resolution_target))

            slas.extend(
                [
                    {
                        "id": f"sla-{sequence:03d}-1",
                        "incident_id": incident_id,
                        "name": "Response SLA",
                        "stage": "Achieved",
                        "target_hours": response_target,
                        "elapsed_hours": response_elapsed,
                        "breached": 0,
                    },
                    {
                        "id": f"sla-{sequence:03d}-2",
                        "incident_id": incident_id,
                        "name": "Resolution SLA",
                        "stage": "In Progress" if not resolved_at else ("Breached" if resolution_breached else "Achieved"),
                        "target_hours": resolution_target,
                        "elapsed_hours": resolution_elapsed,
                        "breached": resolution_breached,
                    },
                ]
            )

            attachment_slug = scenario["attachment_name"].replace(".", f"-{sequence}.")
            image_slug = scenario["image_name"].replace(".", f"-{sequence}.")
            document_slug = scenario["document_name"].replace(".", f"-{sequence}.")

            attachments.append(
                {
                    "id": f"att-{sequence:03d}",
                    "incident_id": incident_id,
                    "file_name": attachment_slug,
                    "content_type": scenario["attachment_type"],
                    "file_size_kb": scenario["attachment_size"] + ticket_index,
                    "description": scenario["attachment_description"],
                    "mock_url": f"{base_url}/mock/attachments/{incident_id}/{attachment_slug}",
                    "uploaded_at": at_offset(days=(scenario_index * 2) + ticket_index, hours=4),
                }
            )
            images.append(
                {
                    "id": f"img-{sequence:03d}",
                    "incident_id": incident_id,
                    "file_name": image_slug,
                    "content_type": scenario["image_type"],
                    "width_px": scenario["image_width"],
                    "height_px": scenario["image_height"],
                    "description": scenario["image_description"],
                    "mock_url": f"{base_url}/mock/images/{incident_id}/{image_slug}",
                    "uploaded_at": at_offset(days=(scenario_index * 2) + ticket_index, hours=4),
                }
            )
            documents.append(
                {
                    "id": f"doc-{sequence:03d}",
                    "incident_id": incident_id,
                    "file_name": document_slug,
                    "content_type": scenario["document_type"],
                    "file_size_kb": scenario["document_size"] + ticket_index,
                    "description": scenario["document_description"],
                    "mock_url": f"{base_url}/mock/documents/{incident_id}/{document_slug}",
                    "uploaded_at": at_offset(days=(scenario_index * 2) + ticket_index, hours=3),
                }
            )
            external_references.append(
                {
                    "id": f"ref-{sequence:03d}",
                    "incident_id": incident_id,
                    "reference_type": scenario["reference_type"],
                    "title": f"{scenario['reference_title']} for {site}",
                    "url": f"{base_url}/mock/references/{scenario['slug']}/{site.lower().replace(' ', '-')}",
                    "source_system": scenario["source_system"],
                }
            )
            incident_kb_links.append(
                {
                    "id": f"ikl-{sequence:03d}",
                    "incident_id": incident_id,
                    "kb_article_id": scenario["kb_article_id"],
                    "relevance_reason": f"Matched the same symptom cluster and recovery pattern seen in {site}.",
                }
            )

    return {
        "users": users,
        "assignment_groups": assignment_groups,
        "categories": categories,
        "kb_articles": kb_articles,
        "incidents": incidents,
        "work_notes": work_notes,
        "resolution_notes": resolution_notes,
        "change_requests": change_requests,
        "incident_change_links": incident_change_links,
        "slas": slas,
        "attachments": attachments,
        "images": images,
        "documents": documents,
        "external_references": external_references,
        "incident_kb_links": incident_kb_links,
    }


def seed_database(connection: sqlite3.Connection, base_url: str) -> None:
    payload = build_seed_payload(base_url)

    table_order = [
        "incident_kb_links",
        "external_references",
        "documents",
        "images",
        "attachments",
        "slas",
        "incident_change_links",
        "resolution_notes",
        "work_notes",
        "incidents",
        "change_requests",
        "kb_articles",
        "categories",
        "assignment_groups",
        "users",
    ]

    for table_name in table_order:
        connection.execute(f"DELETE FROM {table_name}")

    for table_name, rows in payload.items():
        if not rows:
            continue
        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        column_clause = ", ".join(columns)
        values = [tuple(row[column] for column in columns) for row in rows]
        connection.executemany(
            f"INSERT INTO {table_name} ({column_clause}) VALUES ({placeholders})",
            values,
        )
