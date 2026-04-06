#!/bin/bash
set -u

# Healthcare Compliance Scanner v1
# Pattern-based static analysis for healthcare codebases
# Works on any Node.js or Python healthcare project

PROJECT_ROOT="/project/${PROJECT_PATH:-mediconnect-project/mediconnect-infrastructure-production}"
PROJECT_TYPE="${PROJECT_TYPE:-auto}"
REPORT_FILE="/reports/healthcare-compliance-report.json"
SCAN_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

pass=0; fail=0; warn=0; skip=0
checks="[]"

add_check() {
  local id="$1" name="$2" status="$3" details="$4"
  checks=$(echo "$checks" | jq --arg id "$id" --arg name "$name" --arg status "$status" --arg details "$details" \
    '. + [{"id": $id, "name": $name, "status": $status, "details": $details}]')
  case "$status" in
    PASS) pass=$((pass + 1)) ;;
    FAIL) fail=$((fail + 1)) ;;
    WARN) warn=$((warn + 1)) ;;
    SKIP) skip=$((skip + 1)) ;;
  esac
}

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "ERROR: Project not found at $PROJECT_ROOT"
  echo "Set PROJECT_PATH env var to the relative path under /project/"
  exit 1
fi

# Auto-detect project type
if [ "$PROJECT_TYPE" = "auto" ]; then
  if [ -n "$(find "$PROJECT_ROOT" -maxdepth 3 -name 'package.json' -not -path '*/node_modules/*' 2>/dev/null | head -1)" ]; then
    PROJECT_TYPE="node"
  elif [ -n "$(find "$PROJECT_ROOT" -maxdepth 3 -name 'requirements.txt' -o -name 'pyproject.toml' 2>/dev/null | head -1)" ]; then
    PROJECT_TYPE="python"
  else
    PROJECT_TYPE="unknown"
  fi
fi

echo "=== Healthcare Compliance Scanner v1 ==="
echo "Project: $PROJECT_ROOT"
echo "Type:    $PROJECT_TYPE"
echo "Date:    $SCAN_DATE"
echo ""

# Helper: search source files (excluding node_modules, .git, dist, etc.)
search_src() {
  rg "$1" "$PROJECT_ROOT" \
    --glob '!node_modules' --glob '!.git' --glob '!dist' --glob '!build' \
    --glob '!*.lock' --glob '!*.min.js' --glob '!*.map' \
    -l 2>/dev/null || true
}

search_src_count() {
  rg "$1" "$PROJECT_ROOT" \
    --glob '!node_modules' --glob '!.git' --glob '!dist' --glob '!build' \
    --glob '!*.lock' --glob '!*.min.js' --glob '!*.map' \
    -c 2>/dev/null | awk -F: '{sum+=$NF} END {print sum+0}'
}

# ============================================
# AUTH — Authentication & Authorization
# ============================================

echo "--- Authentication & Authorization ---"

# AUTH-001: Auth middleware exists
auth_files=$(search_src '(auth|authenticate|authorize|middleware.*auth|requireAuth|isAuthenticated|verifyToken|cognitoAuth)' | wc -l)
if [ "$auth_files" -gt 0 ]; then
  add_check "AUTH-001" "Auth middleware exists" "PASS" "Found auth patterns in $auth_files files"
else
  add_check "AUTH-001" "Auth middleware exists" "FAIL" "No auth middleware patterns found"
fi

# AUTH-002: Role-based access control
rbac_files=$(search_src '(role|permission|doctor|patient|admin|staff|pharmacist).*(check|guard|authorize|allow|deny|require)' | wc -l)
if [ "$rbac_files" -gt 0 ]; then
  add_check "AUTH-002" "Role-based access control exists" "PASS" "Found RBAC patterns in $rbac_files files"
else
  add_check "AUTH-002" "Role-based access control exists" "FAIL" "No RBAC patterns found"
fi

# AUTH-003: Unprotected routes check
route_files=$(search_src '(router\.(get|post|put|patch|delete)|app\.(get|post|put|patch|delete)|@(Get|Post|Put|Patch|Delete)|def (get|post|put|patch|delete))' | wc -l)
unprotected=$( (rg '(router\.(get|post|put|patch|delete)|app\.(get|post|put|patch|delete))' "$PROJECT_ROOT" \
  --glob '!node_modules' --glob '!.git' --glob '!dist' --glob '!*.lock' \
  -l 2>/dev/null || true) | while read -r f; do
    if [ -n "$f" ] && ! rg -q '(auth|middleware|protect|guard|verify)' "$f" 2>/dev/null; then
      echo "$f"
    fi
  done | wc -l)
