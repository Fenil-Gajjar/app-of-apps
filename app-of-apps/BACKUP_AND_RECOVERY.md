# 📘 Kubernetes Backup & Disaster Recovery
## Argo CD + Velero + MinIO (Kind / EC2)

---

## 📌 Overview

This document explains a complete backup and disaster recovery (DR) implementation for Kubernetes workloads managed by Argo CD (App-of-Apps pattern) using Velero and MinIO.

The objective is to prove:

✅ A cluster can be fully restored after Argo CD is deleted, and once reinstalled, all applications are automatically reconciled from Git.

✅ The App-of-Apps architecture ensures that GitOps principles are maintained throughout the recovery process.

✅ Zero manual intervention is required to redeploy workloads after a disaster.

---

## 🎯 Disaster Recovery Objectives

After completing this guide, you will be able to:

- ✔️ Back up Argo CD and application namespaces
- ✔️ Delete Argo CD completely
- ✔️ Restore Kubernetes objects using Velero
- ✔️ Reinstall Argo CD
- ✔️ Automatically recover all workloads via GitOps
- ✔️ Validate the integrity of restored applications
- ✔️ Implement backup schedules and retention policies

---

## 🧠 High-Level DR Flow

```
Applications running (Deployment, Pod, Service)
        ↓
Argo CD managing workloads (App-of-Apps)
        ↓
Velero takes snapshot backup
        ↓
Backup stored in MinIO (S3-compatible)
        ↓
Simulate Disaster: Delete Argo CD namespace
        ↓
Kubernetes cluster has no Argo CD or apps
        ↓
Velero Restore: Recover all resources
        ↓
Reinstall Argo CD
        ↓
Root-App syncs from Git
        ↓
Child-Apps deploy workloads from actions/
        ↓
Applications fully operational
```

---

## 🏗️ Architecture Overview

```
GitHub Repo (Source of Truth)
        |
        v
Argo CD (App-of-Apps Pattern)
  ├── root-app (Master)
  ├── deployment-app
  ├── pod-app
  └── service-app
        |
        v
Kubernetes Cluster
  ├── argocd namespace (Argo CD control plane)
  ├── demo namespace (Application workloads)
  └── velero namespace (Backup orchestration)
        |
        v
Velero Backup Engine
        |
        v
MinIO S3-Compatible Storage
```

---

## 📦 Components Used

| Component | Purpose | Version |
|-----------|---------|---------|
| **Argo CD** | GitOps controller for continuous deployment | Latest stable |
| **Velero** | Backup & restore orchestration | v1.8.0+ |
| **MinIO** | S3-compatible object storage for backups | Latest |
| **kind** | Kubernetes-in-Docker (local testing) | Latest |
| **EC2 Ubuntu** | Host environment (production ready) | 20.04 LTS+ |
| **kubectl** | Kubernetes command-line client | v1.24+ |

---

## 📂 Namespaces Used

| Namespace | Purpose | Critical |
|-----------|---------|----------|
| **argocd** | Argo CD control plane components | Yes |
| **demo** | Application workloads (deployments, pods, services) | Yes |
| **velero** | Velero backup components and schedules | Yes |
| **kube-system** | Kubernetes system components | Optional |

---

## ⚙️ Prerequisites

Before starting the DR workflow, ensure you have:

- ✅ Kubernetes cluster running (kind or EC2)
- ✅ Docker installed (for MinIO)
- ✅ kubectl configured and authenticated
- ✅ Argo CD deployed with the App-of-Apps pattern (root-app + child apps)
- ✅ Applications deployed in the `demo` namespace
- ✅ Git repository with application manifests
- ✅ Sufficient storage for backups (MinIO)

**Verify Prerequisites:**

```bash
# Check kubectl connectivity
kubectl cluster-info

# Verify Argo CD is running
kubectl get pods -n argocd

# Verify applications are deployed
kubectl get applications -n argocd
kubectl get pods -n demo
```

---

## 📥 Step 1: Install Velero CLI

The Velero CLI is required to manage backups and restore operations.

### Download and Install

```bash
# Download the latest Velero release
curl -LO https://github.com/vmware-tanzu/velero/releases/latest/download/velero-linux-amd64.tar.gz

# Extract the archive
tar -xvf velero-linux-amd64.tar.gz

# Move the binary to system path
sudo mv velero-linux-amd64/velero /usr/local/bin/

# Verify installation
velero version --client-only
```

### ✅ Expected Outcome

```
Client:
  Version: v1.x.x
  Git commit: xxxxxxx
```

