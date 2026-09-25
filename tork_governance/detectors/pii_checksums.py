"""
Check digits for the country registry.

The SDK bundle NAMES twenty algorithms and gives weights and a modulus for the
eleven that reduce to them; the other nine are marked ``kind: "custom"`` and
carry no specification, so they are ported here by hand from
``landing/lib/pii/checksums.ts`` -- the single implementation the cloud and the
country corpus both use. Keeping the arithmetic identical is what makes a
receipt block from this SDK byte-identical to one from the cloud.

Every function is pure: a string in, a bool out. No clock, no I/O.
"""

from __future__ import annotations

import re
from typing import Callable, Dict

_NON_DIGIT = re.compile(r"\D")


def _digits(s: str) -> str:
    return _NON_DIGIT.sub("", s)


def _mod_digits(digits: str, m: int) -> int:
    """Remainder of a long decimal string modulo m, digit by digit."""
    r = 0
    for ch in digits:
        r = (r * 10 + int(ch)) % m
    return r


def luhn(value: str) -> bool:
    """Luhn / ISO-IEC 7812-1 mod-10."""
    d = _digits(value)
    if len(d) < 2:
        return False
    total, dbl = 0, False
    for ch in reversed(d):
        n = int(ch)
        if dbl:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        dbl = not dbl
    return total % 10 == 0


