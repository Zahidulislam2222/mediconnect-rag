# MediConnect Architecture Summary

## Overview
Production-grade multi-cloud healthcare platform with 7 microservices, 4 Lambda functions, and 35 FHIR R4 resource types. Three-cloud architecture: AWS (primary), GCP (backup compute + analytics), Azure (K8s orchestration).

## Services

| Service | Language | Port | Purpose |
|---------|----------|------|---------|
| patient-service | Node.js/TS | 8081 | Registration, vitals, FHIR Patient, allergies, immunizations, care plans, MPI, GDPR |
| doctor-service | Node.js/TS | 8082 | EHR, e-prescriptions, SNOMED CT, lab orders, CDS Hooks, med-reconciliation |
| booking-service | Node.js/TS | 8083 | Appointments, Stripe billing, subscriptions, prior auth, Google Calendar |
| communication-service | Node.js/TS | 8084 | WebSocket chat, Chime video, AI circuit breaker, chatbot |
| admin-service | Python/FastAPI | 8085 | User management, audit logs, system health, subscription dashboard |
| staff-service | Node.js/TS | 8086 | Shifts, tasks, announcements, staff directory |
| dicom-service | Python/FastAPI | 8005 | DICOM upload, de-identification, PACS, FHIR ImagingStudy |

## Shared Utilities (backend_v2/shared/)
- aws-config.ts: Regional AWS SDK client factories
- audit.ts: FHIR AuditEvent logging (7-year TTL)
- kms-crypto.ts: KMS envelope encryption for PHI
- logger.ts: Winston PII masking
- breach-detection.ts: Rate-based anomaly detection
- validation.ts: Zod request validation middleware
- event-bus.ts: SQS + Kafka event pipeline (35 EventTypes)
- kafka.ts: Kafka client with MSK IAM auth
- subscription.ts: Subscription plans, discount calculation, rate cap
- notifications.ts: SES email notifications (11 types)
- emergency-access.ts: HIPAA break-glass override

## Data Flow
Patient App → x-user-region header → API Gateway → Service → Regional DynamoDB
US users → us-east-1 resources | EU users → eu-central-1 resources

## Infrastructure
- 414 Terraform resources (370 AWS + 40 GCP + 4 Azure)
- 46 DynamoDB tables (23 × 2 regions)
- 7 Kafka topics (MSK Serverless)
- 26 SQS queues with DLQ
- CI/CD: GitHub Actions (5-stage pipeline)
