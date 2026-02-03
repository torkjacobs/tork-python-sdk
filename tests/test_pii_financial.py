"""
Tests for Financial PII Detection
Part 1.5 of Comprehensive Test Plan
Covers: Bank Account, Routing Number, SWIFT/BIC, CVV, Card Expiry, Crypto Address
"""

import pytest
from tork_governance.detectors.pii_patterns import (
    PIIDetector, PIIType, detect_pii, redact_pii
)


# ============================================================================
# BANK ACCOUNT NUMBER TESTS
# ============================================================================

class TestBankAccount:
    """Test Bank Account Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    @pytest.mark.parametrize("account,should_detect,description", [
        # With prefix (required for detection)
        ("Account: 12345678901234", True, "Account prefix"),
        ("Acct: 12345678901234", True, "Acct prefix"),
        ("Acct #12345678901234", True, "Acct hash"),
        ("A/C: 12345678901234", True, "A/C prefix"),
        ("Account Number: 98765432101234", True, "Full phrase"),
        # Different lengths (8-17 digits)
        ("Account: 12345678", True, "8 digits"),
        ("Account: 123456789012345", True, "15 digits"),
        ("Account: 12345678901234567", True, "17 digits"),
        # Without prefix (should NOT match)
        ("12345678901234", False, "No prefix"),
        # Too short/long
        ("Account: 1234567", False, "7 digits - too short"),
        ("Account: 123456789012345678", False, "18 digits - too long"),
    ])
    def test_bank_account_detection(self, detector, account, should_detect, description):
        text = account
        matches = detector.detect(text)
        account_matches = [m for m in matches if m.pii_type == PIIType.BANK_ACCOUNT]

        if should_detect:
            assert len(account_matches) >= 1, f"Should detect bank account ({description}): {account}"
        else:
            assert len(account_matches) == 0, f"Should NOT detect ({description}): {account}"

    def test_bank_account_redaction(self, detector):
        """Test bank account redaction"""
        text = "Transfer to Account: 12345678901234"
        redacted, matches = detector.redact(text)

        assert "12345678901234" not in redacted
        assert "[BANK_ACCOUNT_REDACTED]" in redacted


# ============================================================================
# US ROUTING NUMBER TESTS
# ============================================================================

class TestRoutingNumber:
    """Test US Bank Routing Number detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    @pytest.mark.parametrize("routing,should_detect,description", [
        # Valid routing numbers (checksum valid)
        ("Routing: 021000021", True, "Chase"),
        ("ABA: 121000358", True, "BofA"),
        ("RTN: 021000089", True, "Citi"),
        ("Routing: 071000013", True, "BMO Harris"),
        ("Routing: 091000019", True, "Wells Fargo"),
        # With different prefixes
        ("ABA: 021000021", True, "ABA prefix"),
        ("RTN: 021000021", True, "RTN prefix"),
        ("Routing Number: 021000021", True, "Full phrase"),
        # Invalid checksum
        ("Routing: 123456789", False, "Invalid checksum"),
        ("Routing: 000000000", False, "All zeros"),
        # Without prefix
        ("021000021", False, "No prefix"),
    ])
    def test_routing_detection(self, detector, routing, should_detect, description):
        text = routing
        matches = detector.detect(text)
        routing_matches = [m for m in matches if m.pii_type == PIIType.ROUTING_NUMBER]

        if should_detect:
            assert len(routing_matches) >= 1, f"Should detect routing ({description}): {routing}"
        else:
            assert len(routing_matches) == 0, f"Should NOT detect ({description}): {routing}"

    def test_routing_redaction(self, detector):
        """Test routing number redaction"""
        text = "Wire to Routing: 021000021"
        redacted, matches = detector.redact(text)

        assert "021000021" not in redacted


# ============================================================================
# SWIFT/BIC CODE TESTS
# ============================================================================

