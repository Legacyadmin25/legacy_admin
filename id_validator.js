/**
 * South African ID Number Validator
 * 
 * This file contains functions to validate South African ID numbers
 * and extract information from them such as date of birth and gender.
 */

/**
 * Validates a South African ID number using the Luhn algorithm
 * @param {string} idNumber - The ID number to validate
 * @returns {boolean} - Whether the ID number is valid
 */
function validateSouthAfricanID(idNumber) {
    // Basic format check
    if (!/^\d{13}$/.test(idNumber)) {
        console.log('ID validation failed: Not 13 digits');
        return false;
    }

    try {
        // Extract all digits
        const digits = idNumber.split('').map(d => parseInt(d));
        
        // 1. Sum the odd-position digits (positions 1, 3, 5, ..., 11)
        let oddSum = 0;
        for (let i = 0; i < 12; i += 2) {
            oddSum += digits[i];
        }
        
        // 2. Even-position digits (positions 2, 4, ..., 12)
        let evenStr = '';
        for (let i = 1; i < 12; i += 2) {
            evenStr += digits[i];
        }
        
        // 3. Convert to integer, multiply by 2
        const evenProduct = parseInt(evenStr) * 2;
        
        // 4. Sum all digits of the product
        let evenSum = 0;
        const evenProductStr = evenProduct.toString();
        for (let i = 0; i < evenProductStr.length; i++) {
            evenSum += parseInt(evenProductStr[i]);
        }
        
        // 5. Add oddSum and evenSum
        const total = oddSum + evenSum;
        
        // 6. Calculate checksum
        const checksum = (10 - (total % 10)) % 10;
        
        // 7. Compare to the 13th digit
        const isValid = checksum === digits[12];
        
        console.log('ID Validation Details:', {
            idNumber,
            oddSum,
            evenStr,
            evenProduct,
            evenSum,
            total,
            checksum,
            actualCheckDigit: digits[12],
            isValid
        });
        
        return isValid;
    } catch (error) {
        console.error('Error in ID validation:', error);
        return false;
    }
}

/**
 * Extract date of birth from ID number
 * @param {string} idNumber - The ID number
 * @returns {object|null} - Date object or null if invalid
 */
function extractDateFromID(idNumber) {
    const year = parseInt(idNumber.substr(0, 2));
    const month = parseInt(idNumber.substr(2, 2));
    const day = parseInt(idNumber.substr(4, 2));
    
    // Determine full year (1900s or 2000s)
    const currentYear = new Date().getFullYear() % 100;
    const fullYear = year <= currentYear ? 2000 + year : 1900 + year;
    
    // Create and validate date
    const date = new Date(fullYear, month - 1, day);
    if (date.getFullYear() !== fullYear || date.getMonth() + 1 !== month || date.getDate() !== day) {
        return null; // Invalid date
    }
    
    return {
        date: date,
        formattedDate: `${fullYear}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`
    };
}

/**
 * Extract gender from ID number
 * @param {string} idNumber - The ID number
 * @returns {string} - 'M' for male, 'F' for female
 */
function extractGenderFromID(idNumber) {
    const genderDigit = parseInt(idNumber.substr(6, 1));
    return genderDigit < 5 ? 'F' : 'M';
}

/**
 * Complete ID validation with all checks
 * @param {string} idNumber - The ID number to validate
 * @returns {object} - Validation result with details
 */
function validateSAID(idNumber) {
    // Basic format check
    if (!/^\d{13}$/.test(idNumber)) {
        return { valid: false, message: 'ID number must be 13 digits.' };
    }
    
    // Date validation
    const dateInfo = extractDateFromID(idNumber);
    if (!dateInfo) {
        return { valid: false, message: 'ID contains invalid date.' };
    }
    
    // Luhn validation
    if (!validateSouthAfricanID(idNumber)) {
        return { valid: false, message: 'ID number checksum is invalid.' };
    }
    
    // If we got here, ID is valid
    return { 
        valid: true, 
        message: 'Valid ID number.',
        gender: extractGenderFromID(idNumber),
        dateOfBirth: dateInfo.formattedDate
    };
}
