from urllib.parse import urlencode

def payment_link(easypay_no: str, amount: Decimal, method: str="generic") -> str:
    base = f"https://www.easypay.co.za/{method}"
    return f"{base}?{urlencode({'b': easypay_no, 'a': str(amount)})}"