---

## 🗄️ Step 2: MinIO Setup (Backup Storage)

MinIO is an S3-compatible object storage that serves as the backup destination for Velero.

### Run MinIO Container

```bash
# Start MinIO with Docker
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minio \
  -e MINIO_ROOT_PASSWORD=minio123 \
  minio/minio server /data --console-address ":9001"
```

### Verify MinIO is Running

```bash
# Check container status
docker ps | grep minio

# Access MinIO Console
# Open: http://localhost:9001
# Username: minio
# Password: minio123
```

### ✅ Expected Outcome

- ✔️ MinIO container running
- ✔️ Console accessible on `http://<host>:9001`
- ✔️ Can log in with provided credentials

### Get Docker Bridge Gateway IP

```bash
# Get the Docker bridge gateway (used as MinIO endpoint)
docker network inspect bridge \
  --format '{{(index .IPAM.Config 0).Gateway}}'
```

### ✅ Expected Outcome

```
172.17.0.1
```

**Note:** This IP is used as the MinIO endpoint for Velero configuration.

---

## 🔐 Step 3: Create Velero Credentials

Velero requires AWS-compatible credentials to access MinIO.

### Create Credentials File

Create a file named `credentials-velero`:

```ini
[default]
aws_access_key_id=minio
aws_secret_access_key=minio123
```

### Verify File

```bash
# Check file was created
cat credentials-velero

# Ensure proper permissions
chmod 600 credentials-velero
```

### ✅ Expected Outcome

- ✔️ File `credentials-velero` created
- ✔️ Contains MinIO credentials
- ✔️ File permissions set to 600

---

## 🚀 Step 4: Install Velero (with MinIO Backend)

This step deploys Velero in the Kubernetes cluster and configures it to use MinIO for backups.

### Install Velero

```bash
# Install Velero with MinIO backend
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket velero \
  --secret-file ./credentials-velero \
  --use-volume-snapshots=false \
  --backup-location-config \
    region=minio,\
    s3ForcePathStyle="true",\
    s3Url=http://172.17.0.1:9000
```

**Note:** Replace `172.17.0.1` with your Docker bridge gateway IP if different.

### ✅ Expected Outcome

```
Velero is installed! ⛅
Please note the following before you get started:
  * Credentials are stored as a secret called velero-credentials in the velero namespace
  * Backups are stored in a bucket called velero in MinIO
  * Schedules can be created with `velero schedule create`
  * Restore can be performed with `velero restore create`
```

---

## 🔍 Step 5: Verify Velero Installation

### Check Velero Pods

```bash
# List all Velero pods
kubectl get pods -n velero

# Check Velero deployment status
kubectl get deployment -n velero

# View Velero logs
kubectl logs -n velero -l app.kubernetes.io/name=velero -f
```

### ✅ Expected Outcome

```
NAME                     READY   STATUS    RESTARTS   AGE
velero-xxxxx             1/1     Running   0          2m
velero-metrics-xxxxx     1/1     Running   0          2m
```

### Check Backup Storage Location

```bash
# Get backup storage locations
velero backup-location get

# Describe the backup location
velero backup-location describe default
```

### ✅ Expected Outcome

```
NAME      PHASE       ACCESS MODE
default   Available   ReadWrite
```

---

## 📸 Step 6: Create Initial Backup

Before simulating a disaster, create a backup of the entire Argo CD and application workloads.

### Create Backup Command

```bash
# Create a backup including argocd and demo namespaces
velero backup create demo-dr-backup \
  --include-namespaces argocd,demo \
  --wait
```

**Options Explained:**
- `--include-namespaces argocd,demo`: Backup only these namespaces
- `--wait`: Wait for backup to complete before returning

### ✅ Expected Outcome

```
Backup request "demo-dr-backup" submitted successfully.
Waiting for backup to complete...
Backup completed with status: Completed
```

### Verify Backup Details

```bash
# Describe the backup
velero backup describe demo-dr-backup

# Get detailed logs
velero backup logs demo-dr-backup

# List all backups
velero backup get
```

### ✅ Expected Outcome

```
Name:         demo-dr-backup
Namespace:    velero
Labels:       velero.io/storage-location=default
Phase:        Completed
Items backed up:  120+
Items requested:  120+
```

---

## 💣 Step 7: Simulate Disaster - Delete Argo CD

This step simulates a complete failure by deleting the Argo CD namespace and all associated resources.

### Delete Argo CD Namespace

