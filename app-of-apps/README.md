# App of Apps

## Overview
The App of Apps approach is a powerful way to manage multiple Kubernetes applications using a single Argo CD instance. This method allows for better organization, scalability, and management of applications in a Kubernetes environment.

## Purpose of Folder Structure
The folder structure is designed to facilitate the organization and management of Kubernetes resources and Argo CD applications. Each folder serves a specific purpose, ensuring that related files are grouped together for easy access and maintenance. The structure follows the App of Apps pattern where:
- The `root/` directory contains the master application that orchestrates everything.
- The `argocd-apps/` directory contains all child applications that are managed by the root application.
- The `actions/` directory contains the actual Kubernetes resource definitions that the child applications deploy.

## Folder Structure
The project is organized into the following structure:
```
app-of-apps/
	app-of-apps/
		actions/
			deployment/
				deployment.yaml
			pod/
				pod.yaml
			service/
				service.yaml
		argocd-apps/
			deploymentApp.yaml
			podApp.yaml
			serviceApp.yaml
		root/
			rootApp.yaml
```

### Description of Folders
- **actions/**: Contains the definitions for various Kubernetes resources.
  - **deployment/**: Holds the deployment configurations.
    - `deployment.yaml`: Configuration for deploying the application.
  - **pod/**: Contains pod specifications.
    - `pod.yaml`: Configuration for the pods.
  - **service/**: Contains service definitions.
    - `service.yaml`: Configuration for the services.
- **argocd-apps/**: Contains Argo CD application definitions.
  - `deploymentApp.yaml`: Argo CD application for deployment.
  - `podApp.yaml`: Argo CD application for pods.
  - `serviceApp.yaml`: Argo CD application for services.
- **root/**: Contains the root application configuration.
  - `rootApp.yaml`: Configuration for the root application.

## Implementation
The implementation of the App of Apps approach involves defining applications in Argo CD that point to the respective Kubernetes resources. Each application can be managed independently, allowing for easier updates and rollbacks.

### Steps to Implement
1. **Define Applications**: Create YAML files for each application in the `argocd-apps/` directory.
2. **Configure Resources**: Define the necessary Kubernetes resources in the `actions/` directory.
3. **Deploy with Argo CD**: Use Argo CD to deploy the applications defined in the `argocd-apps/` directory.

## Root Application (rootApp.yaml)
The `rootApp.yaml` is the cornerstone of the App of Apps approach. It serves as the main entry point and orchestrator for all child applications in the system.

### Structure of rootApp.yaml
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Fenil-Gajjar/k8s-actions.git
    targetRevision: HEAD
    path: app-of-apps/argocd-apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### How rootApp.yaml Works
1. **Entry Point**: The root application acts as a single entry point for managing the entire system. Instead of registering multiple applications in Argo CD, you only need to create the root application.

2. **Source Repository**: The `source.repoURL` and `source.path` fields point to the `app-of-apps/argocd-apps` directory, which contains all child application manifests (`deploymentApp.yaml`, `podApp.yaml`, `serviceApp.yaml`, etc.).

3. **Automatic Discovery**: When Argo CD syncs the root application, it automatically discovers and manages all child applications defined in the `argocd-apps/` directory.

4. **Centralized Sync Policy**: The sync policy defined in the root application (with `prune: true` and `selfHeal: true`) ensures:
   - **Prune**: Automatically removes resources that are no longer defined in the manifests.
   - **Self-Heal**: Automatically corrects any drift between the desired state and the actual state in the cluster.

5. **Hierarchical Management**: The root application manages child applications, which in turn manage the actual Kubernetes resources (deployments, pods, services) defined in the `actions/` directory.

### How It Enables the App of Apps Approach
- **Modular Architecture**: By pointing to the `argocd-apps/` directory, the root application enables a modular architecture where each child application is a separate, manageable unit.
- **Scalability**: Adding new applications is as simple as creating new application manifests in the `argocd-apps/` directory. The root application automatically discovers and manages them.
- **Separation of Concerns**: The root application handles the orchestration, while child applications handle specific workloads or services.
- **Easy Management**: Teams can add, update, or remove child applications without modifying the root application itself.

## Behavior
The App of Apps approach allows for:
- **Scalability**: Easily add or remove applications as needed.
- **Isolation**: Each application can be managed independently, reducing the risk of affecting other applications.
- **Centralized Management**: Manage all applications from a single Argo CD instance.

## Potential Working
This approach is particularly useful in microservices architectures where multiple services need to be deployed and managed. It allows teams to work on different services independently while maintaining a cohesive deployment strategy. The ability to add child application manifests means that future workloads can be defined and deployed without significant restructuring of the existing setup.

Additionally, by simply adding child application manifests to the `argocd-apps/` folder, you can deploy the workloads defined in the `actions/` directory seamlessly. This modular approach ensures that as new applications are developed, they can be integrated into the existing structure without disrupting current deployments.

## Conclusion
The App of Apps approach simplifies the management of multiple Kubernetes applications, providing a structured and scalable solution for modern application deployment. By organizing applications and their resources effectively, teams can enhance their deployment workflows and improve overall efficiency.

---

## Suggestions for Improvement
- Include diagrams to illustrate the architecture.
- Add examples of common use cases.
- Provide troubleshooting tips for common issues.
- Include links to relevant documentation for further reading.

---