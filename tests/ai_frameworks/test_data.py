"""Shared test data for all AI framework adapter tests."""

PII_SAMPLES = {
    "email": "john.doe@example.com",
    "phone_us": "(555) 123-4567",
    "ssn": "123-45-6789",
    "credit_card": "4111-1111-1111-1111",
    "medical_record": "MRN-12345678",
}

EXPECTED_REDACTIONS = {
    "email": "[EMAIL_REDACTED]",
    "phone_us": "[PHONE_REDACTED]",
    "ssn": "[SSN_REDACTED]",
    "credit_card": "[CARD_REDACTED]",  # Note: SDK uses CARD not CREDIT_CARD
    "medical_record": "[MEDICAL_RECORD_REDACTED]",
}

CLEAN_SAMPLES = [
    "Hello, how can I help?",
    "The weather is nice today.",
    "Please process this request.",
]

# Test messages with embedded PII
PII_MESSAGES = {
    "email_message": f"Contact me at {PII_SAMPLES['email']} for more info.",
    "phone_message": f"Call me at {PII_SAMPLES['phone_us']} tomorrow.",
    "ssn_message": f"My SSN is {PII_SAMPLES['ssn']} for verification.",
    "credit_card_message": f"Use card {PII_SAMPLES['credit_card']} for payment.",
    "mixed_message": f"Email: {PII_SAMPLES['email']}, Phone: {PII_SAMPLES['phone_us']}",
}

# Expected redacted versions
REDACTED_MESSAGES = {
    "email_message": f"Contact me at {EXPECTED_REDACTIONS['email']} for more info.",
    "phone_message": f"Call me at {EXPECTED_REDACTIONS['phone_us']} tomorrow.",
    "ssn_message": f"My SSN is {EXPECTED_REDACTIONS['ssn']} for verification.",
    "credit_card_message": f"Use card {EXPECTED_REDACTIONS['credit_card']} for payment.",
    "mixed_message": f"Email: {EXPECTED_REDACTIONS['email']}, Phone: {EXPECTED_REDACTIONS['phone_us']}",
}