```bash
# Delete the argocd namespace (includes all Argo CD components)
kubectl delete namespace argocd

# Verify deletion
kubectl get namespace argocd
```

### ✅ Expected Outcome

```
Error from server (NotFound): namespaces "argocd" not found
```

### Verify Applications are Gone

```bash
# Check for Argo CD applications
kubectl get applications -A

# List all namespaces
kubectl get namespaces
```

### ✅ Expected Outcome

```
No resources found
```

### Verify Application Workloads Status

```bash
# Check if application pods still exist
kubectl get pods -n demo

# List resources in demo namespace
kubectl get all -n demo
```

### ✅ Expected Outcome

```
NAME                READY   STATUS        RESTARTS   AGE
app-pod             0/1     Terminating   0          10m
```

**Note:** Without Argo CD managing the applications, they will be subject to normal Kubernetes garbage collection and may start terminating.

---

## 🔄 Step 8: Restore From Backup

Restore all backed-up resources (Argo CD and applications) from the Velero backup.

### Create Restore Request

```bash
# Restore from the backup
velero restore create demo-dr-restore \
  --from-backup demo-dr-backup \
  --wait
```

### ✅ Expected Outcome

```
Restore request "demo-dr-restore" submitted successfully.
Waiting for restore to complete...
Restore completed with status: Completed
```

### Check Restore Status

```bash
# Describe the restore
velero restore describe demo-dr-restore

# View restore logs
velero restore logs demo-dr-restore

# List all restores
velero restore get
```

### ✅ Expected Outcome

```
Name:         demo-dr-restore
Namespace:    velero
Status:       Completed
Phase:        Completed
Items restored:  120+
Items requested:  120+
```

---

## 🔁 Step 9: Post-Restore Validation

After restoration, verify that all namespaces and resources have been recovered.

### Check Namespaces

```bash
# List all namespaces
kubectl get namespaces

# Verify argocd namespace exists
kubectl get namespace argocd
```

### ✅ Expected Outcome

```
NAME              STATUS   AGE
argocd            Active   2m
demo              Active   2m
velero            Active   5m
kube-system       Active   20m
default           Active   20m
```

### Check Argo CD Application Resources

```bash
# List Argo CD applications
kubectl get applications -n argocd

# Describe the root application
kubectl describe application root-app -n argocd
```

### ✅ Expected Outcome

```
NAME             NAMESPACE   CLUSTER   AUTH MODELS   REPO
root-app         argocd      in-cluster              default
deployment-app   argocd      in-cluster              default
pod-app          argocd      in-cluster              default
service-app      argocd      in-cluster              default
```

**Note:** Applications may show as `Unknown` status because Argo CD controller is not running yet.

### Check Argo CD Pods Status

```bash
# List Argo CD pods
kubectl get pods -n argocd

# Check pod status details
kubectl get pods -n argocd -o wide
```

### ✅ Expected Outcome

```
NAME                                    READY   STATUS    RESTARTS   AGE
argocd-application-controller-0         0/1     Pending   0          1m
argocd-dex-server-xxxxxxx               0/1     Pending   0          1m
argocd-redis-xxxxxxx                    0/1     Pending   0          1m
argocd-repo-server-xxxxxxx              0/1     Pending   0          1m
argocd-server-xxxxxxx                   0/1     Pending   0          1m
```

**Status Explanation:** Pods are pending because Argo CD hasn't been reinstalled yet.

---

## 🔁 Step 10: Reinstall Argo CD

Reinstall Argo CD using the official manifest. Since the Application CRs were restored, Argo CD will automatically start managing them.

### Install Argo CD

```bash
# Apply the Argo CD manifest (stable version)
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for Argo CD to be ready
kubectl wait --for=condition=available \
  --timeout=300s \
  deployment/argocd-server \
  -n argocd
```

### ✅ Expected Outcome

```
deployment.apps/argocd-server condition met
```

### Verify Argo CD Pods are Running

```bash
# List Argo CD pods
kubectl get pods -n argocd

# Check for any errors
kubectl get pods -n argocd -o wide
```

### ✅ Expected Outcome

```
NAME                                    READY   STATUS    RESTARTS   AGE
argocd-application-controller-0         1/1     Running   0          2m
argocd-dex-server-xxxxxxx               1/1     Running   0          2m
argocd-redis-xxxxxxx                    1/1     Running   0          2m
argocd-repo-server-xxxxxxx              1/1     Running   0          2m
argocd-server-xxxxxxx                   1/1     Running   0          2m
```

---

## ♻️ Step 11: GitOps Reconciliation

