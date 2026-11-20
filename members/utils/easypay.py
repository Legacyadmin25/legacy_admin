# members/utils/easypay.py

import os
from io import BytesIO
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from django.core.files.base import ContentFile
from django.conf import settings

# Default global receiver ID — used when no per-scheme biller code is set.
# In production, set EASYPAY_RECEIVER_ID in .env or use scheme.easypay_biller_code.
DEFAULT_RECEIVER_ID = getattr(settings, 'EASYPAY_RECEIVER_ID', '5047')

def calculate_luhn_check_digit(number_str):
    """
    Calculate the Luhn check digit for a number string.
    """
    digits = [int(d) for d in number_str]
    odd_sum = sum(digits[-1::-2])
    even_sum = sum([sum(divmod(2 * d, 10)) for d in digits[-2::-2]])
    return str((10 - (odd_sum + even_sum) % 10) % 10)

def generate_easypay_number(policy_id: int, receiver_id: str = None) -> str:
    """
    Generate a valid EasyPay number using:
    - Prefix 9 + receiver_id (falls back to DEFAULT_RECEIVER_ID)
    - 12-digit zero-padded account_ref
    - 1-digit Luhn check digit

    Format: 9{RECEIVER_ID}{ACCOUNT_REF}{LUHN}

    Pass the scheme's easypay_biller_code as receiver_id for per-scheme references.
    """
    rid = (receiver_id or DEFAULT_RECEIVER_ID).strip()
    account_ref = str(policy_id).zfill(12)
    base_number = f"9{rid}{account_ref}"
    check_digit = calculate_luhn_check_digit(base_number)
    return f"{base_number}{check_digit}"

def generate_qr_code_image(easypay_number: str) -> ContentFile:
    """
    Generate a QR code for EasyPay that links to the payment URL.
    Returns a Django ContentFile (can be saved to ImageField or FileField).
    """
    from .links import payment_link
    payment_url = payment_link(easypay_number, 0)
    qr = qrcode.make(payment_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"{easypay_number}_qr.png")


def generate_qr_code_image(easypay_number: str) -> ContentFile:
    """
    Generate a QR code for Easypay that links to the payment URL.
    Returns a Django ContentFile (can be saved to ImageField or FileField).
    """
    # Import here to avoid circular imports
    from .links import payment_link
    
    # Create payment link for the QR code
    payment_url = payment_link(easypay_number, 0)  # Amount will be filled in by the payment system
    
    # Generate QR code
    qr = qrcode.make(payment_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"{easypay_number}_qr.png")

def generate_barcode_image(easypay_number: str) -> ContentFile:
    """
    Generate a Code128 barcode image for the Easypay number.
    Returns a Django ContentFile.
    """
    buffer = BytesIO()
    barcode = Code128(easypay_number, writer=ImageWriter(options={
        'dpi': 300,
        'module_height': 15.0,
        'quiet_zone': 6.0,
        'font_size': 14,
        'text_distance': 1.0,
    }))
    barcode.write(buffer)
    return ContentFile(buffer.getvalue(), name=f"{easypay_number}_barcode.png")

def save_barcode_to_file(easypay_number: str, output_path: str) -> str:
    """
    Generates a Code128 barcode PNG at 300 DPI and saves it to a file.
    
    Args:
        easypay_number (str): The Easypay number to encode in the barcode
        output_path (str): Full path where the barcode image will be saved
    
    Returns:
        str: Path to the generated barcode image
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Generate the barcode
    barcode = Code128(easypay_number, writer=ImageWriter(options={
        'dpi': 300,
        'module_height': 15.0,
        'quiet_zone': 6.0,
        'font_size': 14,
        'text_distance': 1.0,
    }))
    
    # Save the barcode to the specified path without the file extension
    # as the barcode library adds it automatically
    path_without_ext = os.path.splitext(output_path)[0]
    saved_path = barcode.save(path_without_ext)
    
    return saved_path

def save_qr_code_to_file(data_url: str, output_path: str) -> str:
    """
    Creates a QR code from a payment link and saves it to a file.
    
    Args:
        data_url (str): The URL or data to encode in the QR code
        output_path (str): Full path where the QR code image will be saved
    
    Returns:
        str: Path to the generated QR code image
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    
    # Add data to the QR code
    qr.add_data(data_url)
    qr.make(fit=True)
    
    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the image
    img.save(output_path)
    
    return output_path
