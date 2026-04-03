"""
Age calculation utilities for the members application.
"""
from datetime import date


def get_member_age_from_dob(date_of_birth):
    """
    Calculate a member's age based on their date of birth.
    
    Args:
        date_of_birth (date): The member's date of birth
        
    Returns:
        int: The member's age in years
    """
    today = date.today()
    
    # Calculate age
    age = today.year - date_of_birth.year
    
    # Adjust age if birthday hasn't occurred yet this year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
        
    return age


def get_age_range(age):
    """
    Get the age range category for a given age.
    
    Args:
        age (int): The age to categorize
        
    Returns:
        str: The age range category (e.g., '0-17', '18-64', '65+')
    """
    if age < 18:
        return '0-17'
    elif age < 65:
        return '18-64'
    else:
        return '65+'
