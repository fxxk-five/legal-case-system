## ADDED Requirements

### Requirement: Production workloads run on cloud-managed runtime
The production system SHALL run `api`, `web`, `ai-worker`, and `report-service` as independently deployable workloads on a cloud-managed container runtime, and SHALL NOT require an interactive SSH session or manual host process supervision to stay online.

#### Scenario: Cloud rollout keeps services online
- **WHEN** a production release is triggered
- **THEN** the cloud runtime deploys the new workload revisions with health checks and keeps the previous revision available until the new revision is ready

### Requirement: Production dependencies use managed cloud data services
The production system SHALL use managed cloud services for PostgreSQL, Redis, and asynchronous task delivery, and these dependencies MUST be reachable only through cloud private networking rather than public host port exposure.

#### Scenario: Internal dependencies stay off the public internet
- **WHEN** the production environment is provisioned
- **THEN** PostgreSQL, Redis, and the task queue are exposed only on private cloud networks and are not directly reachable from the public internet

### Requirement: Production configuration is cloud-governed
The production system SHALL source sensitive configuration from cloud-managed secret or configuration services, and MUST NOT treat a manually edited host `.env` file as the production source of truth.

#### Scenario: Secrets rotate without host file edits
- **WHEN** an operator updates an AI key, storage credential, or JWT signing secret
- **THEN** the new value is published through cloud-managed configuration or secret distribution and the workload restart path does not require hand-editing a host file
