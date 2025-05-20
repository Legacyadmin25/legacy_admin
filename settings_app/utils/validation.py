# settings_app/utils/validation.py

def luhn_checksum(id_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(id_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0

def is_valid_sa_phone(phone):
    return phone.isdigit() and len(phone) == 10 and phone.startswith('0')

from datetime import datetime

def extract_dob_from_id(id_number):
    try:
        dob_str = id_number[:6]
        year = int(dob_str[:2])
        year += 1900 if year > 30 else 2000
        return datetime.strptime(f"{year}{dob_str[2:]}", "%Y%m%d").date()
    except Exception:
        return None

# utils/validation.py

import re

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[@$!%*#?&]', password):
        return False
    return True
