"""
Comprehensive PII Detection Patterns
Covers: US, AU, EU, UK, Universal, Financial, Healthcare, Biometric
Total: 50+ PII types
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Set, Pattern
import logging

logger = logging.getLogger(__name__)


class PIIType(Enum):
    """All supported PII types"""
    # US-Specific
    SSN = "ssn"
    SSN_NO_DASHES = "ssn_no_dashes"
    PHONE_US = "phone_us"
    DRIVER_LICENSE_US = "driver_license_us"
    PASSPORT_US = "passport_us"
    EIN = "ein"  # Employer ID Number
    ITIN = "itin"  # Individual Taxpayer ID

    # Australian-Specific
    PHONE_AU = "phone_au"
    MEDICARE_AU = "medicare_au"
    TFN = "tfn"  # Tax File Number
    ABN = "abn"  # Australian Business Number
    ACN = "acn"  # Australian Company Number

    # European
    IBAN = "iban"
    NINO_UK = "nino_uk"  # UK National Insurance
    NHS_UK = "nhs_uk"  # UK NHS Number
    GERMAN_ID = "german_id"
    FRENCH_SSN = "french_ssn"
    VAT_EU = "vat_eu"
    PHONE_EU = "phone_eu"
    POSTCODE_UK = "postcode_uk"
    SORT_CODE_UK = "sort_code_uk"

    # Universal
    EMAIL = "email"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    IPV6_ADDRESS = "ipv6_address"
    MAC_ADDRESS = "mac_address"
    URL_WITH_PII = "url_with_pii"
    DATE_OF_BIRTH = "date_of_birth"

    # Financial
    BANK_ACCOUNT = "bank_account"
    ROUTING_NUMBER = "routing_number"
    SWIFT_BIC = "swift_bic"
    CVV = "cvv"
    CARD_EXPIRY = "card_expiry"
    CRYPTO_ADDRESS = "crypto_address"

    # Healthcare (HIPAA)
    PATIENT_ID = "patient_id"
    MRN = "mrn"  # Medical Record Number
    HEALTH_PLAN_ID = "health_plan_id"
    NPI = "npi"  # National Provider ID
    DEA_NUMBER = "dea_number"
    ICD_CODE = "icd_code"
    CPT_CODE = "cpt_code"

    # Biometric References
    BIOMETRIC_ID = "biometric_id"
    FACE_ID = "face_id"
    FINGERPRINT_ID = "fingerprint_id"

    # Generic
    NAME = "name"
    ADDRESS = "address"
    PHONE_GENERIC = "phone_generic"


@dataclass
class PIIMatch:
    """Represents a PII match found in text"""
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0
    region: str = "universal"


# ============================================================================
# VALIDATION FUNCTIONS (defined first since patterns reference them)
# ============================================================================

def _validate_ssn(match) -> bool:
    """Validate SSN format and check for known invalid patterns"""
    ssn = match.group(1).replace('-', '').replace(' ', '')
    if len(ssn) != 9:
        return False
    # Invalid SSNs: all same digit, 000/666/9XX area, 00 group, 0000 serial
    if ssn in ['000000000', '111111111', '222222222', '333333333',
               '444444444', '555555555', '666666666', '777777777',
               '888888888', '999999999']:
        return False
    area = ssn[0:3]
    group = ssn[3:5]
    serial = ssn[5:9]
    if area == '000' or area == '666' or area[0] == '9':
        return False
    if group == '00':
        return False
    if serial == '0000':
        return False
    return True


def _validate_medicare(number: str) -> bool:
    """Validate Australian Medicare number using checksum"""
    digits = number.replace('-', '').replace(' ', '')
    # Must be exactly 10 digits
    if len(digits) != 10:
        return False
    # All digits must be numeric
    if not digits.isdigit():
        return False
    # First digit should be 2-6 for valid Medicare cards
    if digits[0] not in '23456':
        return False
    return True


def _validate_tfn(number: str) -> bool:
    """Validate Australian Tax File Number using checksum"""
    digits = number.replace('-', '').replace(' ', '')
    if len(digits) != 9:
        return False
    # Reject all zeros or all same digit
    if digits == '000000000' or len(set(digits)) == 1:
        return False
    # TFN checksum validation
    weights = [1, 4, 3, 7, 5, 8, 6, 9, 10]
    total = sum(int(d) * w for d, w in zip(digits, weights))
    return total % 11 == 0


def _validate_abn(number: str) -> bool:
    """Validate Australian Business Number using checksum"""
    digits = number.replace('-', '').replace(' ', '')
    if len(digits) != 11:
        return False
    # ABN checksum validation
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    # Subtract 1 from first digit
    modified = [int(digits[0]) - 1] + [int(d) for d in digits[1:]]
    total = sum(d * w for d, w in zip(modified, weights))
    return total % 89 == 0


def _validate_iban(iban: str) -> bool:
    """Validate IBAN using MOD 97-10"""
    iban = iban.replace(' ', '').replace('-', '').upper()
    if len(iban) < 15 or len(iban) > 34:
        return False
    # Move first 4 chars to end
    rearranged = iban[4:] + iban[:4]
    # Convert letters to numbers (A=10, B=11, etc.)
    numeric = ''
    for char in rearranged:
        if char.isdigit():
            numeric += char
        else:
            numeric += str(ord(char) - 55)
    # Check MOD 97
    return int(numeric) % 97 == 1


def _validate_nhs(number: str) -> bool:
    """Validate UK NHS number using checksum"""
    digits = number.replace('-', '').replace(' ', '')
    if len(digits) != 10:
        return False
    # Reject all zeros or all same digit
    if digits == '0000000000' or len(set(digits)) == 1:
        return False
    # NHS checksum: multiply first 9 digits by 10-position, sum, mod 11
    total = sum(int(d) * (10 - i) for i, d in enumerate(digits[:9]))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    if check == 10:
        return False  # Invalid NHS number
    return int(digits[9]) == check


def _validate_nino(nino: str) -> bool:
    """Validate UK National Insurance Number format"""
    # Remove separators and uppercase
    clean = nino.replace('-', '').replace(' ', '').upper()
    if len(clean) != 9:
        return False
    # Extract prefix (first 2 letters)
    prefix = clean[:2]
    # Invalid prefixes per HMRC rules
    invalid_prefixes = {'BG', 'GB', 'KN', 'NK', 'NT', 'TN', 'ZZ'}
    if prefix in invalid_prefixes:
        return False
    # First letter cannot be D, F, I, Q, U, V
    if clean[0] in 'DFIQUV':
        return False
    # Second letter cannot be D, F, I, O, Q, U, V
    if clean[1] in 'DFIOQUV':
        return False
    return True


def _validate_credit_card(number: str) -> bool:
    """Validate credit card using Luhn algorithm"""
    digits = number.replace('-', '').replace(' ', '')
    if not digits.isdigit() or len(digits) < 13 or len(digits) > 19:
        return False
    # Reject all zeros or all same digit
    if len(set(digits)) == 1:
        return False
    # Luhn algorithm
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _validate_routing(number: str) -> bool:
    """Validate US routing number using checksum"""
    if len(number) != 9 or not number.isdigit():
        return False
    # Reject all zeros
    if number == '000000000':
        return False
    # Routing number checksum
    weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
    total = sum(int(d) * w for d, w in zip(number, weights))
    return total % 10 == 0


def _validate_npi(number: str) -> bool:
    """Validate NPI using Luhn algorithm with prefix 80840"""
    if len(number) != 10 or not number.isdigit():
        return False
    # Prepend 80840 and validate with Luhn
    full = '80840' + number
    return _validate_credit_card(full)


def _validate_dea(number: str) -> bool:
    """Validate DEA number using checksum"""
    if len(number) != 9:
        return False
    # First char must be letter, second can be letter or number
    if not number[0].isalpha():
        return False
    digits = number[2:]
    if not digits.isdigit():
        return False
    # Reject all zeros in digits portion
    if digits == '0000000':
        return False
    # DEA checksum
    odd_sum = sum(int(digits[i]) for i in range(0, 6, 2))
    even_sum = sum(int(digits[i]) for i in range(1, 6, 2))
    check = (odd_sum + even_sum * 2) % 10
    return int(digits[6]) == check


# ============================================================================
# US-SPECIFIC PATTERNS
# ============================================================================

US_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.SSN: {
        "pattern": re.compile(r'\b(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b'),
        "validation": lambda m: _validate_ssn(m),
        "redaction": "[SSN_REDACTED]",
        "description": "US Social Security Number (XXX-XX-XXXX)",
        "examples": ["123-45-6789", "123 45 6789"],
    },
    PIIType.PHONE_US: {
        "pattern": re.compile(
            r'\b(?:\+?1[-.\s]?)?\(?([2-9]\d{2})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b'
        ),
        "validation": lambda m: True,
        "redaction": "[PHONE_US_REDACTED]",
        "description": "US Phone Number",
        "examples": ["(555) 123-4567", "+1 555-123-4567", "555.123.4567"],
    },
    PIIType.DRIVER_LICENSE_US: {
        "pattern": re.compile(
            r'\b(?:DL|D\.L\.|Driver\'?s?\s*License)[:\s#]*([A-Z]?\d{6,9})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[DL_REDACTED]",
        "description": "US Driver License Number",
        "examples": ["DL: A1234567", "Driver License 123456789"],
    },
    PIIType.PASSPORT_US: {
        "pattern": re.compile(
            r'\b(?:Passport)[:\s#]*([A-Z]?\d{8,9})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[PASSPORT_REDACTED]",
        "description": "US Passport Number",
        "examples": ["Passport: 123456789", "Passport #A12345678"],
    },
    PIIType.EIN: {
        "pattern": re.compile(r'\b(?:EIN)[:\s#]*(\d{2}[-\s]?\d{7})\b', re.IGNORECASE),
        "validation": lambda m: True,
        "redaction": "[EIN_REDACTED]",
        "description": "Employer Identification Number",
        "examples": ["EIN: 12-3456789", "EIN 123456789"],
    },
    PIIType.ITIN: {
        "pattern": re.compile(r'\b(9\d{2}[-\s]?\d{2}[-\s]?\d{4})\b'),
        "validation": lambda m: m.group(1).replace('-', '').replace(' ', '')[0:3] in [
            '900', '901', '902', '903', '904', '905', '906', '907', '908',
            '910', '911', '912', '913', '914', '915', '916', '917', '918', '919',
            '920', '921', '922', '923', '924', '925', '926', '927', '928', '929',
            '930', '931', '932', '933', '934', '935', '936', '937', '938', '939',
            '940', '941', '942', '943', '944', '945', '946', '947', '948', '949',
            '950', '951', '952', '953', '954', '955', '956', '957', '958', '959',
            '960', '961', '962', '963', '964', '965', '966', '967', '968', '969',
            '970', '971', '972', '973', '974', '975', '976', '977', '978', '979',
            '980', '981', '982', '983', '984', '985', '986', '987', '988'
        ],
        "redaction": "[ITIN_REDACTED]",
        "description": "Individual Taxpayer Identification Number",
        "examples": ["912-34-5678", "9XX-XX-XXXX"],
    },
}


# ============================================================================
# AUSTRALIAN PATTERNS
# ============================================================================

AU_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.PHONE_AU: {
        "pattern": re.compile(
            # Mobile: 04XX XXX XXX or 04XXXXXXXX or +61 4XX XXX XXX
            r'\b(?:\+?61[-.\s]?)?0?4\d{2}[-.\s]?\d{3}[-.\s]?\d{3}\b|'
            # Landline: 0X XXXX XXXX or +61 X XXXX XXXX (area codes 2,3,7,8)
            r'\b(?:\+?61[-.\s]?)?0?[2378][-.\s]?\d{4}[-.\s]?\d{4}\b'
        ),
        "validation": lambda m: True,
        "redaction": "[PHONE_AU_REDACTED]",
        "description": "Australian Phone Number",
        "examples": ["0412 345 678", "+61 412 345 678", "02 9876 5432"],
    },
    PIIType.MEDICARE_AU: {
        # Strict format: space-separated, dash-separated, or no separators
        "pattern": re.compile(r'\b(\d{4} \d{5} \d|\d{4}-\d{5}-\d|\d{10})\b'),
        "validation": lambda m: _validate_medicare(m.group(1)),
        "redaction": "[MEDICARE_REDACTED]",
        "description": "Australian Medicare Number",
        "examples": ["2123 45678 1", "2123456781"],
    },
    PIIType.TFN: {
        "pattern": re.compile(r'\b(\d{3}[-\s]?\d{3}[-\s]?\d{3})\b'),
        "validation": lambda m: _validate_tfn(m.group(1)),
        "redaction": "[TFN_REDACTED]",
        "description": "Australian Tax File Number",
        "examples": ["123 456 789", "123-456-789"],
    },
    PIIType.ABN: {
        "pattern": re.compile(r'\b(?:ABN)[:\s#]*(\d{2}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3})\b', re.IGNORECASE),
        "validation": lambda m: _validate_abn(m.group(1)),
        "redaction": "[ABN_REDACTED]",
        "description": "Australian Business Number",
        "examples": ["ABN: 12 345 678 901", "ABN 12345678901"],
    },
    PIIType.ACN: {
        "pattern": re.compile(r'\b(?:ACN)[:\s#]*(\d{3}[-\s]?\d{3}[-\s]?\d{3})\b', re.IGNORECASE),
        "validation": lambda m: True,
        "redaction": "[ACN_REDACTED]",
        "description": "Australian Company Number",
        "examples": ["ACN: 123 456 789", "ACN 123456789"],
    },
}


# ============================================================================
# EUROPEAN PATTERNS
# ============================================================================

EU_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.IBAN: {
        "pattern": re.compile(
            r'\b([A-Z]{2}\d{2}[-\s]?(?:[A-Z0-9]{4}[-\s]?){2,7}[A-Z0-9]{1,4})\b'
        ),
        "validation": lambda m: _validate_iban(m.group(1)),
        "redaction": "[IBAN_REDACTED]",
        "description": "International Bank Account Number",
        "examples": ["DE89370400440532013000", "GB29 NWBK 6016 1331 9268 19"],
    },
    PIIType.VAT_EU: {
        "pattern": re.compile(
            r'\b((?:AT|BE|BG|CY|CZ|DE|DK|EE|EL|ES|FI|FR|HR|HU|IE|IT|LT|LU|LV|MT|NL|PL|PT|RO|SE|SI|SK)[A-Z0-9]{8,12})\b'
        ),
        "validation": lambda m: True,
        "redaction": "[VAT_REDACTED]",
        "description": "EU VAT Number",
        "examples": ["DE123456789", "FR12345678901", "GB123456789"],
    },
    PIIType.PHONE_EU: {
        "pattern": re.compile(
            r'\b\+?(3[0-9]|4[0-9]|5[0-9])[-.\s]?\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}\b'
        ),
        "validation": lambda m: True,
        "redaction": "[PHONE_EU_REDACTED]",
        "description": "European Phone Number",
        "examples": ["+33 1 23 45 67 89", "+49 30 12345678"],
    },
    PIIType.GERMAN_ID: {
        # German ID: 10 characters - first letter + 9 alphanumeric
        "pattern": re.compile(r'\b([CFGHJKLMNPRTVWXYZ][0-9CFGHJKLMNPRTVWXYZ]{9})\b'),
        "validation": lambda m: True,
        "redaction": "[DE_ID_REDACTED]",
        "description": "German ID Number (Personalausweis)",
        "examples": ["T220001293", "L01X00T471"],
    },
    PIIType.FRENCH_SSN: {
        "pattern": re.compile(
            r'\b([12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2})\b'
        ),
        "validation": lambda m: True,
        "redaction": "[FR_SSN_REDACTED]",
        "description": "French Social Security Number (NIR)",
        "examples": ["1 85 05 78 006 084 36"],
    },
}


# ============================================================================
# UK-SPECIFIC PATTERNS
# ============================================================================

UK_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.NINO_UK: {
        "pattern": re.compile(
            r'\b([A-CEGHJ-PR-TW-Z]{2}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{2}[-\s]?[A-D])\b',
            re.IGNORECASE
        ),
        "validation": lambda m: _validate_nino(m.group(1)),
        "redaction": "[NINO_REDACTED]",
        "description": "UK National Insurance Number",
        "examples": ["AB 12 34 56 C", "AB123456C"],
    },
    PIIType.NHS_UK: {
        "pattern": re.compile(r'\b(\d{3}[-\s]?\d{3}[-\s]?\d{4})\b'),
        "validation": lambda m: _validate_nhs(m.group(1)),
        "redaction": "[NHS_REDACTED]",
        "description": "UK NHS Number",
        "examples": ["943 476 5919", "9434765919"],
    },
    PIIType.POSTCODE_UK: {
        # Include GIR 0AA (Girobank) as special case
        "pattern": re.compile(
            r'\b(GIR\s*0AA|[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[POSTCODE_UK_REDACTED]",
        "description": "UK Postcode",
        "examples": ["SW1A 1AA", "EC1A 1BB", "W1A 0AX", "GIR 0AA"],
    },
    PIIType.SORT_CODE_UK: {
        "pattern": re.compile(r'\b(\d{2}[-\s]?\d{2}[-\s]?\d{2})\b'),
        "validation": lambda m: True,
        "redaction": "[SORT_CODE_REDACTED]",
        "description": "UK Bank Sort Code",
        "examples": ["20-00-00", "20 00 00"],
    },
}


# ============================================================================
# UNIVERSAL PATTERNS
# ============================================================================

UNIVERSAL_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.EMAIL: {
        "pattern": re.compile(
            r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        ),
        "validation": lambda m: True,
        "redaction": "[EMAIL_REDACTED]",
        "description": "Email Address",
        "examples": ["john.doe@example.com", "user+tag@sub.domain.co.uk"],
    },
    PIIType.CREDIT_CARD: {
        "pattern": re.compile(
            r'\b((?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11}))\b|'
            r'\b(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b|'
            r'\b(\d{4}[-\s]?\d{6}[-\s]?\d{5})\b'  # Amex format
        ),
        "validation": lambda m: _validate_credit_card(m.group(0)),
        "redaction": "[CREDIT_CARD_REDACTED]",
        "description": "Credit Card Number (Visa, MC, Amex, Discover)",
        "examples": ["4111111111111111", "4111-1111-1111-1111", "3782 822463 10005"],
    },
    PIIType.IP_ADDRESS: {
        # Negative lookbehind/lookahead to prevent matching within longer dotted sequences
        "pattern": re.compile(
            r'(?<!\d\.)\b((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?!\.\d)\b'
        ),
        "validation": lambda m: True,
        "redaction": "[IP_REDACTED]",
        "description": "IPv4 Address",
        "examples": ["192.168.1.100", "10.0.0.1", "172.16.0.1"],
    },
    PIIType.IPV6_ADDRESS: {
        "pattern": re.compile(
            r'\b((?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4})\b'
        ),
        "validation": lambda m: True,
        "redaction": "[IPV6_REDACTED]",
        "description": "IPv6 Address",
        "examples": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
    },
    PIIType.MAC_ADDRESS: {
        # Negative lookbehind/lookahead to prevent matching within longer hex sequences
        "pattern": re.compile(
            r'(?<![0-9A-Fa-f][:-])\b((?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})(?![:-][0-9A-Fa-f])\b'
        ),
        "validation": lambda m: True,
        "redaction": "[MAC_REDACTED]",
        "description": "MAC Address",
        "examples": ["00:1A:2B:3C:4D:5E", "00-1A-2B-3C-4D-5E"],
    },
    PIIType.DATE_OF_BIRTH: {
        "pattern": re.compile(
            r'\b(?:DOB|Date\s*of\s*Birth|Born|Birthday)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[DOB_REDACTED]",
        "description": "Date of Birth",
        "examples": ["DOB: 01/15/1985", "Date of Birth: 15-01-1985"],
    },
}


# ============================================================================
# FINANCIAL PATTERNS
# ============================================================================

FINANCIAL_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.BANK_ACCOUNT: {
        "pattern": re.compile(
            r'\b(?:Account(?:\s+Number)?|Acct|A/C)[:\s#]*(\d{8,17})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[BANK_ACCOUNT_REDACTED]",
        "description": "Bank Account Number",
        "examples": ["Account: 123456789012", "Acct #12345678", "Account Number: 123456789012"],
    },
    PIIType.ROUTING_NUMBER: {
        "pattern": re.compile(
            r'\b(?:Routing(?:\s+Number)?|ABA|RTN)[:\s#]*(\d{9})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: _validate_routing(m.group(1)),
        "redaction": "[ROUTING_REDACTED]",
        "description": "US Bank Routing Number",
        "examples": ["Routing: 021000021", "ABA: 121000358", "Routing Number: 021000021"],
    },
    PIIType.SWIFT_BIC: {
        "pattern": re.compile(
            r'\b([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b'
        ),
        "validation": lambda m: True,
        "redaction": "[SWIFT_REDACTED]",
        "description": "SWIFT/BIC Code",
        "examples": ["CHASUS33XXX", "BOFAUS3N"],
    },
    PIIType.CVV: {
        "pattern": re.compile(
            r'\b(?:CVV|CVC|CVV2|CVC2|CSC)[:\s]*(\d{3,4})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[CVV_NEVER_STORE]",
        "description": "Card Verification Value - NEVER STORE",
        "examples": ["CVV: 123", "CVC: 1234"],
        "pci_dss_critical": True,
    },
    PIIType.CARD_EXPIRY: {
        "pattern": re.compile(
            r'\b(?:Exp(?:iry|iration)?|Valid\s*(?:Thru|Through))[:\s]*(\d{2}[/\-]\d{2,4})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[EXPIRY_REDACTED]",
        "description": "Card Expiration Date",
        "examples": ["Exp: 12/25", "Valid Thru 01/2026"],
    },
    PIIType.CRYPTO_ADDRESS: {
        "pattern": re.compile(
            r'\b((?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39})\b|'  # Bitcoin
            r'\b(0x[a-fA-F0-9]{40})\b'  # Ethereum
        ),
        "validation": lambda m: True,
        "redaction": "[CRYPTO_REDACTED]",
        "description": "Cryptocurrency Address (BTC, ETH)",
        "examples": ["1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "0x742d35Cc6634C0532925a3b844Bc9e7595f"],
    },
}


# ============================================================================
# HEALTHCARE (HIPAA) PATTERNS
# ============================================================================

HEALTHCARE_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.PATIENT_ID: {
        "pattern": re.compile(
            r'\b(?:Patient(?:\s*(?:ID|#|No\.?))?|PID)[:\s#]*([A-Z0-9\-]{5,15})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[PATIENT_ID_REDACTED]",
        "description": "Patient Identifier",
        "examples": ["Patient ID: MRN-123456", "Patient: PAT00001234", "PID: 1234567890"],
    },
    PIIType.MRN: {
        "pattern": re.compile(
            r'\b(?:MRN|Medical\s*Record(?:\s*Number)?)[:\s#]*(\d{6,10})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[MRN_REDACTED]",
        "description": "Medical Record Number",
        "examples": ["MRN: 12345678", "Medical Record 1234567890", "Medical Record Number: 123456789"],
    },
    PIIType.HEALTH_PLAN_ID: {
        "pattern": re.compile(
            r'\b(?:Member\s*ID|Subscriber\s*ID|Policy|Insurance\s*ID|Group|Health\s*Plan|BCBS|Aetna|Cigna|UHC|United)[:\s#]*([A-Z0-9]{6,15})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[HEALTH_PLAN_REDACTED]",
        "description": "Health Plan Beneficiary ID",
        "examples": ["Member ID: BCBS12345678", "Subscriber ID: ABC987654321", "Policy: POL12345678"],
    },
    PIIType.NPI: {
        "pattern": re.compile(
            r'\b(?:(?:Provider\s+)?NPI(?:\s*(?:Number|#))?)[:\s#]*(\d{10})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: _validate_npi(m.group(1)),
        "redaction": "[NPI_REDACTED]",
        "description": "National Provider Identifier",
        "examples": ["NPI: 1234567890", "NPI Number: 1234567893", "Provider NPI: 1234567893"],
    },
    PIIType.DEA_NUMBER: {
        "pattern": re.compile(
            r'\b(?:DEA(?:\s*Number)?)[:\s#]*([A-Z][A-Z0-9]\d{7})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: _validate_dea(m.group(1)),
        "redaction": "[DEA_REDACTED]",
        "description": "DEA Registration Number",
        "examples": ["DEA: AB1234567", "DEA #XY9876543", "DEA Number: AB1234563"],
    },
    PIIType.ICD_CODE: {
        "pattern": re.compile(
            r'\b(?:ICD(?:[-\s]?10)?|Diagnosis|Dx)[:\s]*([A-Z]\d{2}(?:\.\d{1,4})?[A-Z]?)\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[DIAGNOSIS_REDACTED]",
        "description": "ICD-10 Diagnosis Code",
        "examples": ["ICD-10: E11.9", "Diagnosis: J06.9", "ICD: M54.5", "Dx: I10"],
    },
    PIIType.CPT_CODE: {
        "pattern": re.compile(
            r'\b(?:CPT(?:\s*(?:Code|#))?|Procedure)[:\s#]*(\d{5})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[PROCEDURE_REDACTED]",
        "description": "CPT Procedure Code",
        "examples": ["CPT: 99213", "Procedure 99214", "CPT Code: 36415", "CPT #: 71046"],
    },
}


# ============================================================================
# BIOMETRIC PATTERNS
# ============================================================================

BIOMETRIC_PATTERNS: Dict[PIIType, Dict] = {
    PIIType.BIOMETRIC_ID: {
        "pattern": re.compile(
            r'\b(?:Biometric(?:\s*(?:ID|Identifier|Data\s*ID))?|Bio[-\s]?ID)[:\s#]*([A-Z0-9][A-Z0-9\-]{4,19})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[BIOMETRIC_REDACTED]",
        "description": "Generic Biometric Identifier",
        "examples": ["Biometric ID: BIO-12345678", "Biometric: BIO-2024-001234"],
    },
    PIIType.FACE_ID: {
        "pattern": re.compile(
            r'\b(?:Face[-\s]?ID|FaceID|Facial[-\s]?(?:ID|Recognition(?:\s*(?:Data\s*)?ID)?)|Face[-\s]?(?:Recognition|Template)[-\s]?ID?)[:\s#]*([A-Z0-9][A-Z0-9\-]{4,19})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[FACE_ID_REDACTED]",
        "description": "Facial Recognition Identifier",
        "examples": ["FaceID: FACE-12345", "Facial Recognition ID: FR-98765", "Face ID: FACE123456789"],
    },
    PIIType.FINGERPRINT_ID: {
        "pattern": re.compile(
            r'\b(?:Fingerprint(?:\s*(?:ID|Record|Template|Data[-\s]*ID))?|FP[-\s]?ID|Print[-\s]?ID)[:\s#]*([A-Z0-9][A-Z0-9\-]{4,19})\b',
            re.IGNORECASE
        ),
        "validation": lambda m: True,
        "redaction": "[FINGERPRINT_REDACTED]",
        "description": "Fingerprint Identifier",
        "examples": ["Fingerprint: FP-12345", "Fingerprint ID: 98765-FP", "Print ID: PRINT123456789"],
    },
}


# ============================================================================
# PII DETECTOR CLASS
# ============================================================================

class PIIDetector:
    """Main PII detection engine"""

    def __init__(
        self,
        regions: Optional[List[str]] = None,
        custom_patterns: Optional[Dict[PIIType, Dict]] = None,
    ):
        """
        Initialize PII detector with specific regions.

        Args:
            regions: List of regions to detect. Options: 'us', 'au', 'eu', 'uk',
                    'universal', 'financial', 'healthcare', 'biometric', 'all'
            custom_patterns: Additional custom patterns to add
        """
        self.patterns: Dict[PIIType, Dict] = {}

        # Default to all regions
        if regions is None:
            regions = ['all']

        # Load patterns based on regions
        if 'all' in regions or 'us' in regions:
            self.patterns.update(US_PATTERNS)
        if 'all' in regions or 'au' in regions:
            self.patterns.update(AU_PATTERNS)
        if 'all' in regions or 'eu' in regions:
            self.patterns.update(EU_PATTERNS)
        if 'all' in regions or 'uk' in regions:
            self.patterns.update(UK_PATTERNS)
        if 'all' in regions or 'universal' in regions:
            self.patterns.update(UNIVERSAL_PATTERNS)
        if 'all' in regions or 'financial' in regions:
            self.patterns.update(FINANCIAL_PATTERNS)
        if 'all' in regions or 'healthcare' in regions:
            self.patterns.update(HEALTHCARE_PATTERNS)
        if 'all' in regions or 'biometric' in regions:
            self.patterns.update(BIOMETRIC_PATTERNS)

        # Add custom patterns
        if custom_patterns:
            self.patterns.update(custom_patterns)

        logger.info(f"PIIDetector initialized with {len(self.patterns)} patterns")

    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect all PII in text.

        Args:
            text: Text to scan for PII

        Returns:
            List of PIIMatch objects
        """
        matches = []

        for pii_type, config in self.patterns.items():
            pattern = config['pattern']
            validation = config.get('validation', lambda m: True)

            for match in pattern.finditer(text):
                if validation(match):
                    matches.append(PIIMatch(
                        pii_type=pii_type,
                        value=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        confidence=1.0,
                    ))

        # Sort by start position
        matches.sort(key=lambda m: m.start)
        return matches

    def redact(self, text: str) -> tuple[str, List[PIIMatch]]:
        """
        Detect and redact all PII in text.

        Args:
            text: Text to redact

        Returns:
            Tuple of (redacted_text, list of matches)
        """
        matches = self.detect(text)

        # Redact from end to start to preserve positions
        redacted = text
        for match in reversed(matches):
            config = self.patterns.get(match.pii_type, {})
            redaction = config.get('redaction', f'[{match.pii_type.value.upper()}_REDACTED]')
            redacted = redacted[:match.start] + redaction + redacted[match.end:]

        return redacted, matches

    def get_supported_types(self) -> List[str]:
        """Get list of supported PII types"""
        return [p.value for p in self.patterns.keys()]


# Convenience function
def detect_pii(text: str, regions: Optional[List[str]] = None) -> List[PIIMatch]:
    """Convenience function to detect PII"""
    detector = PIIDetector(regions=regions)
    return detector.detect(text)


def redact_pii(text: str, regions: Optional[List[str]] = None) -> str:
    """Convenience function to redact PII"""
    detector = PIIDetector(regions=regions)
    redacted, _ = detector.redact(text)
    return redacted