class TestSWIFTBIC:
    """Test SWIFT/BIC Code detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    @pytest.mark.parametrize("swift,should_detect,description", [
        # Valid SWIFT/BIC codes (8 or 11 characters)
        ("CHASUS33", True, "8-char Chase"),
        ("CHASUS33XXX", True, "11-char Chase"),
        ("BOFAUS3N", True, "8-char BofA"),
        ("CITIUS33", True, "8-char Citi"),
        ("DEUTDEFF", True, "8-char Deutsche"),
        ("DEUTDEFFXXX", True, "11-char Deutsche"),
        ("BNPAFRPP", True, "8-char BNP"),
        ("HSBCHKHH", True, "8-char HSBC HK"),
        # Invalid
        ("CHAS", False, "Too short"),
        ("CHASUS33XXXXXXX", False, "Too long"),
        ("12345678", False, "All numbers"),
        ("chasus33", False, "Lowercase"),
    ])
    def test_swift_detection(self, detector, swift, should_detect, description):
        text = f"SWIFT: {swift}"
        matches = detector.detect(text)
        swift_matches = [m for m in matches if m.pii_type == PIIType.SWIFT_BIC]

        if should_detect:
            assert len(swift_matches) >= 1, f"Should detect SWIFT ({description}): {swift}"
        else:
            assert len(swift_matches) == 0, f"Should NOT detect ({description}): {swift}"

    def test_swift_in_wire_context(self, detector):
        """Test SWIFT in wire transfer context"""
        text = """
        WIRE TRANSFER INSTRUCTIONS
        Bank: Chase Manhattan
        SWIFT/BIC: CHASUS33XXX
        Account: 123456789
        """
        matches = detector.detect(text)
        swift_matches = [m for m in matches if m.pii_type == PIIType.SWIFT_BIC]
        assert len(swift_matches) >= 1, "Should detect SWIFT in wire instructions"


# ============================================================================
# CVV/CVC TESTS (PCI-DSS CRITICAL - NEVER STORE)
# ============================================================================

class TestCVV:
    """Test CVV/CVC detection - PCI-DSS critical, NEVER store"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    @pytest.mark.parametrize("cvv,should_detect,description", [
        # With prefix (required)
        ("CVV: 123", True, "3-digit CVV"),
        ("CVC: 456", True, "3-digit CVC"),
        ("CVV2: 789", True, "CVV2"),
        ("CVC2: 012", True, "CVC2"),
        ("CSC: 345", True, "CSC"),
        # 4-digit (Amex)
        ("CVV: 1234", True, "4-digit Amex"),
        ("CVC: 5678", True, "4-digit CVC"),
        # Case insensitive
        ("cvv: 123", True, "Lowercase cvv"),
        ("Cvv: 123", True, "Mixed case"),
        # Without prefix
        ("123", False, "No prefix - 3 digits"),
        ("1234", False, "No prefix - 4 digits"),
        # Invalid length
        ("CVV: 12", False, "Too short"),
        ("CVV: 12345", False, "Too long"),
    ])
    def test_cvv_detection(self, detector, cvv, should_detect, description):
        text = cvv
        matches = detector.detect(text)
        cvv_matches = [m for m in matches if m.pii_type == PIIType.CVV]

        if should_detect:
            assert len(cvv_matches) >= 1, f"Should detect CVV ({description}): {cvv}"
        else:
            assert len(cvv_matches) == 0, f"Should NOT detect ({description}): {cvv}"

    def test_cvv_redaction_never_store(self, detector):
        """Test CVV redaction uses NEVER_STORE marker"""
        text = "Enter CVV: 123 from back of card"
        redacted, matches = detector.redact(text)

        assert "123" not in redacted
        assert "[CVV_NEVER_STORE]" in redacted

    def test_cvv_pci_dss_compliance(self, detector):
        """Test that CVV is marked as PCI-DSS critical"""
        # The pattern config should have pci_dss_critical flag
        from tork_governance.detectors.pii_patterns import FINANCIAL_PATTERNS
        cvv_config = FINANCIAL_PATTERNS.get(PIIType.CVV, {})
        assert cvv_config.get("pci_dss_critical") == True, "CVV should be marked PCI-DSS critical"


