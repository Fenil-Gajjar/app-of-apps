# Webhook CDK Project

## Overview
This project implements a secure and scalable webhook handling architecture for ArgoCD using AWS CDK. It captures ArgoCD sync events and forwards them to an Amazon SQS queue for downstream processing.

The system ensures that only valid, authorized requests from ArgoCD are processed, providing a robust integration point for building event-driven workflows based on application deployment statuses.

## 🏗 Architecture

The solution uses a serverless architecture on AWS:

```mermaid
graph LR
    ArgoCD[ArgoCD Cluster] -->|HTTPS POST| APIGW[API Gateway]
    APIGW -->|Proxy| Lambda[Webhook Handler Lambda]
    Lambda -->|Validate & Enqueue| SQS[SQS Queue]
    
    subgraph "AWS Cloud"
    APIGW
    Lambda
    SQS
    end
```

**Flow:**
1.  **ArgoCD Notification**: ArgoCD triggers a notification on a sync event (e.g., `on-sync-succeeded`).
2.  **API Gateway**: Receives the webhook POST request.
3.  **Lambda Function**:
    *   Validates the Authorization header (Bearer token).
    *   Parses the JSON payload.
    *   Validates the payload structure.
    *   Verifies that the `clusterId` in the header matches the body (security check).
    *   Enqueues the valid message to SQS.
4.  **SQS**: Stores the message for consumption by backend workers.

## 📂 Project Structure

*   **[argocd/](argocd/README.md)**: Contains the Kubernetes manifests for configuring ArgoCD Notifications.
*   **[cdk/](cdk/webhook_cdk/README.md)**: The AWS CDK application code defining the infrastructure.
    *   **[lambda/](cdk/lambda/README.md)**: The Python source code for the Lambda function.
    *   **[webhook_cdk/](cdk/webhook_cdk/README.md)**: The CDK Stack definition.

## 🚀 Prerequisites

Before deploying, ensure you have the following installed:

*   **Node.js** (for AWS CDK)
*   **Python 3.10+** (for CDK app and Lambda)
*   **Docker** (Must be running for CDK to bundle Python dependencies)
*   **AWS CLI** (configured with appropriate credentials)
*   **AWS CDK Toolkit**: `npm install -g aws-cdk`

## 🛠 Installation & Deployment

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd webhook-cdk
    ```

2.  **Install Python Dependencies**
    Navigate to the `cdk` directory and install the requirements.
    ```bash
    cd cdk
    pip install -r requirements.txt
    ```

3.  **Bootstrap CDK (First time only)**
    If you haven't deployed CDK apps to this account/region before:
    ```bash
    cdk bootstrap
    ```

4.  **Deploy the Stack**
    ```bash
    cdk deploy
    ```
    *Note the `Outputs` from the deployment, specifically the **API Gateway Endpoint URL**.*

## ⚙️ Configuration

### 1. AWS Lambda Environment
The Lambda function is automatically configured by the CDK stack with:
*   `SQS_QUEUE_URL`: Output from the created SQS queue.
*   `WEBHOOK_SECRET`: A shared secret token (Currently hardcoded in `webhook_stack.py` for demo purposes. **Recommendation**: Move to AWS Secrets Manager for production).

### 2. ArgoCD Configuration
You need to configure the `argocd-notifications-cm` ConfigMap in your Kubernetes cluster to send events to the deployed API Gateway.

See **[argocd/README.md](argocd/README.md)** for detailed configuration steps.

## 🧪 Testing

You can test the webhook endpoint using `curl`:

```bash
curl -X POST <YOUR_API_GATEWAY_URL>/webhook \
  -H "Authorization: Bearer argocd-webhook-secret-9f83kdf93kdf" \
  -H "X-Cluster-Id: test-cluster-1" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "sync-succeeded",
    "appName": "test-app",
    "status": "Synced",
    "health": "Healthy",
    "revision": "abc1234",
    "clusterId": "test-cluster-1"
  }'
```

**Expected Response:**
```json
{"status": "enqueued"}
```