Once Argo CD is running, it will automatically reconcile all applications from Git. The App-of-Apps pattern ensures that the root application manages all child applications.

### Monitor Application Reconciliation

```bash
# Watch application sync status
kubectl get applications -n argocd --watch

# Check root-app status
kubectl get application root-app -n argocd -o yaml | grep -A 10 "status:"
```

### ✅ Expected Outcome - Root App Status

```
Name:         root-app
Namespace:    argocd
Status:       Synced
Health:       Healthy
Sync Result:  OK
```

### Verify Child Applications are Syncing

```bash
# List all applications
kubectl get applications -n argocd

# Describe each application
kubectl describe application deployment-app -n argocd
kubectl describe application pod-app -n argocd
kubectl describe application service-app -n argocd
```

### ✅ Expected Outcome - Child Apps Status

```
NAME             SYNCED   HEALTHY   STATUS   AGE
root-app         Synced   Healthy   OK       3m
deployment-app   Synced   Healthy   OK       3m
pod-app          Synced   Healthy   OK       3m
service-app      Synced   Healthy   OK       3m
```

### Verify Application Workloads are Deployed

```bash
# List pods in demo namespace
kubectl get pods -n demo

# Check deployment status
kubectl get deployments -n demo

# Verify services are created
kubectl get services -n demo
```

### ✅ Expected Outcome

```
NAME                     READY   STATUS    RESTARTS   AGE
deployment-xxxxx         2/2     Running   0          2m
pod-xxxxx                1/1     Running   0          2m

NAME                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment-xxxxx         2       2            2           2m

NAME          TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)
service-app   ClusterIP   10.96.xxx.xxx   <none>        8080/TCP
```

---

## 🧠 Key Observations and Benefits

### 1. **Velero Restores Argo CD CRs**
- Velero backup includes Application Custom Resource Definitions (CRDs)
- When restored, all Application objects are present in the cluster

### 2. **Argo CD Pulls from Git**
- Argo CD controller starts monitoring the restored Application CRs
- It pulls the latest manifests from the configured Git repository
- No manual intervention is required

### 3. **App-of-Apps Pattern Ensures Automatic Reconciliation**
- `root-app` automatically discovers and manages child applications
- Child applications deploy workloads from the `actions/` directory
- Full infrastructure is reconciled automatically

### 4. **Git is the Single Source of Truth**
- All manifest definitions come from Git
- Even if Kubernetes objects are lost, they are recreated from Git
- Zero manual redeployment required

### 5. **Complete Infrastructure Recovery**
- Deployments, pods, services are all recreated
- Network policies, ConfigMaps, Secrets are restored
- StatefulSet data requires separate snapshot management

---

## ⚠️ Production Best Practices

### 1. **Use Managed Object Storage**
```bash
# Instead of MinIO, use cloud-native solutions:
# AWS S3
# Google Cloud Storage (GCS)
# Azure Blob Storage
# These are more reliable and scalable for production
```

### 2. **Enable Velero Schedules**
```bash
# Create automated backup schedules
velero schedule create daily-backup \
  --schedule="0 2 * * *" \
  --include-namespaces argocd,demo,kube-system \
  --ttl 720h0m0s
```

### 3. **Encrypt Backups**
```bash
# Enable encryption for sensitive data
velero backup create encrypted-backup \
  --include-namespaces argocd,demo \
  --encryption-key your-encryption-key
```

### 4. **Store Credentials Securely**
- Use HashiCorp Vault
- Use AWS Secrets Manager
- Use Kubernetes Secrets with RBAC restrictions
- Never commit credentials to Git

### 5. **Test Restore Procedures Regularly**
- Schedule monthly DR drills
- Document recovery time objectives (RTO)
- Document recovery point objectives (RPO)
- Validate that restored applications work correctly

### 6. **Monitor Backup Health**
```bash
# Setup Prometheus/Grafana to monitor Velero
# Alert on failed backups
# Track backup size and duration

velero backup get
velero restore get
```

### 7. **Retention Policies**
```bash
# Define backup retention
velero backup create retention-backup \
  --include-namespaces argocd,demo \
  --ttl 168h0m0s  # Keep for 7 days
```

### 8. **Volume Snapshots for Stateful Apps**
```bash
# For stateful applications (databases, etc.)
velero install \
  --use-volume-snapshots=true \
  --snapshot-location-config ...
```

---

## 🔄 Advanced Scenarios

### Selective Restoration
```bash
# Restore only specific namespaces
velero restore create partial-restore \
  --from-backup demo-dr-backup \
  --include-namespaces demo
```

