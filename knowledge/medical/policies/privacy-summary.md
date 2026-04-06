# MediConnect Privacy Summary

## What data we collect
- Account information (name, email, date of birth)
- Health records (allergies, immunizations, prescriptions, vitals)
- Appointment history
- Payment information (processed by Stripe — we never see card numbers)
- Chat conversations with AI assistant

## How we protect your data
- All health data encrypted with AWS KMS (at rest and in transit)
- PII masking in all logs (emails, phone numbers, SSNs automatically redacted)
- 7-year audit trail for compliance
- Two-factor authentication available
- Browser data encrypted with AES-GCM 256-bit

## Your rights (GDPR)
- **Access** (Art 15): Export all your data as FHIR Bundle
- **Erasure** (Art 17): Request complete data deletion with 30-day grace period
- **Portability** (Art 20): Download data in standard FHIR format
- **Consent** (Art 7): Manage your consent preferences at any time
- **Withdraw** (Art 7): Withdraw consent without affecting prior processing

## Data residency
- US patients: us-east-1 (Virginia, USA)
- EU patients: eu-central-1 (Frankfurt, Germany)
- Data never crosses regions

## AI chatbot
- This chatbot is an AI assistant, not a medical professional
- Conversations are logged for quality and compliance
- Your messages are scrubbed of personal information before AI processing
- Chat history is included in GDPR data export and erasure
- The AI never stores your personal health information

## Third parties
- AWS: Infrastructure (HIPAA BAA signed)
- Stripe: Payment processing (PCI-DSS Level 1)
- Google Cloud: Analytics and AI fallback
- No data sold to third parties. Ever.