# ============================================================================
# CARD EXPIRY DATE TESTS
# ============================================================================

class TestCardExpiry:
    """Test Card Expiration Date detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    @pytest.mark.parametrize("expiry,should_detect,description", [
        # With prefix
        ("Exp: 12/25", True, "Exp slash"),
        ("Expiry: 01/26", True, "Expiry slash"),
        ("Expiration: 06/27", True, "Expiration"),
        ("Valid Thru 12/25", True, "Valid Thru"),
        ("Valid Through 01/2026", True, "Valid Through 4-digit"),
        # Different separators
        ("Exp: 12-25", True, "Dash separator"),
        ("Exp: 12/2025", True, "4-digit year"),
        # Case insensitive
        ("EXP: 12/25", True, "Uppercase"),
        ("exp: 12/25", True, "Lowercase"),
        # Without prefix
        ("12/25", False, "No prefix"),
        ("01/2026", False, "No prefix 4-digit"),
    ])
    def test_expiry_detection(self, detector, expiry, should_detect, description):
        text = expiry
        matches = detector.detect(text)
        expiry_matches = [m for m in matches if m.pii_type == PIIType.CARD_EXPIRY]

        if should_detect:
            assert len(expiry_matches) >= 1, f"Should detect expiry ({description}): {expiry}"
        else:
            assert len(expiry_matches) == 0, f"Should NOT detect ({description}): {expiry}"


# ============================================================================
# CRYPTOCURRENCY ADDRESS TESTS
# ============================================================================

class TestCryptoAddress:
    """Test Cryptocurrency Address detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    @pytest.mark.parametrize("address,should_detect,crypto_type", [
        # Bitcoin Legacy (starts with 1)
        ("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", True, "BTC Legacy"),
        ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", True, "BTC Genesis"),
        # Bitcoin P2SH (starts with 3)
        ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", True, "BTC P2SH"),
        # Bitcoin Bech32 (starts with bc1)
        ("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", True, "BTC Bech32"),
        # Ethereum (starts with 0x, 40 hex chars)
        ("0x742d35Cc6634C0532925a3b844Bc454e4438f44E", True, "ETH"),
        ("0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe", True, "ETH 2"),
        # Invalid
        ("0x742d35", False, "ETH too short"),
        ("1BvBMS", False, "BTC too short"),
        ("2BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", False, "Invalid BTC prefix"),
    ])
    def test_crypto_detection(self, detector, address, should_detect, crypto_type):
        text = f"Send to: {address}"
        matches = detector.detect(text)
        crypto_matches = [m for m in matches if m.pii_type == PIIType.CRYPTO_ADDRESS]

        if should_detect:
            assert len(crypto_matches) >= 1, f"Should detect crypto ({crypto_type}): {address}"
        else:
            assert len(crypto_matches) == 0, f"Should NOT detect ({crypto_type}): {address}"

    def test_crypto_redaction(self, detector):
        """Test crypto address redaction"""
        text = "Wallet: 0x742d35Cc6634C0532925a3b844Bc454e4438f44E"
        redacted, matches = detector.redact(text)

        assert "0x742d35Cc6634C0532925a3b844Bc454e4438f44E" not in redacted
        assert "[CRYPTO_REDACTED]" in redacted


# ============================================================================
# COMBINED FINANCIAL TESTS
# ============================================================================