### Restore to Different Cluster
```bash
# Copy backup from MinIO to another cluster
# Restore on destination cluster
velero restore create cluster-migration \
  --from-backup demo-dr-backup
```

### Backup Individual Applications
```bash
# Backup only specific applications
velero backup create app-specific-backup \
  --selector app.kubernetes.io/name=my-app
```

---

## ❌ Troubleshooting

### Issue: Backup Fails
```bash
# Check Velero logs
kubectl logs -n velero -l app.kubernetes.io/name=velero

# Check backup status
velero backup describe <backup-name>
velero backup logs <backup-name>
```

### Issue: Restore Shows Errors
```bash
# Check restore status
velero restore describe <restore-name>

# Get detailed restore logs
velero restore logs <restore-name>

# Check for specific errors
kubectl get events -n velero --sort-by='.lastTimestamp'
```

### Issue: MinIO Connectivity
```bash
# Test MinIO connectivity from Velero pod
kubectl exec -it <velero-pod> -n velero -- bash
aws s3 ls --endpoint-url=http://172.17.0.1:9000 --no-sign-request

# Verify MinIO is running
docker logs minio
```

### Issue: Application CRs Not Found
```bash
# Check if Velero included CRDs
velero backup describe <backup-name> | grep -i crd

# Manually apply CRDs if missing
kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/crds.yaml
```

---

## 📊 Performance Considerations

### Backup Size Optimization
- Exclude non-critical namespaces
- Use selective backup labels
- Implement backup retention policies
- Compress backups where possible

### Recovery Time
- Smaller backups restore faster
- Network bandwidth affects restore duration
- Consider scheduling backups during off-peak hours

### Storage Requirements
- Estimate backup size based on cluster data
- Plan MinIO storage accordingly
- Implement cleanup policies to prevent disk overflow

### Example Storage Calculation
```
Cluster Size: 50 applications × 100 resources = 5,000 resources
Average Resource Size: ~2KB
Backup Size: 5,000 × 2KB = 10MB per backup
Daily Backup: 10MB × 7 days = 70MB per week
Monthly Backups: 70MB × 4 weeks = 280MB per month
Yearly: 280MB × 12 months = 3.36GB per year
```

---

## 🏁 Complete Recovery Validation Checklist

- [ ] Velero CLI installed and verified
- [ ] MinIO running and accessible
- [ ] Velero installed in Kubernetes cluster
- [ ] Backup storage location available
- [ ] Initial backup created and verified
- [ ] Argo CD deleted successfully
- [ ] Applications confirmed deleted
- [ ] Velero restore completed
- [ ] Namespaces restored
- [ ] Application CRs restored
- [ ] Argo CD reinstalled
- [ ] Argo CD pods running and healthy
- [ ] Applications synced from Git
- [ ] All child applications healthy
- [ ] Workloads deployed in demo namespace
- [ ] Services accessible and functioning
- [ ] No manual redeployment needed

---

## 🎯 Success Criteria

✅ **Recovery Successful If:**
1. Argo CD is running and operational
2. All Application CRs are present and synced
3. Root-app manages child applications correctly
4. All workloads in `demo` namespace are running
5. Services are accessible and responding
6. No manual intervention was required after restore
7. Git remained as the single source of truth

---

## 📚 Additional Resources

- [Velero Official Documentation](https://velero.io/)
- [MinIO S3 Documentation](https://min.io/docs/)
- [Argo CD App of Apps Pattern](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/#app-of-apps-pattern)
- [Kubernetes Backup Best Practices](https://kubernetes.io/docs/tasks/administer-cluster/disaster-recovery/)
- [Argo CD Disaster Recovery](https://argo-cd.readthedocs.io/en/stable/operator-manual/disaster-recovery/)

---

## 📝 Summary

This guide demonstrates a **complete backup and disaster recovery solution** for Kubernetes workloads managed by Argo CD using the **App-of-Apps pattern**.

**Key Takeaways:**
- 🔄 Velero provides reliable backup and restore capabilities
- 🗄️ MinIO serves as a cost-effective S3-compatible backup storage
- 🚀 App-of-Apps pattern enables automatic reconciliation from Git
- ✅ Zero manual redeployment after disasters
- 🛡️ Git remains the single source of truth for all infrastructure

This setup mirrors **real-world production DR strategies** used by platform teams managing enterprise Kubernetes deployments.

---

**Last Updated:** January 15, 2026
**Version:** 1.0.0
**Status:** Production Ready
