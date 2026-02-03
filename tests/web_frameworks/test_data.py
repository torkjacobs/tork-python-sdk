"""
Shared test data for web framework adapter tests.
"""

# Sample PII values
PII_SAMPLES = {
    "email": "john.doe@example.com",
    "phone_us": "(555) 123-4567",
    "ssn": "123-45-6789",
    "credit_card": "4111111111111111"
}

# Expected redaction patterns
EXPECTED_REDACTIONS = {
    "email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "ssn": "[SSN_REDACTED]",
    "credit_card": "[CARD_REDACTED]"
}

# Sample messages containing PII
PII_MESSAGES = {
    "email_message": f"Contact me at {PII_SAMPLES['email']} for details",
    "phone_message": f"Call me at {PII_SAMPLES['phone_us']}",
    "ssn_message": f"My SSN is {PII_SAMPLES['ssn']}",
    "credit_card_message": f"Card number: {PII_SAMPLES['credit_card']}"
}

# Sample request bodies
REQUEST_BODIES = {
    "clean": {"content": "What is the weather today?"},
    "email_pii": {"content": PII_MESSAGES["email_message"]},
    "phone_pii": {"message": PII_MESSAGES["phone_message"]},
    "ssn_pii": {"text": PII_MESSAGES["ssn_message"]},
    "credit_card_pii": {"prompt": PII_MESSAGES["credit_card_message"]},
}
