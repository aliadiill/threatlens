import base64
import json
import logging
import re
from decimal import Decimal
from .domain import STATUSES, TRANSITIONS
from .repository import Repository, NotFound, Conflict


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in {"PK", "SK", "GSI1PK", "GSI1SK", "entity"}}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return int(value) if isinstance(value, Decimal) else value


def response(code, value):
    return {"statusCode": code, "headers": {"content-type": "application/json", "cache-control": "no-store", "x-content-type-options": "nosniff"}, "body": json.dumps(clean(value))}


def serve(event, repository):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    # API Gateway verifies signatures, issuer, audience and route scope. Reject ID tokens too.
    if not claims.get("sub") or claims.get("token_use") != "access":
        return response(401, {"error": "Authentication required"})
    route = event.get("routeKey")
    try:
        if route == "GET /incidents":
            cursor = (event.get("queryStringParameters") or {}).get("cursor")
            if cursor and len(cursor) > 2000:
                raise ValueError("Invalid cursor")
            return response(200, repository.list(cursor))
        incident_id = (event.get("pathParameters") or {}).get("id", "")
        if not re.fullmatch(r"[a-f0-9]{24}", incident_id):
            return response(400, {"error": "Invalid incident ID"})
        if route == "GET /incidents/{id}":
            return response(200, repository.get(incident_id))
        if route == "PATCH /incidents/{id}":
            body = event.get("body") or "{}"
            if event.get("isBase64Encoded"):
                body = base64.b64decode(body).decode()
            if len(body) > 5000:
                raise ValueError("Request too large")
            data = json.loads(body)
            if not isinstance(data, dict) or set(data) - {"version", "status", "note"}:
                raise ValueError("Unsupported fields")
            version, note, status = data.get("version"), data.get("note", ""), data.get("status")
            if type(version) is not int or version < 1 or not isinstance(note, str) or len(note) > 2000 or status not in STATUSES:
                raise ValueError("Version, status and note are invalid")
            current = repository.get(incident_id)
            if status != current["status"] and status not in TRANSITIONS[current["status"]]:
                raise ValueError("Invalid status transition")
            if status == "RESOLVED" and not note.strip():
                raise ValueError("Resolution requires an investigation note")
            return response(200, repository.change(incident_id, version, status, note.strip(), claims["sub"]))
        return response(404, {"error": "Route not found"})
    except (ValueError, UnicodeError) as exc:
        return response(400, {"error": str(exc)})
    except NotFound:
        return response(404, {"error": "Incident not found"})
    except Conflict:
        return response(409, {"error": "Incident changed; refresh and retry"})
    except Exception as exc:
        logging.error(json.dumps({"action": "api-failed", "errorType": type(exc).__name__}))
        return response(500, {"error": "Request failed"})


def handler(event, context):
    return serve(event, Repository())
