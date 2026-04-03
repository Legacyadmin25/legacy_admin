import logging
import base64
import io
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

def process_id_document(image_data):
    """
    Process an ID document image using OCR to extract text.
    
    Args:
        image_data (str): Base64 encoded image data
        
    Returns:
        dict: Extracted text from the ID document
    """
    try:
        # Decode the base64 image
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
            
        image_data = base64.b64decode(image_data)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to grayscale for better OCR
        image = image.convert('L')
        
        # Use Tesseract to do OCR on the image
        text = pytesseract.image_to_string(image)
        
        # Process the text to extract relevant information
        # This is a simplified example - you'll need to adjust based on your ID format
        result = {
            'raw_text': text,
            'id_number': extract_id_number(text),
            'name': extract_name(text),
            'surname': extract_surname(text),
            'date_of_birth': extract_dob(text),
            'gender': extract_gender(text),
            'nationality': extract_nationality(text),
            'status': 'success'
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing ID document: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

def extract_id_number(text):
    """Extract ID number from OCR text"""
    # South African ID number is 13 digits
    import re
    id_match = re.search(r'\b\d{13}\b', text)
    return id_match.group(0) if id_match else None

def extract_name(text):
    """Extract first name from OCR text"""
    # This is a very basic implementation
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 1:
        return lines[0].split()[-1]  # Assume last word of first line is first name
    return None

def extract_surname(text):
    """Extract surname from OCR text"""
    # This is a very basic implementation
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 0:
        return lines[0].split()[0]  # Assume first word is surname
    return None

def extract_dob(text):
    """Extract date of birth from OCR text"""
    # Look for dates in common formats
    import re
    # YYYY-MM-DD or YYYY/MM/DD or YYYY MM DD
    date_match = re.search(r'\b(19|20)\d{2}[-/ ](0[1-9]|1[0-2])[-/ ](0[1-9]|[12][0-9]|3[01])\b', text)
    if date_match:
        return date_match.group(0)
    return None

def extract_gender(text):
    """Extract gender from OCR text"""
    text_lower = text.lower()
    if 'male' in text_lower:
        return 'Male'
    elif 'female' in text_lower:
        return 'Female'
    return None

def extract_nationality(text):
    """Extract nationality from OCR text"""
    # This is a very basic implementation
    text_lower = text.lower()
    if 'south africa' in text_lower or 'south african' in text_lower:
        return 'South African'
    return None
