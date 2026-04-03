"""
Validation utilities for the application.
"""

def luhn_check(id_number):
    """
    Validate a South African ID number using the Luhn algorithm.
    
    Args:
        id_number (str): The ID number to validate
        
    Returns:
        bool: True if the ID number is valid, False otherwise
    """
    # Remove any non-digit characters
    id_number = ''.join(filter(str.isdigit, str(id_number)))
    
    # Check if the ID number is 13 digits long
    if len(id_number) != 13:
        return False
    
    # Extract the check digit (last digit)
    check_digit = int(id_number[-1])
    
    # Calculate the Luhn check digit
    total = 0
    for i in range(12):
        digit = int(id_number[i])
        
        # Double every second digit from the right (odd positions when starting from 0 from the left)
        if i % 2 == 1:  # This is the key change - South African IDs use odd positions
            digit *= 2
            # If the result is a two-digit number, add the digits
            if digit > 9:
                digit = (digit // 10) + (digit % 10)
        
        total += digit
    
    # Calculate the check digit that would make the total a multiple of 10
    calculated_check = (10 - (total % 10)) % 10
    
    # Compare the calculated check digit with the actual check digit
    return calculated_check == check_digit


def validate_sa_id(id_number):
    """
    Validate a South African ID number and extract date of birth and gender.
    
    Args:
        id_number (str): The ID number to validate
        
    Returns:
        tuple: (is_valid, date_of_birth, gender) where is_valid is a boolean,
               date_of_birth is a datetime.date object, and gender is a string ('Male' or 'Female')
    """
    import datetime
    
    # Basic validation
    if not id_number or not isinstance(id_number, str):
        return False, None, None
    
    # Remove any non-digit characters
    clean_id = ''.join(filter(str.isdigit, str(id_number)))
    
    # Check length
    if len(clean_id) != 13:
        return False, None, None
    
    # Check if all characters are digits
    if not clean_id.isdigit():
        return False, None, None
    
    # Extract date components from ID number
    try:
        # First 6 digits represent YYMMDD
        year_str = clean_id[0:2]
        month_str = clean_id[2:4]
        day_str = clean_id[4:6]
        
        # Determine century (19xx or 20xx)
        year_prefix = '19' if int(year_str) > 50 else '20'
        year = int(year_prefix + year_str)
        month = int(month_str)
        day = int(day_str)
        
        # Validate date components
        if month < 1 or month > 12 or day < 1 or day > 31:
            return False, None, None
            
        # Create date object
        date_of_birth = datetime.date(year, month, day)
        
        # Extract gender from ID number
        # Digits 7-10 represent gender (0000-4999 = female, 5000-9999 = male)
        gender_digits = int(clean_id[6:10])
        gender = 'Male' if gender_digits >= 5000 else 'Female'
        
        # Check Luhn algorithm
        if not luhn_check(clean_id):
            return False, None, None
        
        # If we get here, the ID is valid
        return True, date_of_birth, gender
        
    except (ValueError, IndexError):
        return False, None, None