_VERHOEFF_MUL = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6), (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8), (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2), (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4), (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

_VERHOEFF_PERM = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2), (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0), (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5), (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def verhoeff(value: str) -> bool:
    """Verhoeff (Aadhaar, UIDAI Circular No. 1 of 2018)."""
    d = _digits(value)
    c = 0
    for i, ch in enumerate(reversed(d)):
        c = _VERHOEFF_MUL[c][_VERHOEFF_PERM[i % 8][int(ch)]]
    return c == 0


def au_tfn(value: str) -> bool:
    """Australian TFN (ATO): weights 1,4,3,7,5,8,6,9,10 over 9 digits, sum mod 11 == 0."""
    d = _digits(value)
    if len(d) != 9:
        return False
    w = (1, 4, 3, 7, 5, 8, 6, 9, 10)
    return sum(int(c) * w[i] for i, c in enumerate(d)) % 11 == 0


def au_abn(value: str) -> bool:
    """Australian ABN (ABR): subtract 1 from the first digit, weights 10,1,3..19, sum mod 89 == 0."""
    d = _digits(value)
    if len(d) != 11:
        return False
    w = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
    total = (int(d[0]) - 1) * w[0] + sum(int(c) * w[i + 1] for i, c in enumerate(d[1:]))
    return total % 89 == 0


def au_medicare(value: str) -> bool:
    """Australian Medicare (Services Australia): weights 1,3,7,9,1,3,7,9 over digits 1-8."""
    d = _digits(value)
    if len(d) < 10 or d[0] not in "23456":
        return False
    w = (1, 3, 7, 9, 1, 3, 7, 9)
    return sum(int(c) * w[i] for i, c in enumerate(d[:8])) % 10 == int(d[8])


def uk_nhs(value: str) -> bool:
    """UK NHS number: weights 10..2, check = 11 - (sum mod 11); 11 -> 0; 10 invalid."""
    d = _digits(value)
    if len(d) != 10:
        return False
    total = sum(int(c) * (10 - i) for i, c in enumerate(d[:9]))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    if check == 10:
        return False
    return check == int(d[9])


def br_cpf(value: str) -> bool:
    """Brazil CPF (Receita Federal): two sequential mod-11 check digits."""
    d = _digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False

    def calc(length: int) -> int:
        total = sum(int(d[i]) * (length + 1 - i) for i in range(length))
        r = (total * 10) % 11
        return 0 if r == 10 else r

    return calc(9) == int(d[9]) and calc(10) == int(d[10])


def br_cnpj(value: str) -> bool:
    """Brazil CNPJ (Receita Federal): two mod-11 check digits, different weight vectors."""
    d = _digits(value)
    if len(d) != 14 or d == d[0] * 14:
        return False

    def calc(weights):
        r = sum(int(d[i]) * w for i, w in enumerate(weights)) % 11
        return 0 if r < 2 else 11 - r

    return (calc((5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)) == int(d[12])
            and calc((6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)) == int(d[13]))


def jp_my_number(value: str) -> bool:
    """Japan My Number (MIC Ordinance No. 85 of 2014)."""
    d = _digits(value)
    if len(d) != 12:
        return False
    total = 0
    for n in range(1, 12):
        p = int(d[11 - n])
        q = n + 1 if n <= 6 else n - 5
        total += p * q
    r = total % 11
    check = 0 if r <= 1 else 11 - r
    return check == int(d[11])


def cn_resident_id(value: str) -> bool:
    """China resident ID (GB 11643-1999): ISO 7064 MOD 11-2, check in 0-9 or X."""
    s = re.sub(r"\s", "", value).upper()
    if not re.fullmatch(r"\d{17}[\dX]", s):
        return False
    w = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    total = sum(int(c) * w[i] for i, c in enumerate(s[:17]))
    return "10X98765432"[total % 11] == s[17]


def kr_rrn(value: str) -> bool:
    """Korea RRN, for numbers issued before 20 Oct 2020.

    ADVISORY ONLY, never a gate: numbers issued from 20 Oct 2020 are randomly
    assigned and carry no check digit, so rejecting on this would stop
    detecting every RRN issued since.
    """
    d = _digits(value)
    if len(d) != 13:
        return False
    w = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
    total = sum(int(c) * w[i] for i, c in enumerate(d[:12]))
    return (11 - (total % 11)) % 10 == int(d[12])


def sg_nric(value: str) -> bool:
    """Singapore NRIC/FIN (ICA): weights 2,7,6,5,4,3,2 and a prefix-dependent letter table."""
    s = re.sub(r"\s", "", value).upper()
    if not re.fullmatch(r"[STFGM]\d{7}[A-Z]", s):
        return False
    w = (2, 7, 6, 5, 4, 3, 2)
    total = sum(int(c) * w[i] for i, c in enumerate(s[1:8]))
    prefix = s[0]
    if prefix in ("T", "G"):
        total += 4
    if prefix == "M":
        total += 3
    st, fg, m = "JZIHGFEDCBA", "XWUTRQPNMLK", "KLJNPQRTUWX"
    table = st if prefix in ("S", "T") else (m if prefix == "M" else fg)
    return table[total % 11] == s[8]


_CF_ODD = {
    "0": 1, "1": 0, "2": 5, "3": 7, "4": 9, "5": 13, "6": 15, "7": 17, "8": 19, "9": 21,
    "A": 1, "B": 0, "C": 5, "D": 7, "E": 9, "F": 13, "G": 15, "H": 17, "I": 19, "J": 21,
    "K": 2, "L": 4, "M": 18, "N": 20, "O": 11, "P": 3, "Q": 6, "R": 8, "S": 12, "T": 14,
    "U": 16, "V": 10, "W": 22, "X": 25, "Y": 24, "Z": 23,
}


def it_codice_fiscale(value: str) -> bool:
    """Italy codice fiscale (Agenzia delle Entrate): odd/even tables, check letter."""
    s = re.sub(r"\s", "", value).upper()
    if not re.fullmatch(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", s):
        return False
    total = 0
    for i in range(15):
        c = s[i]
        if i % 2 == 0:
            total += _CF_ODD[c]
        else:
            total += int(c) if c.isdigit() else ord(c) - 65
    return chr(65 + (total % 26)) == s[15]


def fr_nir(value: str) -> bool:
    """France NIR (Insee): 97-complement, Corsican 2A/2B mapped to 19/18 first."""
    s = re.sub(r"\s", "", value).upper()
    if not re.fullmatch(r"[12]\d{2}\d{2}(\d{2}|2A|2B)\d{3}\d{3}\d{2}", s):
        return False
    s = s.replace("2A", "19").replace("2B", "18")
    return 97 - _mod_digits(s[:13], 97) == int(s[13:])


def de_steuer_id(value: str) -> bool:
    """Germany Steuer-IdNr (BZSt): ISO 7064 MOD 11,10 over 10 digits."""
    d = _digits(value)
    if len(d) != 11 or d[0] == "0":
        return False
    product = 10
    for i in range(10):
        total = (int(d[i]) + product) % 10
        if total == 0:
            total = 10
        product = (total * 2) % 11
    check = 11 - product
    if check == 10:
        check = 0
    return check == int(d[10])


def th_national_id(value: str) -> bool:
    """Thailand national ID (DOPA): weights 13..2, check = (11 - sum mod 11) mod 10."""
    d = _digits(value)
    if len(d) != 13:
        return False
    total = sum(int(c) * (13 - i) for i, c in enumerate(d[:12]))
    return (11 - (total % 11)) % 10 == int(d[12])


def ca_sin(value: str) -> bool:
    """Canada SIN: Luhn over 9 digits. Advisory -- the algorithm is community-sourced."""
    return len(_digits(value)) == 9 and luhn(value)


def za_id(value: str) -> bool:
    """South Africa ID (Home Affairs / SARS BRS Appendix B 8.3): Luhn over 13 digits."""
    return len(_digits(value)) == 13 and luhn(value)


def ae_emirates_id(value: str) -> bool:
    """UAE Emirates ID (ICP): Luhn over 15 digits starting 784. Advisory."""
    d = _digits(value)
    return len(d) == 15 and d.startswith("784") and luhn(d)


def sa_national_id(value: str) -> bool:
    """Saudi national ID / iqama: Luhn over 10 digits starting 1 or 2. Advisory."""
    d = _digits(value)
    return len(d) == 10 and d[0] in "12" and luhn(d)


#: Keyed by the bundle's ``checksum`` field.
CHECKSUM_FUNCTIONS: Dict[str, Callable[[str], bool]] = {
    "luhn": luhn,
    "verhoeff": verhoeff,
    "au_tfn": au_tfn,
    "au_abn": au_abn,
    "au_medicare": au_medicare,
    "uk_nhs": uk_nhs,
    "br_cpf": br_cpf,
    "br_cnpj": br_cnpj,
    "jp_my_number": jp_my_number,
    "cn_resident_id": cn_resident_id,
    "kr_rrn": kr_rrn,
    "sg_nric": sg_nric,
    "it_codice_fiscale": it_codice_fiscale,
    "fr_nir": fr_nir,
    "de_steuer_id": de_steuer_id,
    "th_national_id": th_national_id,
    "ca_sin": ca_sin,
    "za_id": za_id,
    "ae_emirates_id": ae_emirates_id,
    "sa_national_id": sa_national_id,
}
