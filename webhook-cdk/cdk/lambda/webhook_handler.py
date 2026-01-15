import json
import os
import logging
import boto3

# ---------- Setup ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]

# Required fields for valid ArgoCD webhook payload
REQUIRED_FIELDS = {"event", "appName", "status", "health", "revision", "clusterId"}


# ---------- Validation Functions ----------
def _validate_payload_structure(payload):
    """Ensure payload has all required ArgoCD fields."""
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        return False, f"Missing required fields: {missing}"

    return True, None


def _validate_cluster_id(headers, payload):
    """Ensure header clusterId matches body clusterId."""
    header_cluster_id = headers.get("x-cluster-id") or headers.get("X-Cluster-Id")
    body_cluster_id = payload.get("clusterId")

    if not header_cluster_id:
        return False, "Missing X-Cluster-Id header"

    if header_cluster_id != body_cluster_id:
        return False, "Cluster ID mismatch between header and body"

    return True, None


# ---------- Lambda Handler ----------
def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    # 1️⃣ Authorization Header
    headers = event.get("headers") or {}
    auth_header = headers.get("authorization") or headers.get("Authorization")

    if not auth_header:
        logger.warning("Missing Authorization header")
        return _unauthorized("Missing Authorization header")

    if not auth_header.startswith("Bearer "):
        logger.warning("Invalid Authorization header format")
        return _unauthorized("Invalid Authorization header")

    token = auth_header.replace("Bearer ", "").strip()

    if token != WEBHOOK_SECRET:
        logger.warning("Invalid webhook token")
        return _unauthorized("Invalid token")

    # 2️⃣ Parse Body
    body = event.get("body")
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return _bad_request("Invalid JSON payload")

    # 3️⃣ Validate Payload Structure
    is_valid, error_msg = _validate_payload_structure(payload)
    if not is_valid:
        logger.warning("Payload structure validation failed: %s", error_msg)
        return _bad_request(error_msg)

    # 4️⃣ Validate Header-Body ClusterId Match
    is_valid, error_msg = _validate_cluster_id(headers, payload)
    if not is_valid:
        logger.warning("Cluster ID validation failed: %s", error_msg)
        return _bad_request(error_msg)

    # Extract clusterId (now guaranteed to exist and match)
    cluster_id = payload.get("clusterId")

    # 5️⃣ Send to SQS
    try:
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({
                "source": "argocd",
                "cluster_id": cluster_id,
                "payload": payload,
                "headers": {
                    "x-request-id": context.aws_request_id
                }
            })
        )

        logger.info("Message sent to SQS. MessageId=%s", response["MessageId"])

    except Exception as e:
        logger.exception("Failed to send message to SQS")
        return _server_error("Failed to enqueue message")

    # 6️⃣ Success
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "enqueued"})
    }


# ---------- Helpers ----------
def _unauthorized(message):
    return {
        "statusCode": 401,
        "body": json.dumps({"error": message})
    }


def _bad_request(message):
    return {
        "statusCode": 400,
        "body": json.dumps({"error": message})
    }


def _server_error(message):
    return {
        "statusCode": 500,
        "body": json.dumps({"error": message})
    }
