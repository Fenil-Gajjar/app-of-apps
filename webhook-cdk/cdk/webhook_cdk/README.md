# CDK Infrastructure Stack

This directory contains the `ArgoCdWebhookStack` class, which defines the cloud infrastructure for the project using AWS Cloud Development Kit (CDK).

## 🏗 Stack Resources

The stack provisions the following AWS resources:

### 1. Amazon SQS Queue (`ArgoCdWebhookQueue`)
*   **Purpose**: Buffer for incoming webhook events.
*   **Configuration**:
    *   `retention_period`: 4 days (default).
    *   `visibility_timeout`: 60 seconds.

### 2. AWS Lambda Function (`WebhookHandler`)
*   **Purpose**: Validates and processes the webhook requests.
*   **Runtime**: Python 3.10.
*   **Code Source**: Uploads code from the `../lambda` directory.
*   **Bundling**: Uses AWS CDK `BundlingOptions` to install dependencies (like `pydantic`) from `requirements.txt` using a Docker container during the build process.
*   **Permissions**: Granted `sqs:SendMessage` permissions to the Queue.

### 3. API Gateway HTTP API (`ArgoCdWebhookApi`)
*   **Purpose**: Public-facing endpoint for ArgoCD to call.
*   **Integration**: `HttpLambdaIntegration` - directly triggers the Lambda function.
*   **Route**: `POST /webhook`.

## 🔒 Security

*   **IAM Roles**: The Lambda function is assigned a minimal IAM execution role that only allows writing to the specific SQS Queue created by this stack.
*   **Environment Secrets**:
    *   *Current State*: `WEBHOOK_SECRET` is passed as a plain environment variable.
    *   *Production Recommendation*: Update the stack to fetch this secret from **AWS Secrets Manager** or **Systems Manager Parameter Store** at runtime to avoid exposing it in the Lambda configuration.

## 📂 File Structure

*   `webhook_stack.py`: The main stack definition file.

## 🧬 Extending the Stack

To add more functionality (e.g., a Dead Letter Queue or Custom Domain), modify the `ArgoCdWebhookStack` class in `webhook_stack.py`.

Example - Adding a Dead Letter Queue (DLQ):

```python
dlq = sqs.Queue(self, "WebhookDLQ")

queue = sqs.Queue(
    self,
    "ArgoCdWebhookQueue",
    dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
)
```
