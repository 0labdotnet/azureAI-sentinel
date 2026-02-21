"""Hand-written investigation playbooks for the knowledge base.

Provides detailed response playbooks for the top 5 incident types:
phishing, brute force, malware, suspicious sign-in, and data exfiltration.
Each playbook includes investigation steps (with KQL), indicators,
containment, and escalation guidance.
"""

PLAYBOOKS: list[dict] = [
    # --- 1. Phishing ---
    {
        "playbook_id": "phishing-01",
        "incident_type": "Phishing",
        "mitre_techniques": "T1566,T1204,T1534",
        "sections": [
            {
                "section": "investigation",
                "content": (
                    "Phishing Investigation Playbook: Begin by identifying all "
                    "recipients who received the phishing email. Check the email "
                    "gateway logs for the sender address and subject line across "
                    "the organization. Determine how many users clicked the link "
                    "or opened the attachment by cross-referencing with endpoint "
                    "telemetry. Run the following KQL query in Sentinel to find "
                    "related sign-in anomalies after the email was delivered:\n\n"
                    "```kql\n"
                    "let phishing_time = datetime(2026-01-15T10:00:00Z);\n"
                    "SigninLogs\n"
                    "| where TimeGenerated > phishing_time\n"
                    "| where ResultType != 0\n"
                    "| summarize FailedAttempts=count() by UserPrincipalName, "
                    "IPAddress, Location\n"
                    "| where FailedAttempts > 3\n"
                    "| order by FailedAttempts desc\n"
                    "```\n\n"
                    "Also check for any new inbox rules created by compromised "
                    "accounts using the Office 365 management activity logs. "
                    "Verify whether any credentials were harvested by checking "
                    "for password changes or MFA registrations after the phishing "
                    "email was sent."
                ),
            },
            {
                "section": "indicators",
                "content": (
                    "Phishing Indicators Playbook: Key indicators of a phishing "
                    "attack include spoofed sender addresses with subtle domain "
                    "variations (e.g., contoso-portal.com vs contoso.com), URLs "
                    "pointing to recently registered domains (check WHOIS for "
                    "domain age under 30 days), email attachments with double "
                    "extensions (.pdf.exe), and urgency language in the email "
                    "body. Check SPF, DKIM, and DMARC results in the email "
                    "headers -- failed authentication is a strong indicator. "
                    "Look for encoded or obfuscated URLs using base64 or URL "
                    "shorteners. Monitor for newly created inbox forwarding "
                    "rules which attackers set up to maintain persistence."
                ),
            },
            {
                "section": "containment",
                "content": (
                    "Phishing Containment Playbook: Immediately block the "
                    "sender address and malicious URLs at the email gateway. "
                    "Purge the phishing email from all mailboxes using Exchange "
                    "content search and purge. If credentials were compromised, "
                    "force password resets for affected accounts and revoke all "
                    "active sessions. Disable any inbox rules created by the "
                    "attacker. If malicious attachments were opened, isolate "
                    "affected endpoints from the network and run a full "
                    "antimalware scan. Update the email filtering rules to block "
                    "similar patterns going forward."
                ),
            },
            {
                "section": "escalation",
                "content": (
                    "Phishing Escalation Playbook: Escalate to Tier 2 if more "
                    "than 5 users clicked the phishing link or opened the "
                    "attachment. Escalate to Tier 3 / IR team if credentials "
                    "were confirmed harvested and used for unauthorized access. "
                    "Escalate to CISO if executive accounts were targeted or "
                    "compromised. Notify legal and compliance if PII or "
                    "regulated data was potentially exposed. File an abuse "
                    "report with the hosting provider for the phishing domain."
                ),
            },
        ],
    },
    # --- 2. Brute Force ---
    {
        "playbook_id": "brute-force-01",
        "incident_type": "Brute Force",
        "mitre_techniques": "T1110,T1078",
        "sections": [
            {
                "section": "investigation",
                "content": (
                    "Brute Force Investigation Playbook: Identify the source "
                    "IP addresses performing the brute force attack and check "
                    "them against threat intelligence feeds. Determine which "
                    "accounts were targeted and whether any login succeeded. "
                    "Run the following KQL query to identify brute force "
                    "patterns in Sentinel:\n\n"
                    "```kql\n"
                    "SigninLogs\n"
                    "| where TimeGenerated > ago(24h)\n"
                    "| where ResultType == 50126  // Invalid username or password\n"
                    "| summarize FailureCount=count(), "
                    "TargetAccounts=dcount(UserPrincipalName), "
                    "Accounts=make_set(UserPrincipalName, 10) "
                    "by IPAddress, Location\n"
                    "| where FailureCount > 50\n"
                    "| order by FailureCount desc\n"
                    "```\n\n"
                    "Check if the attack is a password spray (few passwords, "
                    "many accounts) or a traditional brute force (many passwords, "
                    "one account). Review Azure AD Identity Protection risk "
                    "events for correlated detections. Check if any of the "
                    "targeted accounts have weak or default passwords."
                ),
            },
            {
                "section": "indicators",
                "content": (
                    "Brute Force Indicators Playbook: High volume of failed "
                    "authentication events (ResultType 50126) from a single "
                    "IP or small IP range. Time patterns showing systematic "
                    "attempts at regular intervals. Multiple accounts targeted "
                    "with the same password (password spray pattern). Source "
                    "IPs from Tor exit nodes, VPN services, or hosting "
                    "providers. Geographic anomalies -- attacks originating "
                    "from countries where the organization has no presence. "
                    "Watch for a sudden successful login after many failures "
                    "which indicates a compromised credential."
                ),
            },
            {
                "section": "containment",
                "content": (
                    "Brute Force Containment Playbook: Block the attacking IP "
                    "addresses at the firewall and Azure AD Conditional Access. "
                    "If any account was successfully compromised, immediately "
                    "reset the password and revoke active sessions. Enable "
                    "smart lockout in Azure AD if not already configured. "
                    "Enforce MFA for all targeted accounts. Review and "
                    "strengthen password policies. If the attack targeted "
                    "a VPN or RDP endpoint, ensure it is not directly "
                    "exposed to the internet -- place it behind a VPN "
                    "gateway or jump box."
                ),
            },
            {
                "section": "escalation",
                "content": (
                    "Brute Force Escalation Playbook: Escalate to Tier 2 if "
                    "the attack persists after IP blocking (attacker rotating "
                    "IPs). Escalate to Tier 3 if any account was confirmed "
                    "compromised and there is evidence of post-compromise "
                    "activity (lateral movement, data access). Escalate to "
                    "CISO if privileged accounts (Global Admin, Domain Admin) "
                    "were targeted or compromised. Engage ISP or hosting "
                    "provider abuse teams for persistent distributed attacks."
                ),
            },
        ],
    },
    # --- 3. Malware ---
    {
        "playbook_id": "malware-01",
        "incident_type": "Malware",
        "mitre_techniques": "T1059,T1204,T1486,T1562",
        "sections": [
            {
                "section": "investigation",
                "content": (
                    "Malware Investigation Playbook: Identify the malware "
                    "family and variant using the hash values from endpoint "
                    "detection. Check the file hash against VirusTotal and "
                    "internal threat intelligence databases. Determine the "
                    "initial infection vector -- was it email attachment, web "
                    "download, USB drive, or lateral movement? Run the "
                    "following KQL query to find related process executions "
                    "in Sentinel:\n\n"
                    "```kql\n"
                    "SecurityAlert\n"
                    "| where TimeGenerated > ago(7d)\n"
                    "| where AlertName has_any (\"malware\", \"trojan\", "
                    "\"ransomware\", \"beacon\")\n"
                    "| extend Entities = parse_json(Entities)\n"
                    "| mv-expand Entity = Entities\n"
                    "| extend EntityType = tostring(Entity.Type), "
                    "EntityName = tostring(Entity.Name)\n"
                    "| summarize AlertCount=count(), "
                    "Alerts=make_set(AlertName, 5) by EntityName, EntityType\n"
                    "| order by AlertCount desc\n"
                    "```\n\n"
                    "Check if the malware established persistence mechanisms "
                    "(registry run keys, scheduled tasks, services). Analyze "
                    "network traffic for C2 communication patterns. Determine "
                    "the scope by identifying all endpoints that have the "
                    "same indicators of compromise."
                ),
            },
            {
                "section": "indicators",
                "content": (
                    "Malware Indicators Playbook: Suspicious process names "
                    "or processes running from temp directories (%TEMP%, "
                    "%APPDATA%). Unsigned executables or DLLs loaded by "
                    "legitimate processes (DLL sideloading). Unusual network "
                    "connections to external IPs on non-standard ports. "
                    "PowerShell with encoded commands (-EncodedCommand flag). "
                    "Disabled security tools (Defender, AMSI bypass attempts). "
                    "Registry modifications to Run/RunOnce keys. Newly "
                    "created scheduled tasks or services. Large DNS query "
                    "volumes to newly registered domains (potential DNS "
                    "tunneling)."
                ),
            },
            {
                "section": "containment",
                "content": (
                    "Malware Containment Playbook: Isolate infected endpoints "
                    "from the network immediately using EDR network isolation. "
                    "Do NOT power off the machine -- preserve volatile memory "
                    "for forensics. Block all identified C2 IP addresses and "
                    "domains at the firewall and DNS level. Quarantine the "
                    "malware sample for analysis. If ransomware, check whether "
                    "encryption has started and assess backup availability. "
                    "Run targeted antimalware scans on all endpoints in the "
                    "same network segment. Block the file hashes in Defender "
                    "for Endpoint custom indicators."
                ),
            },
            {
                "section": "escalation",
                "content": (
                    "Malware Escalation Playbook: Escalate to Tier 2 if the "
                    "malware has spread to more than 3 endpoints. Escalate to "
                    "Tier 3 / IR team if C2 communication was confirmed or "
                    "data exfiltration is suspected. Escalate to CISO for any "
                    "ransomware incident regardless of scope. Engage external "
                    "incident response if the malware is a novel variant with "
                    "no known remediation. Notify legal if customer data or "
                    "PII may have been accessed by the malware."
                ),
            },
        ],
    },
    # --- 4. Suspicious Sign-in ---
    {
        "playbook_id": "suspicious-signin-01",
        "incident_type": "Suspicious Sign-in",
        "mitre_techniques": "T1078,T1134",
        "sections": [
            {
                "section": "investigation",
                "content": (
                    "Suspicious Sign-in Investigation Playbook: Verify the "
                    "sign-in details including source IP, location, device, "
                    "and browser. Check if the user has a history of signing "
                    "in from this location or device. Compare the sign-in "
                    "time with the user's normal working hours. Run the "
                    "following KQL query to profile the user's recent "
                    "sign-in behavior:\n\n"
                    "```kql\n"
                    "let target_user = \"user@contoso.com\";\n"
                    "SigninLogs\n"
                    "| where TimeGenerated > ago(30d)\n"
                    "| where UserPrincipalName == target_user\n"
                    "| summarize SignInCount=count(), "
                    "Locations=make_set(Location, 10), "
                    "IPs=make_set(IPAddress, 10), "
                    "Devices=make_set(DeviceDetail.displayName, 10) "
                    "by bin(TimeGenerated, 1d)\n"
                    "| order by TimeGenerated desc\n"
                    "```\n\n"
                    "Check for impossible travel scenarios (two logins from "
                    "geographically distant locations within a short time). "
                    "Review Azure AD Identity Protection risk detections for "
                    "the user. Check if MFA was satisfied or bypassed. "
                    "Contact the user directly to confirm whether the sign-in "
                    "was legitimate."
                ),
            },
            {
                "section": "indicators",
                "content": (
                    "Suspicious Sign-in Indicators Playbook: Logins from new "
                    "or unfamiliar geographic locations. Sign-ins from "
                    "anonymous IP addresses (Tor, VPN services). Impossible "
                    "travel -- two sign-ins from distant locations within a "
                    "time window that makes physical travel impossible. "
                    "Sign-ins from unfamiliar or non-compliant devices. "
                    "Sign-ins outside normal business hours for the user's "
                    "time zone. Multiple failed MFA attempts followed by "
                    "success (MFA fatigue attack). Service accounts used "
                    "interactively when they should only be used by "
                    "automated processes."
                ),
            },
            {
                "section": "containment",
                "content": (
                    "Suspicious Sign-in Containment Playbook: If the sign-in "
                    "is confirmed unauthorized, immediately reset the user's "
                    "password and revoke all active refresh tokens. Review and "
                    "remove any MFA methods the attacker may have registered. "
                    "Check for and disable any mailbox forwarding rules or "
                    "delegate access added by the attacker. Apply a Conditional "
                    "Access policy to require compliant device and known "
                    "location for the affected account. Review the user's "
                    "recent activities for any data access or changes made "
                    "during the suspicious session."
                ),
            },
            {
                "section": "escalation",
                "content": (
                    "Suspicious Sign-in Escalation Playbook: Escalate to "
                    "Tier 2 if the account performed sensitive actions during "
                    "the suspicious session (file downloads, admin operations). "
                    "Escalate to Tier 3 if the account has elevated privileges "
                    "(Global Admin, Exchange Admin) or if post-compromise "
                    "activity is detected (new inbox rules, OAuth app "
                    "registrations). Escalate to CISO if multiple accounts "
                    "show the same suspicious sign-in pattern simultaneously "
                    "(coordinated attack). Notify the user's manager per "
                    "insider threat procedures."
                ),
            },
        ],
    },
    # --- 5. Data Exfiltration ---
    {
        "playbook_id": "data-exfiltration-01",
        "incident_type": "Data Exfiltration",
        "mitre_techniques": "T1567,T1041,T1005",
        "sections": [
            {
                "section": "investigation",
                "content": (
                    "Data Exfiltration Investigation Playbook: Identify the "
                    "user or system account involved and the data destination. "
                    "Determine what data was transferred -- check DLP alerts, "
                    "file access logs, and SharePoint/OneDrive audit logs. "
                    "Assess whether the data contained sensitive or regulated "
                    "information (PII, financial, intellectual property). Run "
                    "the following KQL query to identify unusual data "
                    "transfers in Sentinel:\n\n"
                    "```kql\n"
                    "CommonSecurityLog\n"
                    "| where TimeGenerated > ago(7d)\n"
                    "| where DeviceAction == \"Allow\"\n"
                    "| where SentBytes > 100000000  // More than 100MB\n"
                    "| summarize TotalBytesSent=sum(SentBytes), "
                    "ConnectionCount=count() "
                    "by SourceUserName, DestinationHostName, "
                    "DestinationIP\n"
                    "| extend TotalMB = TotalBytesSent / 1048576\n"
                    "| where TotalMB > 500\n"
                    "| order by TotalMB desc\n"
                    "```\n\n"
                    "Cross-reference the destination with known cloud storage "
                    "services, file sharing platforms, or anonymous upload "
                    "sites. Check if the transfer occurred during business "
                    "hours or at unusual times. Review the user's recent "
                    "access patterns for anomalous file access volumes."
                ),
            },
            {
                "section": "indicators",
                "content": (
                    "Data Exfiltration Indicators Playbook: Large outbound "
                    "data transfers (especially outside business hours). "
                    "Connections to personal cloud storage services (Google "
                    "Drive, Dropbox, personal OneDrive). Connections to "
                    "anonymous file sharing services (Mega.nz, WeTransfer). "
                    "DNS tunneling -- high volume of DNS queries to unusual "
                    "domains. Encrypted archive files (.7z, .zip with password) "
                    "being created before transfer. Bulk file downloads from "
                    "SharePoint or internal file servers preceding the "
                    "outbound transfer. Use of staging directories where "
                    "files are collected before exfiltration."
                ),
            },
            {
                "section": "containment",
                "content": (
                    "Data Exfiltration Containment Playbook: Block the "
                    "destination IP or domain at the firewall immediately. "
                    "Disable the user account if exfiltration is confirmed "
                    "malicious (not accidental). Revoke access to the "
                    "sensitive data sources accessed by the user. If a "
                    "service account was used, rotate the credentials and "
                    "audit all access logs. Apply DLP policies to prevent "
                    "further transfers of sensitive data categories. Preserve "
                    "all evidence: network flow logs, file access logs, "
                    "endpoint telemetry, and email logs for forensic analysis."
                ),
            },
            {
                "section": "escalation",
                "content": (
                    "Data Exfiltration Escalation Playbook: Escalate to Tier 2 "
                    "for any confirmed data exfiltration regardless of volume. "
                    "Escalate to Tier 3 / IR team if the data includes PII, "
                    "PHI, financial records, or intellectual property. Escalate "
                    "to CISO and legal immediately if the exfiltration may "
                    "trigger regulatory notification requirements (GDPR, "
                    "HIPAA, state breach notification laws). Engage HR if the "
                    "exfiltration appears to be an insider threat (departing "
                    "employee, disgruntled employee). Preserve chain of "
                    "custody for any data that may be needed as evidence."
                ),
            },
        ],
    },
]


def build_playbook_chunks(playbook: dict) -> list[dict]:
    """Convert a playbook dict into a list of chunk dicts for VectorStore.

    Each section becomes a separate chunk with self-contained context
    (includes playbook title and incident type in the document text).
    """
    chunks = []
    for i, section in enumerate(playbook["sections"]):
        chunk_id = f"{playbook['playbook_id']}-{section['section']}-{i}"
        document = (
            f"Playbook: {playbook['incident_type']} - "
            f"{section['section']}\n\n{section['content']}"
        )
        metadata = {
            "playbook_id": playbook["playbook_id"],
            "incident_type": playbook["incident_type"],
            "mitre_techniques": playbook["mitre_techniques"],
            "section": section["section"],
            "chunk_index": i,
            "source": "hand-written",
        }
        chunks.append({
            "id": chunk_id,
            "document": document,
            "metadata": metadata,
        })
    return chunks
