"""
Tests for the regional detector's "Generic" PII types: url_with_pii and
phone_generic (SDK-PYTHON-REGIONAL-DETECTOR-DECLARES-FIVE-TYPES-WITH-NO-PATTERN).

name, address, and ssn_no_dashes were removed from PIIType instead -- see
README.md ("Removed regional types") for why.
"""

import pytest
from tork_governance.detectors.pii_patterns import PIIDetector, PIIType


class TestURLWithPII:
    """Test URL-with-PII-query-parameter detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("url,should_detect", [
        ("https://example.com/reset?email=john@example.com&token=abc123", True),
        ("http://api.example.com/user?ssn=123456789", True),
        ("https://x.com/callback?api_key=SECRET123", True),
        ("https://x.com/callback?apikey=SECRET123", True),
        ("https://example.com/login?password=hunter2", True),
        # No PII-indicative query param
        ("https://example.com/products?category=shoes&sort=price", False),
        ("https://example.com/search?q=hello+world", False),
        # No query string at all
        ("Visit https://example.com for more info", False),
    ])
    def test_url_with_pii_detection(self, detector, url, should_detect):
        matches = detector.detect(url)
        url_matches = [m for m in matches if m.pii_type == PIIType.URL_WITH_PII]

        if should_detect:
            assert len(url_matches) >= 1, f"Should detect PII-bearing URL: {url}"
        else:
            assert len(url_matches) == 0, f"Should NOT flag URL: {url}"

    def test_url_with_pii_redaction(self, detector):
        text = "Password reset link: https://example.com/reset?email=john@example.com&token=abc123"
        redacted, matches = detector.redact(text)

        assert "email=john@example.com" not in redacted
        assert "[URL_PII_REDACTED]" in redacted


class TestPhoneGeneric:
    """Test keyword-labeled generic phone number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['universal'])

    @pytest.mark.parametrize("text,should_detect", [
        ("Phone: +254 20 123 4567", True),
        ("Tel: 09-8765-4321", True),
        ("Mobile Number: +81-90-1234-5678", True),
        ("Cell: 022-334-5566", True),
        ("Telephone: +886 2 1234 5678", True),
        # Too few digits to be a real number (E.164 minimum is 7)
        ("Phone: 123", False),
        # Too many digits (E.164 maximum is 15)
        ("Phone: 1234567890123456789", False),
        # No recognized keyword label
        ("Random text with no keyword 022-334-5566", False),
        # Keyword present but no digits follow
        ("The Phone Booth is closed", False),
        # Already a US-format number -- phone_us is the more specific, correct
        # label; phone_generic must not also fire on the identical span.
        ("Cell: 555-123-4567", False),
    ])
    def test_phone_generic_detection(self, detector, text, should_detect):
        matches = detector.detect(text)
        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE_GENERIC]

        if should_detect:
            assert len(phone_matches) >= 1, f"Should detect generic phone: {text}"
        else:
            assert len(phone_matches) == 0, f"Should NOT detect generic phone: {text}"

    def test_phone_generic_redaction(self, detector):
        text = "Reach me: Mobile: +81-90-1234-5678"
        redacted, matches = detector.redact(text)

        assert "+81-90-1234-5678" not in redacted
        assert "[PHONE_GENERIC_REDACTED]" in redacted

    def test_phone_generic_does_not_double_match_a_us_format_number(self, detector):
        """phone_us's pattern already covers this text; phone_generic firing
        too would double-label the identical span and corrupt
        PIIDetector.redact() (see test_pii_type_parity.py)."""
        text = "Cell: 555-123-4567"
        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert PIIType.PHONE_GENERIC not in types_found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
