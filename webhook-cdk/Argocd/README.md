# ArgoCD Notifications Configuration

This directory contains the configuration files required to set up ArgoCD to send webhook events to our AWS solution.

## 📄 File: `argocd-configmap-notifications.yaml`

This ConfigMap defines the `service`, `template`, and `trigger` for the ArgoCD Notifications controller.

### Components

#### 1. Service Definition (`service.webhook.argocd-events`)
Defines **where** and **how** to send the webhook.

```yaml
service.webhook.argocd-events: |
  url: <YOUR_API_GATEWAY_URL>/webhook  # REST API Endpoint
  method: POST
  headers:
    - name: Content-Type
      value: application/json
    - name: Authorization
      value: Bearer <YOUR_SECRET_TOKEN> # Shared secret for authentication
    - name: X-Cluster-Id
      value: "{{.app.metadata.labels.clusterid}}" # Injects cluster ID from app label
```

*   **Authorization**: Adds a Bearer token that the Lambda function will verify.
*   **X-Cluster-Id**: Extracts the `clusterid` label from the Application resource and sends it as a header. This is critical for security validation in the Lambda.

#### 2. Template (`template.argocd-sync-succeeded`)
Defines the **JSON payload** structure sent to the webhook.

```yaml
context: |
  {
    "event": "sync-succeeded",
    "appName": "{{.app.metadata.name}}",
    "status": "{{.app.status.sync.status}}",
    "health": "{{.app.status.health.status}}",
    "revision": "{{.app.status.sync.revision}}",
    "clusterId": "{{.app.metadata.labels.clusterid}}" # Must match header
  }
```
*   **Data Consistency**: We send `clusterId` in the body effectively duplicating the header. The Lambda function checks that these two values match to prevent tampering.

#### 3. Trigger (`trigger.on-sync-succeeded`)
Defines **when** the notification is sent.

```yaml
trigger.on-sync-succeeded: |
  - when: app.status.sync.status == 'Synced'
    send:
      - argocd-sync-succeeded
```
*   This triggers the webhook whenever an Application's sync status becomes `Synced`.

## 📦 Deployment Instructions

1.  **Edit the ConfigMap**:
    Replace the placeholder URL and Token in `argocd-configmap-notifications.yaml` with your actual API Gateway URL and Secret.
    ```yaml
    url: https://<api-id>.execute-api.<region>.amazonaws.com/webhook
    value: Bearer my-secure-token
    ```

2.  **Apply to Cluster**:
    Apply the manifest to the namespace where ArgoCD is installed (usually `argocd`).

    ```bash
    kubectl apply -f argocd-configmap-notifications.yaml -n argocd
    ```

3.  **Reload Controller** (Optional but recommended):
    Sometimes the notification controller needs a restart to pick up changes immediately.
    ```bash
    kubectl rollout restart deployment argocd-notifications-controller -n argocd
    ```

## 🏷 Application Requirements

For the webhook to work correctly, every ArgoCD Application **MUST** have the `clusterid` label.

Example Application:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  labels:
    clusterid: production-cluster-01  <-- REQUIRED
spec:
  ...
```
If this label is missing, the webhook payload will contain an empty cluster ID, and the Lambda validation may fail.
