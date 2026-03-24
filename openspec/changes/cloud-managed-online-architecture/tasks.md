## 1. Blueprint And Platform Baseline

- [x] 1.1 Update the core blueprint documents so the first commercial production baseline is `CVM + Docker Compose + COS`, with later evolution to `CLB + multi-CVM` or `TCR + TKE`
- [x] 1.2 Define the first-wave Tencent Cloud resource inventory covering `VPC`, `CVM`, system disk, snapshot policy, security group, `COS`, domain, `DNSPod`, `SSL`, and cloud monitoring
- [x] 1.3 Define the second-wave resource inventory covering `CDN`, `WAF`, `CLB`, `TencentDB PostgreSQL`, `TencentDB Redis`, `TDMQ/CMQ`, `TCR`, `TKE`, and secret management
- [x] 1.4 Produce environment and secret mapping for dev, staging, and production without relying on host `.env` files as the long-term production source of truth

## 2. CVM + COS Storage Delivery

- [x] 2.1 Implement a `COS` storage backend alongside the existing local backend abstraction
- [x] 2.2 Add signed upload policy or temporary credential issuance endpoints for Web and mini-program clients
- [x] 2.3 Refactor upload completion flow so object metadata is confirmed and stored after direct-to-COS upload
- [x] 2.4 Refactor download and report access flows to return signed COS or CDN-backed URLs instead of local file responses in production
- [x] 2.5 Add cloud storage lifecycle, retention, and delete handling rules to the file and report domain flows

## 3. CVM Production Runtime

- [x] 3.1 Produce a single-CVM production runbook for `nginx`, `web`, `backend`, `ai-worker`, `report-service`, `postgres`, and `redis`
- [x] 3.2 Remove uploaded-file and report persistence dependence on host local volumes in production
- [x] 3.3 Add backup, recovery, snapshot, log rotation, and restart policy guidance for single-CVM production
- [x] 3.4 Keep `DB Queue` as a first-wave compatible mode while adding retry, dead-task handling, and worker supervision guardrails

## 4. Scale-Out Evolution

- [x] 4.1 Define the migration path from single-CVM database/cache to managed `TencentDB PostgreSQL` and `TencentDB Redis`
- [x] 4.2 Define the scale-out path to `CLB + multi-CVM` once traffic, tenant count, or availability targets exceed single-host limits
- [x] 4.3 Introduce a cloud queue adapter for `TDMQ/CMQ` while keeping the current DB queue for local development and first-wave compatibility
- [x] 4.4 Define the optional container-platform path to `TCR + TKE` after the CVM + COS baseline is stable

## 5. Public Ingress And Cutover

- [x] 5.1 Define the first-wave public ingress path `DNS/SSL -> Nginx(CVM)` and align Web, API, mini-program, and download domains
- [x] 5.2 Define when and how to add `CDN`, `WAF`, and `CLB` to the public ingress without changing the file storage model
- [x] 5.3 Execute a staged migration plan for storage, runtime, and public traffic with rollback checkpoints after each cutover wave
- [ ] 5.4 Run end-to-end validation for upload, analyze, report generation, signed download, and client mini-program access on the cloud domain