if [ "$route_files" -eq 0 ]; then
  add_check "AUTH-003" "All API routes have auth middleware" "SKIP" "No route files detected"
elif [ "$unprotected" -eq 0 ]; then
  add_check "AUTH-003" "All API routes have auth middleware" "PASS" "All $route_files route files reference auth"
else
  add_check "AUTH-003" "All API routes have auth middleware" "WARN" "$unprotected of $route_files route files may lack auth middleware"
fi

# ============================================
# PHI — PHI/PII Protection
# ============================================

echo "--- PHI/PII Protection ---"

# PHI-001: Patient data encryption
encrypt_count=$(search_src_count '(encrypt|KMS|kms|AES|aes256|crypto\.(create|cipher)|bcrypt|argon2|hashField)')
if [ "$encrypt_count" -gt 0 ]; then
  add_check "PHI-001" "Patient data encryption references exist" "PASS" "Found $encrypt_count encryption references"
else
  add_check "PHI-001" "Patient data encryption references exist" "FAIL" "No encryption patterns found in source"
fi

# PHI-002: No console.log with patient data
phi_leaks=$( (rg 'console\.(log|error|warn|info).*\b(patient|ssn|birthDate|dateOfBirth|dob|socialSecurity|medicalRecord)\b' "$PROJECT_ROOT" \
  --glob '!node_modules' --glob '!.git' --glob '!dist' --glob '!*.lock' --glob '!*.test.*' --glob '!*.spec.*' \
  -c 2>/dev/null || true) | awk -F: '{sum+=$NF} END {print sum+0}')
if [ "$phi_leaks" -eq 0 ]; then
  add_check "PHI-002" "No console.log leaking patient data" "PASS" "No PHI in console output statements"
else
  add_check "PHI-002" "No console.log leaking patient data" "FAIL" "Found $phi_leaks console statements referencing patient data fields"
fi

# PHI-003: Error responses don't leak PHI
error_phi=$( (rg '(catch|error|err).*\b(res\.(json|send|status)|return|response).*\b(patient|record|ssn)\b' "$PROJECT_ROOT" \
  --glob '!node_modules' --glob '!.git' --glob '!dist' --glob '!*.lock' \
  -c 2>/dev/null || true) | awk -F: '{sum+=$NF} END {print sum+0}')
if [ "$error_phi" -eq 0 ]; then
  add_check "PHI-003" "Error responses don't leak PHI" "PASS" "No PHI leakage patterns in error handlers"
else
  add_check "PHI-003" "Error responses don't leak PHI" "WARN" "Found $error_phi potential PHI leaks in error handlers"
fi

# ============================================
# AUDIT — Audit Logging
# ============================================

echo "--- Audit Logging ---"

# AUDIT-001: Audit log function exists
audit_files=$(search_src '(auditLog|audit_log|createAuditEntry|logAudit|AuditTrail|audit\.log|writeAudit)' | wc -l)
if [ "$audit_files" -gt 0 ]; then
  add_check "AUDIT-001" "Audit log function exists" "PASS" "Found audit logging in $audit_files files"
else
  add_check "AUDIT-001" "Audit log function exists" "FAIL" "No audit logging function found"
fi

# AUDIT-002: Audit captures required fields (who, what, when, which patient)
audit_fields=$(search_src_count '(userId|user_id|actor|who).*(action|event|what).*(timestamp|createdAt|when).*(patientId|patient_id|subject)')
if [ "$audit_fields" -gt 0 ]; then
  add_check "AUDIT-002" "Audit logs capture who/what/when/which" "PASS" "Found $audit_fields structured audit entries"
else
  # Check partial
  partial=$(search_src_count '(userId|user_id|actor).*(action|event)')
  if [ "$partial" -gt 0 ]; then
    add_check "AUDIT-002" "Audit logs capture who/what/when/which" "WARN" "Found partial audit fields ($partial refs) — verify all 4 fields are captured"
  else
    add_check "AUDIT-002" "Audit logs capture who/what/when/which" "FAIL" "No structured audit field patterns found"
  fi
fi

# AUDIT-003: Audit log retention/TTL
ttl_count=$(search_src_count '(TTL|ttl|retention|expir|TimeToLive|time_to_live).*\b(audit|log)\b')
if [ "$ttl_count" -gt 0 ]; then
  add_check "AUDIT-003" "Audit log retention configured" "PASS" "Found $ttl_count retention/TTL references"
