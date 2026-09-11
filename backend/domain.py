"""Pure detection rules. No AWS calls and no destructive response capabilities."""
import hashlib
from datetime import datetime, timezone

STATUSES = {"OPEN", "INVESTIGATING", "RESOLVED"}
TRANSITIONS = {"OPEN": {"INVESTIGATING", "RESOLVED"}, "INVESTIGATING": {"OPEN", "RESOLVED"}, "RESOLVED": {"INVESTIGATING"}}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize(event):
    if not isinstance(event, dict) or not isinstance(event.get("detail"), dict):
        raise ValueError("Expected an EventBridge event with detail")
    source = event.get("source", "")
    if source not in {"threatlens.demo", "aws.iam", "aws.ec2", "aws.signin", "aws.cloudtrail"}:
        raise ValueError("Unsupported source")
    detail = event["detail"]
    simulated = source == "threatlens.demo"
    # Demo IDs survive a repeated PutEvents call; CloudTrail eventID survives transport retries.
    event_id = detail.get("eventID") or event.get("id")
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
        raise ValueError("A bounded stable event ID is required")
    event_name = str(detail.get("eventName", ""))[:80]
    params = detail.get("requestParameters") or {}
    if not isinstance(params, dict):
        raise ValueError("requestParameters must be an object")
    principal = detail.get("userIdentity") or {}
    resource = detail.get("resource") if simulated else params.get("groupId") or params.get("userName") or params.get("roleName") or "account-control-plane"
    observed_at = event.get("time") or timestamp()
    if not isinstance(observed_at, str):
        raise ValueError("Invalid event time")
    parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Event time needs a timezone")
    return {"eventId": event_id, "source": source, "eventName": event_name,
            "resource": str(resource or "demo-resource")[:180],
            "actor": str(principal.get("arn") or principal.get("userName") or "unknown")[:240],
            "region": str(event.get("region", "us-east-1"))[:30],
            "occurredAt": parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "simulated": simulated, "parameters": params,
            "errorCode": detail.get("errorCode"), "responseElements": detail.get("responseElements") or {}}


def public_ingress(params):
    permissions = params.get("ipPermissions", {})
    permissions = permissions.get("items", []) if isinstance(permissions, dict) else permissions
    if not isinstance(permissions, list):
        return False
    for permission in permissions:
        ranges = permission.get("ipRanges", {})
        ranges = ranges.get("items", []) if isinstance(ranges, dict) else ranges
        ipv6 = permission.get("ipv6Ranges", {})
        ipv6 = ipv6.get("items", []) if isinstance(ipv6, dict) else ipv6
        public = any(r.get("cidrIp") == "0.0.0.0/0" for r in ranges) or any(r.get("cidrIpv6") == "::/0" for r in ipv6)
        low, high = permission.get("fromPort"), permission.get("toPort")
        sensitive = permission.get("ipProtocol") == "-1" or (isinstance(low, int) and isinstance(high, int) and any(low <= p <= high for p in (22, 3389)))
        if public and sensitive:
            return True
    return False


def detect(signal):
    name, params = signal["eventName"], signal["parameters"]
    rule = None
    if name in {"StopLogging", "DeleteTrail"} and not signal["errorCode"]:
        rule = ("audit-evasion", "CRITICAL", "Cloud audit logging was disabled", "Review CloudTrail configuration and preserve the event for investigation.")
    elif name in {"AttachUserPolicy", "AttachRolePolicy"} and str(params.get("policyArn", "")).endswith(":policy/AdministratorAccess") and not signal["errorCode"]:
        rule = ("privilege-escalation", "HIGH", "Administrator policy attached", "Verify change authorization and review the principal's recent activity.")
    elif name == "AuthorizeSecurityGroupIngress" and public_ingress(params) and not signal["errorCode"]:
        rule = ("network-exposure", "HIGH", "Administrative port exposed publicly", "Review the security group and narrow administrative access after approval.")
    elif name == "ConsoleLogin" and signal["responseElements"].get("ConsoleLogin") == "Failure":
        rule = ("authentication", "MEDIUM", "Failed console sign-in", "Correlate with other login events; one failure is a signal, not proof of compromise.")
    elif name == "CreateAccessKey" and not signal["errorCode"]:
        rule = ("credential-change", "MEDIUM", "Long-lived access key created", "Verify the key is required and prefer temporary credentials.")
    if not rule:
        return None
    category, severity, title, guidance = rule
    incident_id = hashlib.sha256((signal["source"] + ":" + signal["eventId"] + ":" + category).encode()).hexdigest()[:24]
    return {"id": incident_id, "eventId": signal["eventId"], "title": title, "severity": severity,
            "category": category, "resource": signal["resource"], "actor": signal["actor"], "region": signal["region"],
            "source": signal["source"], "eventName": name, "createdAt": signal["occurredAt"],
            "updatedAt": timestamp(), "status": "OPEN", "version": 1, "simulated": signal["simulated"],
            "guidance": guidance, "response": "SIMULATED: investigation checklist prepared; no resource was changed."}
