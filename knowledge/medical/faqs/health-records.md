# Health Records FAQs

## What health records can I access?
You can view your allergies, immunizations, care plans, prescriptions, lab results, vitals, and appointment history — all in FHIR R4 format.

## How do I export my health data?
Go to Settings > GDPR > Export Data. MediConnect exports your complete health record as a FHIR Bundle with a SHA-256 integrity hash. This is compliant with GDPR Article 20 (data portability).

## How do I delete my data?
Go to Settings > GDPR > Request Erasure. There is a 30-day grace period during which you can cancel the request. After 30 days, your data is permanently anonymized across all systems including chat history, appointments, prescriptions, and analytics.

## Is my data encrypted?
Yes. All patient health information (PHI) is encrypted using AWS KMS envelope encryption both at rest and in transit. Your data in the browser is encrypted with AES-GCM 256-bit encryption.

## Can my doctor see my records?
Your doctor can only see records relevant to your care during an active appointment. Emergency access (break-glass) is available with strict time limits, reason codes, and full audit trail per HIPAA regulations.

## Where is my data stored?
US patients: data stored in AWS us-east-1 (Virginia).
EU patients: data stored in AWS eu-central-1 (Frankfurt).
Your data never crosses regions — this complies with GDPR Schrems II requirements.

## What is FHIR?
FHIR (Fast Healthcare Interoperability Resources) is the international standard for exchanging healthcare information electronically. MediConnect supports 35 FHIR R4 resource types and US Core profiles.

## Can I share my records with another provider?
Yes. Use the Data Export feature to download your FHIR Bundle, which any FHIR-compatible healthcare system can import. We also support Blue Button 2.0 for CMS-compliant data access.
