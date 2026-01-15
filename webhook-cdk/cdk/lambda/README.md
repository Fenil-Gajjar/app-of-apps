# Webhook Handler Lambda

This directory contains the Python source code for the AWS Lambda function that handles incoming webhooks from ArgoCD.

## 🧠 Logic Flow

### Dependencies
The function relies on external libraries defined in `requirements.txt`:
*   `pydantic`: Used for strict, declarative payload validation.

### Logic Flow

The `webhook_handler.py` script performs the following steps sequentially:

1.  **Startup**: Initializes the AWS SDK (Boto3) for SQS and reads environment variables.
2.  **Receive Event**: Accepts the API Gateway Proxy event.
3.  **Authorization Check**:
    *   Extracts the `Authorization` header.
    *   Verifies it follows the `Bearer <token>` format.
    *   Compares the token against the `WEBHOOK_SECRET` environment variable.
4.  **Parse & Validate Payload**:
    *   Decodes the JSON body.
    *   Uses **Pydantic** (`WebhookPayload` model) to validate the structure and data types.
    *   **Strict Check**: Ensures `event`, `appName`, `status`, `health`, `revision`, and `clusterId` are present and of the correct type.
5.  **Security Validation (Cluster ID)**:
    *   Compares the `X-Cluster-Id` HTTP header with the `clusterId` field in the JSON body.
    *   **Rule**: They MUST match. This prevents scenarios where a malicious actor might try to spoof the payload origin details while passing a valid header, or vice-versa.
6.  **Enqueue**: Sends the validated payload to the SQS queue.
7.  **Response**: Returns HTTP 200 to API Gateway.

## 🔧 Environment Variables

The Lambda function relies on the following environment variables, injected by the CDK stack:

| Variable | Description |
| :--- | :--- |
| `SQS_QUEUE_URL` | The HTTPS URL of the SQS queue where messages are sent. |
| `WEBHOOK_SECRET` | The secret token used to validate the `Authorization` header. |

## 📥 Input Payload (ArgoCD Webhook)

The function expects a JSON payload from ArgoCD similar to this:

```json
{
  "event": "sync-succeeded",
  "appName": "guestbook-prod",
  "status": "Synced",
  "health": "Healthy",
  "revision": "Wait",
  "clusterId": "cluster-nyc-01"
}
```

## 📤 SQS Message Format

When successfully processed, the message sent to SQS is wrapped with additional metadata:

```json
{
  "source": "argocd",
  "cluster_id": "cluster-nyc-01",
  "payload": { ...original_argocd_payload... },
  "headers": {
    "x-request-id": "aws-request-id-uuid"
  }
}
```

## 🚫 Error Handling

The function returns standard HTTP error codes which API Gateway relays to the caller:

*   **401 Unauthorized**: Missing or incorrect `Authorization` token.
*   **400 Bad Request**: Invalid JSON, missing fields, or Cluster ID mismatch.
*   **500 Internal Server Error**: Issues connecting to SQS or other unhandled exceptions.

## 📝 Logging

The function uses the standard Python `logging` module. logs are streamed to AWS CloudWatch Logs.
*   **INFO**: startup, successful events (with sanitized data).
*   **WARNING**: Validation failures (auth, schema, security headers).
*   **ERROR**: Exceptions and system failures.
