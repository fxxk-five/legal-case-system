## ADDED Requirements

### Requirement: All public traffic enters through unified cloud ingress
The production system SHALL expose Web, API, and download traffic through a unified cloud ingress stack composed of managed DNS, TLS termination, public edge protection, and cloud load balancing, rather than binding the service identity to a single manually managed host entrypoint.

#### Scenario: Public access uses managed edge path
- **WHEN** an end user opens the Web app, mini-program API, or an authorized download link
- **THEN** the request enters through the configured cloud domain and edge ingress path before reaching application workloads or object storage

### Requirement: Production access is independent from local office or developer networks
The production system SHALL remain startable, deployable, and reachable without dependence on a developer workstation, office LAN, or residential network, with all serving components hosted inside cloud infrastructure.

#### Scenario: Service remains available after local network loss
- **WHEN** a developer device, office router, or non-cloud local network becomes unavailable
- **THEN** the production service continues running in the cloud and remains reachable to end users through the public cloud domain

### Requirement: Public endpoints use role-appropriate optimized delivery paths
The production system SHALL separate delivery concerns so that API traffic, static assets, and large file transfers can use optimized cloud paths such as load balancing, CDN, and cloud object storage delivery according to the endpoint type.

#### Scenario: Large file traffic avoids the API hot path
- **WHEN** a user downloads a large report or evidence attachment
- **THEN** the request is served through the cloud storage or CDN delivery path instead of consuming routine API application throughput

### Requirement: Public ingress exposes health-aware fail-safe behavior
The production system SHALL define health checks, upstream readiness, and cutover behavior at the cloud ingress layer so that unhealthy workloads are removed from service and releases can be cut over without manual host-by-host intervention.

#### Scenario: Unhealthy revision is removed from ingress
- **WHEN** a newly deployed workload revision fails readiness checks
- **THEN** the cloud ingress keeps routing traffic to healthy revisions and does not expose the unhealthy revision as the primary serving path
