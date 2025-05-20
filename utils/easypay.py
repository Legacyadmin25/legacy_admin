from django.conf import settings

def calculate_luhn(num_str: str) -> str:
    """
    Given a numeric string, returns its single-digit Luhn check digit.
    """
    digits = [int(d) for d in num_str]
    total = 0
    # Starting from the right, double every second digit:
    for i, d in enumerate(reversed(digits), start=1):
        if i % 2 == 1:
            total += d
        else:
            dbl = d * 2
            total += dbl if dbl < 10 else dbl - 9
    # Check digit is the amount to round up to the next multiple of 10:
    return str((10 - (total % 10)) % 10)

def generate_easypay_number(account_ref: str) -> str:
    """
    Builds a valid EasyPay number:
      9 + RECEIVER_ID + zero-padded account_ref (12 digits) + Luhn check digit
    """
    receiver = settings.EASY_PAY_RECEIVER_ID
    # Left-pad account_ref to 12 digits now
    acct = account_ref.zfill(settings.EASY_PAY_ACCOUNT_LENGTH)
    base = f"{receiver}{acct}"
    check = calculate_luhn(base)
    return f"9{base}{check}"
