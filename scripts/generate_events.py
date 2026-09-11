"""Deterministic, bounded security signals; JSON output by default, AWS only with --send."""
import argparse
import json
from datetime import datetime, timezone, timedelta


def events(count=12, seed=7):
    if not 1 <= count <= 100:
        raise ValueError("count must be between 1 and 100")
    cases = [
        ("StopLogging", {}, {}),
        ("AttachUserPolicy", {"policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}, {}),
        ("AuthorizeSecurityGroupIngress", {"ipPermissions": {"items": [{"ipProtocol": "tcp", "fromPort": 22, "toPort": 22, "ipRanges": {"items": [{"cidrIp": "0.0.0.0/0"}]}}]}}, {}),
        ("ConsoleLogin", {}, {"ConsoleLogin": "Failure"}),
        ("CreateAccessKey", {}, {}),
        ("DescribeInstances", {}, {})]
    for index in range(count):
        name, parameters, response = cases[(seed + index) % len(cases)]
        yield {"id": f"demo-{seed}-{index:03}", "source": "threatlens.demo", "detail-type": "ThreatLens Demo Signal", "region": "us-east-1", "time": (datetime(2026, 1, 15, 12, tzinfo=timezone.utc) + timedelta(minutes=index)).isoformat(), "detail": {"eventID": f"demo-{seed}-{index:03}", "eventName": name, "resource": f"demo-resource-{index % 4 + 1}", "userIdentity": {"userName": "demo-analyst"}, "requestParameters": parameters, "responseElements": response}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--send", action="store_true", help="Actually publish safe custom events; never runs suspicious AWS APIs")
    parser.add_argument("--bus", default="threatlens-dev-events")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()
    items = list(events(args.count, args.seed))
    if not args.send:
        print(json.dumps(items, indent=2))
        return
    import boto3
    client = boto3.client("events", region_name=args.region)
    for start in range(0, len(items), 10):
        result = client.put_events(Entries=[{"EventBusName": args.bus, "Source": e["source"], "DetailType": e["detail-type"], "Detail": json.dumps(e["detail"]), "Time": datetime.fromisoformat(e["time"])} for e in items[start:start + 10]])
        if result["FailedEntryCount"]:
            raise RuntimeError("Some events failed; rerun the same seed safely after inspecting AWS response codes")
    print(f"Published {len(items)} safe custom events; repeated seed IDs are deduplicated")


if __name__ == "__main__":
    main()