else
  add_check "AUDIT-003" "Audit log retention configured" "WARN" "No explicit audit log retention/TTL found"
fi

# ============================================
# CONSENT — Consent & GDPR
# ============================================

echo "--- Consent & GDPR ---"

# CONSENT-001: Consent check before data processing
consent_count=$(search_src_count '(consent|checkConsent|verifyConsent|hasConsent|consentGiven|userConsent)')
if [ "$consent_count" -gt 0 ]; then
  add_check "CONSENT-001" "Consent check exists" "PASS" "Found $consent_count consent references"
else
  add_check "CONSENT-001" "Consent check exists" "FAIL" "No consent check patterns found"
fi

# CONSENT-002: Data erasure/deletion function (right to be forgotten)
erasure_count=$(search_src_count '(deleteUser|eraseData|deletePatient|removePersonalData|rightToErasure|gdprDelete|purgeUser|forgetMe)')
if [ "$erasure_count" -gt 0 ]; then
  add_check "CONSENT-002" "Data erasure function exists (GDPR Art. 17)" "PASS" "Found $erasure_count erasure references"
else
  add_check "CONSENT-002" "Data erasure function exists (GDPR Art. 17)" "FAIL" "No data erasure/deletion function found"
fi

# CONSENT-003: Data export function (GDPR portability)
export_count=$(search_src_count '(exportData|dataExport|downloadData|portability|exportPatient|getUserData)')
if [ "$export_count" -gt 0 ]; then
  add_check "CONSENT-003" "Data export/portability function exists (GDPR Art. 20)" "PASS" "Found $export_count export references"
else
  add_check "CONSENT-003" "Data export/portability function exists (GDPR Art. 20)" "FAIL" "No data export function found"
fi

# CONSENT-004: Consent model tracks legal basis
legal_basis=$(search_src_count '(legalBasis|legal_basis|lawfulBasis|consentType|consent_type|processingBasis|purpose)')
if [ "$legal_basis" -gt 0 ]; then
  add_check "CONSENT-004" "Consent model tracks legal basis" "PASS" "Found $legal_basis legal basis references"
else
  add_check "CONSENT-004" "Consent model tracks legal basis" "WARN" "No explicit legal basis tracking found in consent model"
fi

# ============================================
# FHIR — FHIR Resource Compliance
# ============================================

echo "--- FHIR Compliance ---"

# FHIR-001: FHIR resourceType in responses
fhir_rt=$(search_src_count 'resourceType')
if [ "$fhir_rt" -gt 0 ]; then
  add_check "FHIR-001" "FHIR resources include resourceType" "PASS" "Found $fhir_rt resourceType references"
else
  add_check "FHIR-001" "FHIR resources include resourceType" "SKIP" "No FHIR resourceType references found (may not use FHIR)"
fi

# FHIR-002: FHIR meta.profile for validation
fhir_profile=$(search_src_count 'meta\.profile|meta\[.profile')
if [ "$fhir_rt" -gt 0 ] && [ "$fhir_profile" -gt 0 ]; then
  add_check "FHIR-002" "FHIR resources include meta.profile" "PASS" "Found $fhir_profile meta.profile references"
elif [ "$fhir_rt" -gt 0 ]; then
  add_check "FHIR-002" "FHIR resources include meta.profile" "WARN" "FHIR resources found but no meta.profile for validation"
else
  add_check "FHIR-002" "FHIR resources include meta.profile" "SKIP" "No FHIR resources detected"
fi

# FHIR-003: Patient resource required fields
fhir_patient=$(search_src_count '(identifier|name|gender|birthDate).*Patient|Patient.*(identifier|name|gender|birthDate)')
if [ "$fhir_rt" -gt 0 ] && [ "$fhir_patient" -gt 0 ]; then
  add_check "FHIR-003" "Patient resource includes required fields" "PASS" "Found $fhir_patient Patient field references"
elif [ "$fhir_rt" -gt 0 ]; then
  add_check "FHIR-003" "Patient resource includes required fields" "WARN" "FHIR found but Patient required fields not clearly structured"
else
  add_check "FHIR-003" "Patient resource includes required fields" "SKIP" "No FHIR resources detected"
fi

# ============================================
# VALIDATE — Input Validation
# ============================================

echo "--- Input Validation ---"

# VALIDATE-001: Request validation middleware
validation_count=$(search_src_count '(validate|validation|validator|sanitize|Joi|Zod|yup|ajv|express-validator|class-validator|celebrate)' )
if [ "$validation_count" -gt 0 ]; then
  add_check "VALIDATE-001" "Input validation framework used" "PASS" "Found $validation_count validation references"
