import json
import os
import logging
import boto3
from pydantic import BaseModel, ConfigDict, ValidationError

# ---------- Setup ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]


# ---------- Pydantic Models ----------
class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    event: str
    appName: str
    status: str
    health: dict
    revision: str
    clusterId: str  # Ensures clusterId is present and is a string


def _validate_cluster_id(headers, payload: WebhookPayload):
    """Ensure header clusterId matches body clusterId."""
    header_cluster_id = headers.get("x-cluster-id") or headers.get("X-Cluster-Id")
    body_cluster_id = payload.clusterId

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

    # 2️⃣ Parse Body & 3️⃣ Validate Payload Structure (Pydantic)
    body = event.get("body")
    try:
        payload_data = json.loads(body) if body else {}
        payload = WebhookPayload(**payload_data)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return _bad_request("Invalid JSON payload")
    except ValidationError as e:
        logger.warning("Payload validation failed: %s", e)
        # Return a nice string error from Pydantic
        return _bad_request(f"Validation Error: {str(e)}")

    # 4️⃣ Validate Header-Body ClusterId Match
    is_valid, error_msg = _validate_cluster_id(headers, payload)
    if not is_valid:
        logger.warning("Cluster ID validation failed: %s", error_msg)
        return _bad_request(error_msg)

    # 5️⃣ Send to SQS
    try:
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({
                "source": "argocd",
                "cluster_id": payload.clusterId,
                "payload": payload.model_dump(),  # Convert back to dict
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