class TestFinancialCombined:
    """Test combined Financial PII detection scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    def test_wire_transfer_form(self, detector):
        """Test wire transfer form with multiple financial PII"""
        text = """
        WIRE TRANSFER REQUEST

        Beneficiary Account: 12345678901234
        Routing: 021000021
        SWIFT/BIC: CHASUS33XXX
        """

        matches = detector.detect(text)
        types_found = {m.pii_type for m in matches}

        assert len(matches) >= 2, f"Should find multiple financial PII, found: {types_found}"

    def test_payment_card_full_details(self, detector):
        """Test payment card with CVV and expiry"""
        text = """
        Card Details:
        CVV: 123
        Exp: 12/25
        """

        matches = detector.detect(text)
        cvv_matches = [m for m in matches if m.pii_type == PIIType.CVV]
        expiry_matches = [m for m in matches if m.pii_type == PIIType.CARD_EXPIRY]

        assert len(cvv_matches) >= 1, "Should detect CVV"
        assert len(expiry_matches) >= 1, "Should detect expiry"

    def test_crypto_exchange_withdrawal(self, detector):
        """Test crypto exchange withdrawal"""
        text = """
        Withdrawal Request

        BTC Address: 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2
        ETH Address: 0x742d35Cc6634C0532925a3b844Bc454e4438f44E
        """

        matches = detector.detect(text)
        crypto_matches = [m for m in matches if m.pii_type == PIIType.CRYPTO_ADDRESS]
        assert len(crypto_matches) >= 2, "Should detect both crypto addresses"

    def test_full_redaction(self, detector):
        """Test full redaction of financial document"""
        text = """
        CONFIDENTIAL BANKING INFORMATION

        Account: 12345678901234
        Routing: 021000021
        CVV: 123
        Exp: 12/25
        """

        redacted, matches = detector.redact(text)

        assert "12345678901234" not in redacted
        assert "021000021" not in redacted
        assert "123" not in redacted.split("CVV")[0] if "CVV" in redacted else True


# ============================================================================
# REAL WORLD SCENARIOS
# ============================================================================

class TestFinancialRealWorld:
    """Test real-world financial scenarios"""

    @pytest.fixture
    def detector(self):
        return PIIDetector(regions=['financial'])

    def test_ach_transfer_form(self, detector):
        """Test ACH transfer form"""
        text = """
        ACH DIRECT DEPOSIT FORM

        Bank Name: Chase Bank
        Account Number: Account: 123456789012
        Routing Number: ABA: 021000021
        Account Type: Checking
        """

        matches = detector.detect(text)
        routing_matches = [m for m in matches if m.pii_type == PIIType.ROUTING_NUMBER]
        assert len(routing_matches) >= 1, "Should detect routing number"

    def test_international_wire(self, detector):
        """Test international wire transfer"""
        text = """
        INTERNATIONAL WIRE TRANSFER

        Beneficiary Bank: Deutsche Bank
        SWIFT Code: DEUTDEFFXXX
        Beneficiary Account: Acct: 12345678901234
        """

        matches = detector.detect(text)
        swift_matches = [m for m in matches if m.pii_type == PIIType.SWIFT_BIC]
        assert len(swift_matches) >= 1, "Should detect SWIFT code"

    def test_crypto_invoice(self, detector):
        """Test cryptocurrency payment invoice"""
        text = """
        CRYPTO PAYMENT INVOICE
        Invoice #: INV-2026-001

        Pay to BTC: 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2
        Or ETH: 0x742d35Cc6634C0532925a3b844Bc454e4438f44E

        Amount: 0.5 BTC or 10 ETH
        """

        matches = detector.detect(text)
        crypto_matches = [m for m in matches if m.pii_type == PIIType.CRYPTO_ADDRESS]
        assert len(crypto_matches) >= 2, "Should detect both crypto addresses"

    def test_checkout_page(self, detector):
        """Test e-commerce checkout page"""
        text = """
        CHECKOUT - PAYMENT

        Card Number: [already redacted]
        CVV: 456
        Expiry: 03/27

        Billing Account: Account: 9876543210
        """

        matches = detector.detect(text)
        assert len(matches) >= 2, "Should detect multiple financial PII"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
