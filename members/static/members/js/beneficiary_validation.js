/**
 * Handles ID validation and auto-fill for beneficiary forms
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find all beneficiary forms on the page
    const beneficiaryForms = document.querySelectorAll('.beneficiary-form');
    
    if (beneficiaryForms.length === 0) return;
    
    // Add event listeners to each form
    beneficiaryForms.forEach(form => {
        const idInput = form.querySelector('input[name$="-id_number"]');
        const dobInput = form.querySelector('input[name$="-date_of_birth"]');
        const genderSelect = form.querySelector('select[name$="-gender"]');
        
        if (idInput) {
            // Add input event listener for real-time validation
            idInput.addEventListener('input', function() {
                validateAndFillBeneficiaryID(this, dobInput, genderSelect);
            });
            
            // Also validate on blur in case the user tabs out
            idInput.addEventListener('blur', function() {
                validateAndFillBeneficiaryID(this, dobInput, genderSelect, true);
            });
        }
    });
});

/**
 * Validates a South African ID number and auto-fills date of birth and gender
 * @param {HTMLInputElement} idInput - The ID number input element
 * @param {HTMLInputElement|null} dobInput - The date of birth input element
 * @param {HTMLSelectElement|null} genderSelect - The gender select element
 * @param {boolean} showError - Whether to show error messages
 */
function validateAndFillBeneficiaryID(idInput, dobInput, genderSelect, showError = true) {
    const idNumber = idInput.value.trim();
    const formGroup = idInput.closest('.form-group') || idInput.parentElement;
    let errorElement = formGroup.querySelector('.invalid-feedback');
    
    // Remove existing validation classes and messages
    idInput.classList.remove('is-invalid', 'is-valid');
    if (errorElement) {
        errorElement.remove();
    }
    
    // If empty, just return
    if (!idNumber) return;
    
    // Basic format validation
    if (!/^\d{13}$/.test(idNumber)) {
        if (showError) {
            showValidationError(idInput, 'ID number must be 13 digits');
        }
        return false;
    }
    
    // Validate using Luhn algorithm
    if (!isValidSAID(idNumber)) {
        if (showError) {
            showValidationError(idInput, 'Invalid South African ID number');
        }
        return false;
    }
    
    // If we have a valid ID, extract and fill the date of birth and gender
    const dob = extractDOB(idNumber);
    const gender = extractGender(idNumber);
    
    if (dob && dobInput) {
        // Format date as YYYY-MM-DD for the date input
        const formattedDate = `${dob.getFullYear()}-${String(dob.getMonth() + 1).padStart(2, '0')}-${String(dob.getDate()).padStart(2, '0')}`;
        dobInput.value = formattedDate;
    }
    
    if (gender && genderSelect) {
        // Find the option that matches the gender (case-insensitive)
        const options = Array.from(genderSelect.options);
        const matchingOption = options.find(option => 
            option.value.toLowerCase() === gender.toLowerCase()
        );
        
        if (matchingOption) {
            matchingOption.selected = true;
        }
    }
    
    // Show success state
    idInput.classList.add('is-valid');
    return true;
}

/**
 * Extracts the date of birth from a South African ID number
 * @param {string} idNumber - The 13-digit South African ID number
 * @returns {Date|null} - The date of birth or null if invalid
 */
function extractDOB(idNumber) {
    if (!idNumber || idNumber.length < 13) return null;
    
    const year = parseInt(idNumber.substring(0, 2), 10);
    const month = parseInt(idNumber.substring(2, 4), 10) - 1; // JS months are 0-11
    const day = parseInt(idNumber.substring(4, 6), 10);
    
    // Handle Y2K - IDs after 2000 have 00-99 as years, so we need to adjust
    const currentYear = new Date().getFullYear();
    const currentCentury = Math.floor(currentYear / 100) * 100;
    const fullYear = currentCentury - 100 + year > currentYear - 100 ? 
                     currentCentury - 100 + year : 
                     currentCentury + year;
    
    // Create the date (months are 0-11 in JS)
    const dob = new Date(fullYear, month, day);
    
    // Check if the date is valid
    if (isNaN(dob.getTime())) {
        return null;
    }
    
    return dob;
}

/**
 * Extracts the gender from a South African ID number
 * @param {string} idNumber - The 13-digit South African ID number
 * @returns {string} - 'M' for male, 'F' for female
 */
function extractGender(idNumber) {
    if (!idNumber || idNumber.length < 13) return '';
    
    // The 7th digit (0-9) indicates gender: 0-4 = female, 5-9 = male
    const genderDigit = parseInt(idNumber.charAt(6), 10);
    return genderDigit < 5 ? 'F' : 'M';
}

/**
 * Validates a South African ID number using the Luhn algorithm
 * @param {string} idNumber - The ID number to validate
 * @returns {boolean} - True if valid, false otherwise
 */
function isValidSAID(idNumber) {
    if (!idNumber || idNumber.length !== 13 || !/^\d+$/.test(idNumber)) {
        return false;
    }
    
    // Luhn algorithm implementation
    let sum = 0;
    let double = false;
    
    // Process each digit from right to left
    for (let i = idNumber.length - 1; i >= 0; i--) {
        let digit = parseInt(idNumber.charAt(i), 10);
        
        if (double) {
            digit *= 2;
            if (digit > 9) {
                digit = (digit % 10) + 1;
            }
        }
        
        sum += digit;
        double = !double;
    }
    
    return (sum % 10) === 0;
}

/**
 * Shows a validation error message
 * @param {HTMLElement} input - The input element
 * @param {string} message - The error message to display
 */
function showValidationError(input, message) {
    const formGroup = input.closest('.form-group') || input.parentElement;
    
    // Remove any existing error messages
    const existingError = formGroup.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
    
    // Add error class to input
    input.classList.add('is-invalid');
    
    // Create and append error message
    const errorElement = document.createElement('div');
    errorElement.className = 'invalid-feedback';
    errorElement.textContent = message;
    
    // Insert after the input
    input.insertAdjacentElement('afterend', errorElement);
}