else
  add_check "VALIDATE-001" "Input validation framework used" "FAIL" "No validation framework found (Joi, Zod, yup, ajv, etc.)"
fi

# VALIDATE-002: Request body schemas defined
schema_count=$(search_src_count '(schema|Schema|bodySchema|requestSchema|\.object\(|\.string\(\)|z\.object|Joi\.object)')
if [ "$schema_count" -gt 0 ]; then
  add_check "VALIDATE-002" "Request body schemas defined" "PASS" "Found $schema_count schema definitions"
else
  add_check "VALIDATE-002" "Request body schemas defined" "WARN" "No explicit request body schemas found"
fi

# ============================================
# ENCRYPT — Encryption
# ============================================

echo "--- Encryption ---"

# ENCRYPT-001: Database SSL/TLS
db_ssl=$(search_src_count '(ssl|tls|sslmode|useSSL|require_ssl|encrypted).*\b(database|db|postgres|mysql|mongo|dynamo|connection)\b')
if [ "$db_ssl" -gt 0 ]; then
  add_check "ENCRYPT-001" "Database connections use SSL/TLS" "PASS" "Found $db_ssl DB SSL/TLS references"
else
  add_check "ENCRYPT-001" "Database connections use SSL/TLS" "WARN" "No explicit DB SSL/TLS configuration found"
fi

# ENCRYPT-002: S3 server-side encryption
s3_sse=$(search_src_count '(ServerSideEncryption|SSESpecification|BucketEncryption|aws:kms|AES256|server_side_encryption)')
if [ "$s3_sse" -gt 0 ]; then
  add_check "ENCRYPT-002" "S3 operations use server-side encryption" "PASS" "Found $s3_sse SSE references"
else
  s3_usage=$(search_src_count '(s3Client|S3|putObject|getObject|s3\.)')
  if [ "$s3_usage" -gt 0 ]; then
    add_check "ENCRYPT-002" "S3 operations use server-side encryption" "FAIL" "S3 used ($s3_usage refs) but no encryption configured"
  else
    add_check "ENCRYPT-002" "S3 operations use server-side encryption" "SKIP" "No S3 usage detected"
  fi
fi

# ENCRYPT-003: KMS or key management
kms_count=$(search_src_count '(KMS|kms|KeyManagement|key_management|masterKey|master_key|encryption_key|encryptionKey|AWS\.KMS|kms\.)')
if [ "$kms_count" -gt 0 ]; then
  add_check "ENCRYPT-003" "Key management service (KMS) used" "PASS" "Found $kms_count KMS references"
else
  add_check "ENCRYPT-003" "Key management service (KMS) used" "WARN" "No KMS/key management references found"
fi

# ============================================
# REGION — Multi-region (if applicable)
# ============================================

echo "--- Multi-region ---"

# REGION-001: Region routing
region_count=$(search_src_count '(region|Region|AWS_REGION|GCP_REGION|AZURE_REGION|x-region|regionRouter|RegionConfig)')
if [ "$region_count" -gt 5 ]; then
  add_check "REGION-001" "Region-aware configuration exists" "PASS" "Found $region_count region references"
elif [ "$region_count" -gt 0 ]; then
  add_check "REGION-001" "Region-aware configuration exists" "WARN" "Found $region_count region references — verify multi-region routing"
else
  add_check "REGION-001" "Region-aware configuration exists" "SKIP" "No multi-region patterns detected"
fi

# ============================================
# Generate Report
# ============================================

echo ""
echo "=== Scan Summary ==="
echo "PASS: $pass | FAIL: $fail | WARN: $warn | SKIP: $skip"
echo ""

report=$(jq -n \
  --arg project "$PROJECT_ROOT" \
  --arg date "$SCAN_DATE" \
  --arg framework "healthcare-compliance-v1" \
  --argjson pass "$pass" \
  --argjson fail "$fail" \
  --argjson warn "$warn" \
  --argjson skip "$skip" \
  --argjson checks "$checks" \
  '{
    project: $project,
    scan_date: $date,
    framework: $framework,
    summary: { pass: $pass, fail: $fail, warn: $warn, skip: $skip },
    checks: $checks
  }')

echo "$report" > "$REPORT_FILE"
echo "Report saved to: $REPORT_FILE"

# Print detailed results
echo ""
echo "=== Detailed Results ==="
echo "$report" | jq -r '.checks[] | "\(.status)  \(.id)  \(.name)  — \(.details)"'
