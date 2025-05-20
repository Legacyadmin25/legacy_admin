import io
import re
import logging
import base64
from datetime import datetime
import pytesseract
from PIL import Image
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def process_id_document(image_data):
    """
    Process an ID document image to extract personal information.
    
    Args:
        image_data (str): Base64 encoded image data
        
    Returns:
        dict: Extracted information (id_number, full_name, date_of_birth, gender)
    """
    try:
        # First try with OpenAI Vision API if configured
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            result = process_with_openai_vision(image_data)
            if result and result.get('id_number'):
                return result
        
        # Fallback to Tesseract OCR
        return process_with_tesseract(image_data)
    except Exception as e:
        logger.error(f"Error processing ID document: {str(e)}")
        return {
            'id_number': None,
            'full_name': None,
            'date_of_birth': None,
            'gender': None,
            'error': str(e)
        }

def process_with_openai_vision(image_data):
    """
    Process ID document using OpenAI Vision API
    
    Args:
        image_data (str): Base64 encoded image data
        
    Returns:
        dict: Extracted information
    """
    try:
        api_key = settings.OPENAI_API_KEY
        
        # Prepare the image data
        if image_data.startswith('data:image'):
            # Remove the data URL prefix
            image_data = image_data.split(',')[1]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the following information from this South African ID document: ID Number, Full Name, Date of Birth (in YYYY-MM-DD format), and Gender (M or F). Return ONLY a JSON object with these fields. If you can't extract a field, set it to null."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Extract JSON from response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group(0))
                
                # Validate ID number
                if extracted_data.get('id_number') and validate_sa_id(extracted_data['id_number']):
                    # If date of birth is not in the right format, try to extract from ID
                    if not extracted_data.get('date_of_birth') and extracted_data.get('id_number'):
                        extracted_data['date_of_birth'] = extract_dob_from_id(extracted_data['id_number'])
                    
                    # If gender is not extracted, try to extract from ID
                    if not extracted_data.get('gender') and extracted_data.get('id_number'):
                        extracted_data['gender'] = extract_gender_from_id(extracted_data['id_number'])
                    
                    return extracted_data
        
        return None
    except Exception as e:
        logger.error(f"Error with OpenAI Vision: {str(e)}")
        return None

def process_with_tesseract(image_data):
    """
    Process ID document using Tesseract OCR
    
    Args:
        image_data (str): Base64 encoded image data
        
    Returns:
        dict: Extracted information
    """
    try:
        # Convert base64 to image
        if image_data.startswith('data:image'):
            # Remove the data URL prefix
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(image)
        
        # Extract ID number
        id_number = extract_id_number(text)
        
        # Extract name
        full_name = extract_name(text)
        
        # Extract date of birth and gender from ID number
        date_of_birth = None
        gender = None
        
        if id_number:
            date_of_birth = extract_dob_from_id(id_number)
            gender = extract_gender_from_id(id_number)
        
        return {
            'id_number': id_number,
            'full_name': full_name,
            'date_of_birth': date_of_birth,
            'gender': gender
        }
    except Exception as e:
        logger.error(f"Error with Tesseract OCR: {str(e)}")
        return {
            'id_number': None,
            'full_name': None,
            'date_of_birth': None,
            'gender': None,
            'error': str(e)
        }

def extract_id_number(text):
    """Extract South African ID number from text"""
    # Look for 13 digit number
    id_pattern = r'\b\d{13}\b'
    matches = re.findall(id_pattern, text)
    
    for match in matches:
        if validate_sa_id(match):
            return match
    
    return None

def extract_name(text):
    """Extract name from text"""
    # This is a simplified approach - in real implementation, 
    # you would need more sophisticated pattern matching
    lines = text.split('\n')
    for line in lines:
        # Skip lines that are likely not names
        if re.search(r'\d', line):  # Skip lines with numbers
            continue
        if len(line.strip()) < 3:  # Skip very short lines
            continue
        
        # Check for common name patterns
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', line.strip()):
            return line.strip()
    
    return None

def validate_sa_id(id_number):
    """Validate South African ID number"""
    if not id_number or not re.match(r'^\d{13}$', id_number):
        return False
    
    # Check date validity
    try:
        year = int(id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        
        # Adjust year (assume 1900s if > current year last 2 digits, otherwise 2000s)
        current_year = datetime.now().year % 100
        year = 1900 + year if year > current_year else 2000 + year
        
        # Check if date is valid
        datetime(year, month, day)
        
        # Check citizenship and gender digits are valid
        citizenship = int(id_number[10])
        if citizenship not in [0, 1]:
            return False
        
        # Check checksum (Luhn algorithm)
        digits = [int(d) for d in id_number]
        checksum = 0
        for i in range(len(digits)):
            if i % 2 == 0:
                checksum += digits[i]
            else:
                doubled = digits[i] * 2
                checksum += doubled if doubled < 10 else doubled - 9
        
        return checksum % 10 == 0
    except:
        return False

def extract_dob_from_id(id_number):
    """Extract date of birth from ID number"""
    if not id_number or len(id_number) != 13:
        return None
    
    try:
        year = int(id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        
        # Adjust year (assume 1900s if > current year last 2 digits, otherwise 2000s)
        current_year = datetime.now().year % 100
        year = 1900 + year if year > current_year else 2000 + year
        
        return f"{year:04d}-{month:02d}-{day:02d}"
    except:
        return None

def extract_gender_from_id(id_number):
    """Extract gender from ID number"""
    if not id_number or len(id_number) != 13:
        return None
    
    try:
        gender_digit = int(id_number[6])
        return 'M' if gender_digit >= 5 else 'F'
    except:
        return None
