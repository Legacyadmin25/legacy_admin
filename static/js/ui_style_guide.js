/**
 * UI Style Guide Implementation
 * This script applies consistent styling to all pages as per the UI Style Guide
 */

document.addEventListener('DOMContentLoaded', function() {
  // 1. Apply Typography Standards
  document.body.classList.add('font-sans');
  
  // 2. Style Form Fields
  styleFormElements();
  
  // 3. Apply Layout Wrappers
  wrapMainContent();
  
  // 4. Style Section Headings
  styleSectionHeadings();
  
  // 5. Apply Form Row Spacing
  applyFormRowSpacing();
});

/**
 * Applies consistent styling to all form elements
 */
function styleFormElements() {
  // Style all labels
  document.querySelectorAll('label').forEach(label => {
    label.classList.add('block', 'text-sm', 'font-medium', 'text-gray-700', 'mb-1');
  });
  
  // Style all inputs, selects, and textareas
  document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), select, textarea').forEach(input => {
    input.classList.add(
      'mt-1', 'block', 'w-full', 'pl-3', 'pr-10', 'py-2', 
      'border', 'border-gray-300', 'rounded-md', 'bg-gray-50',
      'focus:outline-none', 'focus:ring-2', 'focus:ring-blue-500'
    );
    
    // Remove any conflicting styles
    input.style.boxShadow = '';
    
    // If the input has an error, add error styling
    if (input.classList.contains('is-invalid') || 
        input.closest('.has-error') || 
        input.getAttribute('aria-invalid') === 'true') {
      input.classList.add('border-red-500');
      
      // Find or create error message element
      const errorElement = input.nextElementSibling?.classList.contains('error-message') 
        ? input.nextElementSibling 
        : null;
      
      if (errorElement) {
        errorElement.classList.add('text-xs', 'text-red-600', 'mt-1');
      }
    }
  });
  
  // Style checkboxes and radios differently
  document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(input => {
    const label = input.closest('label') || input.nextElementSibling;
    if (label && label.tagName === 'LABEL') {
      label.classList.remove('block');
      label.classList.add('inline-flex', 'items-center');
    }
  });
}

/**
 * Wraps main content with the proper layout classes
 */
function wrapMainContent() {
  // Find main content container - this will vary by page
  const mainContent = document.querySelector('.container') || 
                      document.querySelector('main') || 
                      document.querySelector('.content');
  
  if (mainContent && !mainContent.classList.contains('max-w-3xl')) {
    mainContent.classList.add('max-w-3xl', 'mx-auto', 'px-4', 'sm:px-6', 'lg:px-8');
  }
  
  // Ensure page has the correct background
  const pageElement = document.querySelector('body > div') || document.body;
  if (!pageElement.classList.contains('bg-gray-50') && !pageElement.classList.contains('bg-gray-100')) {
    pageElement.classList.add('bg-gray-50');
  }
}

/**
 * Styles all section headings consistently
 */
function styleSectionHeadings() {
  // Target common heading elements
  document.querySelectorAll('h3, .section-title, .card-header, .panel-heading').forEach(heading => {
    heading.classList.add('text-lg', 'font-semibold', 'text-gray-900', 'mb-4');
    
    // Add border-bottom if it doesn't already have one
    if (!heading.classList.contains('border-b')) {
      heading.classList.add('border-b', 'pb-2');
    }
  });
}

/**
 * Applies consistent spacing to form rows
 */
function applyFormRowSpacing() {
  // Find form groups/rows and apply consistent spacing
  document.querySelectorAll('.form-group, .form-row, .mb-3').forEach(formGroup => {
    formGroup.classList.add('mb-6');
  });
  
  // If there are no form-group classes, look for label+input pairs
  document.querySelectorAll('label').forEach(label => {
    const formGroup = label.parentElement;
    if (formGroup && !formGroup.classList.contains('mb-6')) {
      formGroup.classList.add('mb-6');
    }
  });
}
