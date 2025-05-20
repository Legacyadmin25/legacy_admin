# utils/luhn.py

from datetime import date, datetime
from typing import Tuple

def luhn_check(id_number: str) -> bool:
    """
    Returns True if `id_number` passes the Luhn checksum.
    Works on any string of digits.
    """
    digits = [int(d) for d in id_number if d.isdigit()]
    # Starting from the right, double every second digit:
    total = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0

def validate_id_number(id_number: str) -> Tuple[bool, date, str]:
    """
    For a 13-digit South African ID:
      - returns (is_valid, birth_date, gender_str)
      - `is_valid` is False if length!=13 or Luhn fails or date invalid
      - `birth_date` is a datetime.date object if valid, else None
      - `gender_str` is 'Male' or 'Female' based on digits 7–10
    """
    if len(id_number) != 13 or not id_number.isdigit():
        return False, None, None

    if not luhn_check(id_number):
        return False, None, None

    # parse YYMMDD
    yy = int(id_number[0:2])
    mm = int(id_number[2:4])
    dd = int(id_number[4:6])

    # determine century: assume 1900s until current year cutoff
    today = date.today()
    cutoff = today.year % 100
    year = 1900 + yy if yy > cutoff else 2000 + yy

    try:
        birth_date = date(year, mm, dd)
    except ValueError:
        return False, None, None

    # gender: digits 6–9 inclusive (4 digits) >=5000 → male
    gender = 'Male' if int(id_number[6:10]) >= 5000 else 'Female'

    return True, birth_date, gender
