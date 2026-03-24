## ADDED Requirements

### Requirement: Production evidence and reports live in cloud object storage
The production system SHALL store evidence files, generated reports, and export artifacts in cloud object storage, and MUST NOT rely on local application disks as the durable production storage of record.

#### Scenario: New file is stored in COS
- **WHEN** a user uploads a production evidence file or the system generates a report
- **THEN** the persisted file object is written to cloud object storage and the database stores its cloud storage key and metadata

### Requirement: Uploads use direct-to-object-storage authorization
The production system SHALL provide a signed upload policy or temporary cloud credentials so that Web and mini-program clients can upload files directly to cloud object storage, while the application records metadata and enforces authorization separately.

#### Scenario: Client uploads without proxying file bytes through API
- **WHEN** an authorized user requests an upload policy
- **THEN** the system returns a time-limited cloud upload authorization and the client can send file bytes directly to object storage without streaming the full file through the application server

### Requirement: Downloads use signed cloud delivery
The production system SHALL serve private evidence and report downloads through signed object-storage or CDN-backed URLs, and MUST NOT require the production API service to stream large file bodies from local disk for routine downloads.

#### Scenario: Authorized download returns signed cloud link
- **WHEN** an authorized user requests a report or evidence download
- **THEN** the system returns a time-limited signed cloud delivery path that grants access only to the requested object

### Requirement: Cloud storage objects follow lifecycle and audit controls
The production system SHALL define retention, versioning, and deletion controls for stored objects so that uploads, report generations, and deletes remain auditable and recoverable according to platform policy.

#### Scenario: Delete follows retention policy
- **WHEN** a user deletes a file record or a report is superseded
- **THEN** the underlying cloud object is processed according to the configured retention and recovery policy instead of being silently lost without audit context
