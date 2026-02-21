"""Synthetic seed incidents for the knowledge base.

Provides 20 realistic-but-fake security incidents covering 9 attack types.
These form the baseline dataset before live Sentinel incidents are ingested.
"""

from datetime import UTC, datetime

# 20 synthetic incidents covering:
# phishing (3), brute force (3), malware/ransomware (3), suspicious sign-in (3),
# data exfiltration (2), privilege escalation (2), lateral movement (2),
# denial of service (1), credential theft (1)
SEED_INCIDENTS: list[dict] = [
    # --- Phishing (3) ---
    {
        "id": "synthetic-001",
        "title": "Phishing email with malicious attachment detected",
        "severity": "High",
        "status": "Closed",
        "description": (
            "A phishing email containing a weaponized Excel macro was delivered "
            "to multiple users in the finance department. The attachment was "
            "flagged by Defender for Office 365 after two users opened it."
        ),
        "mitre_techniques": "T1566,T1204",
        "entities": "user: jsmith@contoso.com, user: mgarcia@contoso.com, host: WS-FIN01",
        "source": "synthetic",
    },
    {
        "id": "synthetic-002",
        "title": "Credential harvesting phishing campaign targeting HR",
        "severity": "High",
        "status": "Active",
        "description": (
            "A coordinated phishing campaign using spoofed login pages was "
            "detected targeting HR personnel. The attacker registered a "
            "typosquatted domain contoso-hr-portal.com to harvest credentials."
        ),
        "mitre_techniques": "T1566,T1078",
        "entities": (
            "user: kpatel@contoso.com, user: lwong@contoso.com, "
            "domain: contoso-hr-portal.com"
        ),
        "source": "synthetic",
    },
    {
        "id": "synthetic-003",
        "title": "Spear phishing with PDF lure targeting executives",
        "severity": "Medium",
        "status": "Closed",
        "description": (
            "A targeted spear phishing email was sent to three C-level "
            "executives containing a malicious PDF that attempted to download "
            "a second-stage payload from a compromised WordPress site."
        ),
        "mitre_techniques": "T1566,T1204,T1059",
        "entities": "user: ceo@contoso.com, user: cfo@contoso.com, url: hxxps://compromised-wp[.]net/stage2",
        "source": "synthetic",
    },
    # --- Brute Force (3) ---
    {
        "id": "synthetic-004",
        "title": "Brute force attack against VPN gateway",
        "severity": "High",
        "status": "Closed",
        "description": (
            "Over 15,000 failed authentication attempts were detected against "
            "the corporate VPN gateway from a single IP address in Eastern "
            "Europe over a 4-hour window. No successful logins confirmed."
        ),
        "mitre_techniques": "T1110",
        "entities": "ip: 185.220.101.42, host: VPN-GW01",
        "source": "synthetic",
    },
    {
        "id": "synthetic-005",
        "title": "Password spray attack on Azure AD accounts",
        "severity": "Medium",
        "status": "Active",
        "description": (
            "A password spray attack was detected across 200+ Azure AD "
            "accounts using a small set of common passwords. The attack "
            "originated from a Tor exit node and targeted the sales department."
        ),
        "mitre_techniques": "T1110,T1078",
        "entities": "ip: 198.51.100.23, department: Sales",
        "source": "synthetic",
    },
    {
        "id": "synthetic-006",
        "title": "RDP brute force from known malicious IP range",
        "severity": "High",
        "status": "Closed",
        "description": (
            "Sustained RDP brute force attempts were detected against an "
            "internet-facing server from an IP range associated with a known "
            "botnet. NSG rules were updated to block the offending range."
        ),
        "mitre_techniques": "T1110,T1021",
        "entities": "ip: 203.0.113.0/24, host: SRV-WEB01",
        "source": "synthetic",
    },
    # --- Malware / Ransomware (3) ---
    {
        "id": "synthetic-007",
        "title": "Ransomware execution blocked on endpoint",
        "severity": "High",
        "status": "Closed",
        "description": (
            "Defender for Endpoint blocked a ransomware binary attempting to "
            "encrypt files on a workstation in the engineering department. "
            "The malware was delivered via a compromised USB drive."
        ),
        "mitre_techniques": "T1486,T1204",
        "entities": "user: rjones@contoso.com, host: WS-ENG05, file: encrypt0r.exe",
        "source": "synthetic",
    },
    {
        "id": "synthetic-008",
        "title": "Cobalt Strike beacon detected on domain controller",
        "severity": "High",
        "status": "Active",
        "description": (
            "Network telemetry detected Cobalt Strike C2 beacon traffic "
            "originating from a domain controller. The beacon was "
            "communicating with a known C2 infrastructure IP address."
        ),
        "mitre_techniques": "T1071,T1059",
        "entities": "host: DC01, ip: 192.0.2.100, process: rundll32.exe",
        "source": "synthetic",
    },
    {
        "id": "synthetic-009",
        "title": "Fileless malware using PowerShell detected",
        "severity": "Medium",
        "status": "Closed",
        "description": (
            "A fileless malware attack was detected where PowerShell was used "
            "to download and execute an in-memory payload. The script was "
            "obfuscated and attempted to disable Windows Defender."
        ),
        "mitre_techniques": "T1059,T1562",
        "entities": "user: alopez@contoso.com, host: WS-MKT03, process: powershell.exe",
        "source": "synthetic",
    },
    # --- Suspicious Sign-in (3) ---
    {
        "id": "synthetic-010",
        "title": "Impossible travel: sign-ins from two countries within 30 minutes",
        "severity": "Medium",
        "status": "Active",
        "description": (
            "A user account authenticated from New York and then from "
            "Singapore within 30 minutes, indicating either credential "
            "compromise or VPN/proxy usage. The Singapore sign-in used a "
            "previously unseen device."
        ),
        "mitre_techniques": "T1078",
        "entities": "user: tchen@contoso.com, ip: 203.0.113.45, ip: 198.51.100.12",
        "source": "synthetic",
    },
    {
        "id": "synthetic-011",
        "title": "Service account used interactively from unknown host",
        "severity": "High",
        "status": "New",
        "description": (
            "A service account normally restricted to automated processes "
            "was used for an interactive sign-in from an unregistered host. "
            "The account has elevated privileges on several file servers."
        ),
        "mitre_techniques": "T1078,T1134",
        "entities": "user: svc-backup@contoso.com, host: UNKNOWN-PC42",
        "source": "synthetic",
    },
    {
        "id": "synthetic-012",
        "title": "Multiple failed MFA challenges followed by successful login",
        "severity": "Medium",
        "status": "Closed",
        "description": (
            "An account experienced 12 failed MFA challenges in quick "
            "succession followed by a successful authentication, suggesting "
            "an MFA fatigue attack. The user confirmed they did not initiate "
            "most of the requests."
        ),
        "mitre_techniques": "T1078,T1110",
        "entities": "user: dbrown@contoso.com, ip: 100.64.0.15",
        "source": "synthetic",
    },
    # --- Data Exfiltration (2) ---
    {
        "id": "synthetic-013",
        "title": "Large data upload to personal cloud storage detected",
        "severity": "High",
        "status": "Active",
        "description": (
            "A user uploaded 4.2 GB of data to a personal Google Drive "
            "account during off-hours. The data included files from a "
            "restricted SharePoint site containing customer PII."
        ),
        "mitre_techniques": "T1567,T1005",
        "entities": "user: nwilson@contoso.com, host: WS-LEGAL02, destination: drive.google.com",
        "source": "synthetic",
    },
    {
        "id": "synthetic-014",
        "title": "Unusual outbound data transfer to external FTP server",
        "severity": "High",
        "status": "Closed",
        "description": (
            "Network monitoring detected a 2.8 GB data transfer from an "
            "internal database server to an external FTP server. The "
            "transfer occurred outside business hours using a compromised "
            "service account."
        ),
        "mitre_techniques": "T1041,T1005",
        "entities": "host: DB-PROD01, ip: 198.51.100.77, user: svc-etl@contoso.com",
        "source": "synthetic",
    },
    # --- Privilege Escalation (2) ---
    {
        "id": "synthetic-015",
        "title": "Unauthorized Global Admin role assignment in Azure AD",
        "severity": "High",
        "status": "Active",
        "description": (
            "A user account was granted the Global Administrator role in "
            "Azure AD without following the standard approval process. The "
            "role was assigned from a session originating from a VPN endpoint "
            "not registered in the corporate inventory."
        ),
        "mitre_techniques": "T1098,T1548",
        "entities": "user: mlee@contoso.com, role: Global Administrator",
        "source": "synthetic",
    },
    {
        "id": "synthetic-016",
        "title": "Scheduled task created with SYSTEM privileges on server",
        "severity": "Medium",
        "status": "Closed",
        "description": (
            "A scheduled task was created on a production server running "
            "with SYSTEM-level privileges. The task executes a script from "
            "a temp directory and was created by a standard user account."
        ),
        "mitre_techniques": "T1053,T1548",
        "entities": "user: jwhite@contoso.com, host: SRV-APP02, task: UpdateService",
        "source": "synthetic",
    },
    # --- Lateral Movement (2) ---
    {
        "id": "synthetic-017",
        "title": "PsExec lateral movement detected across file servers",
        "severity": "High",
        "status": "Closed",
        "description": (
            "PsExec was used to remotely execute commands on three file "
            "servers from a compromised workstation. The attacker used a "
            "domain admin account to move laterally and enumerate shares."
        ),
        "mitre_techniques": "T1021,T1570",
        "entities": "user: admin-ops@contoso.com, host: FS01, host: FS02, host: FS03",
        "source": "synthetic",
    },
    {
        "id": "synthetic-018",
        "title": "WMI remote execution spreading across workstations",
        "severity": "Medium",
        "status": "Active",
        "description": (
            "WMI remote execution was observed propagating from a single "
            "compromised workstation to seven others in the same subnet. "
            "Each execution downloaded an identical payload from an internal "
            "staging server."
        ),
        "mitre_techniques": "T1021,T1059",
        "entities": "host: WS-DEV01, subnet: 10.20.30.0/24",
        "source": "synthetic",
    },
    # --- Denial of Service (1) ---
    {
        "id": "synthetic-019",
        "title": "Application-layer DDoS targeting public web application",
        "severity": "High",
        "status": "Closed",
        "description": (
            "An application-layer DDoS attack was detected targeting the "
            "public-facing web application. The attack generated 50,000 "
            "requests per second from a distributed botnet, causing service "
            "degradation for 45 minutes before WAF rules were updated."
        ),
        "mitre_techniques": "T1489",
        "entities": "host: LB-WEB01, domain: portal.contoso.com",
        "source": "synthetic",
    },
    # --- Credential Theft (1) ---
    {
        "id": "synthetic-020",
        "title": "LSASS memory dump attempt detected on workstation",
        "severity": "High",
        "status": "Closed",
        "description": (
            "An attempt to dump LSASS process memory was detected on a "
            "developer workstation using a renamed copy of procdump. The "
            "attempt was blocked by Credential Guard but indicates an "
            "attacker with local admin access."
        ),
        "mitre_techniques": "T1003",
        "entities": "user: ekim@contoso.com, host: WS-DEV07, process: svchelper.exe",
        "source": "synthetic",
    },
]


def build_incident_document(incident: dict) -> str:
    """Convert an incident dict into a natural-language document for embedding.

    Structured fields become readable text to maximize embedding quality.
    """
    parts = [
        f"Security Incident: {incident.get('title', 'Unknown')}",
        f"Severity: {incident.get('severity', 'Unknown')}",
        f"Status: {incident.get('status', 'Unknown')}",
    ]
    if incident.get("description"):
        parts.append(f"Description: {incident['description']}")
    if incident.get("mitre_techniques"):
        parts.append(f"MITRE ATT&CK Techniques: {incident['mitre_techniques']}")
    if incident.get("entities"):
        parts.append(f"Affected Entities: {incident['entities']}")
    return "\n".join(parts)


def build_incident_metadata(incident: dict) -> dict:
    """Extract metadata fields from an incident dict for ChromaDB storage."""
    return {
        "incident_number": 0,  # 0 for synthetic; real incidents use Sentinel number
        "title": incident.get("title", ""),
        "severity": incident.get("severity", "Unknown"),
        "status": incident.get("status", "Unknown"),
        "source": incident.get("source", "synthetic"),
        "mitre_techniques": incident.get("mitre_techniques", ""),
        "created_date": datetime.now(UTC).strftime("%Y-%m-%d"),
    }
