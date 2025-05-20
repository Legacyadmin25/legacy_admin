# UI Style Guide Implementation

This document outlines how to implement the UI style guide across all pages in the LegacyAdmin application to ensure a consistent look and feel.

## Overview

All pages should use exactly the same look & feel as Steps 1-2 of the Create-Policy flow, including:
- Find Policy
- Make a Payment
- Payment History
- Submit Claim
- Claim Status
- Reports (Plan Fee & Full Policy)
- All Imports submenus
- All Settings submenus

## Implementation Method

We've created a comprehensive UI style guide implementation that includes:

1. **CSS Styles**: `static/css/ui_style_guide.css`
2. **JavaScript Utilities**: `static/js/ui_style_guide.js`
3. **Template Snippets**:
   - `templates/ui_style_guide.html` (included in base.html)
   - `templates/ui_style_guide_form.html` (for form-specific pages)

## Style Guide Standards

### 1. Typography
- **Font stack:** `font-sans` (Inter, system-ui, sans-serif)
- **Body text:** `text-base leading-relaxed`
- **Headings:** `text-lg font-semibold text-gray-900 mb-4`
- **Labels:** `text-sm font-medium text-gray-700 mb-1`

### 2. Form Fields
- **Markup for every `<label>` + `<input>` / `<select>` / `<textarea>`:**
  ```html
  <label class="block text-sm font-medium text-gray-700 mb-1">
    <!-- Field Label -->
  </label>
  <input
    class="mt-1 block w-full pl-3 pr-10 py-2 border border-gray-300 rounded-md bg-gray-50
           focus:outline-none focus:ring-2 focus:ring-blue-500"
    …
  />
  ```
- **Placeholder / text color:** `text-gray-600`
- **Error state on field:**  
  - Border: `border-red-500`  
  - Help text: `<p class="text-xs text-red-600 mt-1">Error message</p>`

### 3. Spacing & Layout
- **Form rows:** wrap each label+field pair in a container with `mb-6`
- **Main wrapper:**  
  ```html
  <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- page content -->
  </div>
  ```
- **Section headings:** `text-lg font-semibold text-gray-900 mb-4`

### 4. Navigation (Steps / Tabs / Sidebar)
- **Step bar / tabs:**  
  ```html
  <nav class="flex items-center space-x-4 border-b border-gray-200 mb-8">
    <a href="#" class="pb-2 text-blue-600 border-b-2 border-blue-600">Step 1</a>
    <a href="#" class="pb-2 text-gray-500 hover:text-gray-700">Step 2</a>
    <!-- etc. -->
  </nav>
  ```
- **Sidebar & submenus:** Already implemented in base.html

### 5. Color Palette
- **Page background:** `bg-gray-50` (preferred) or `bg-gray-100`
- **Containers:** `bg-white`
- **Inputs:** `bg-gray-50`
- **Borders:** `border-gray-300`
- **Text:**  
  - Body: `text-gray-700`  
  - Headings: `text-gray-900`  
  - Sidebar links: `text-white`

## How to Apply to New Pages

### For Regular Pages

1. Ensure the page extends the base template:
   ```html
   {% extends "base.html" %}
   ```

2. For form-heavy pages, include the form style guide:
   ```html
   {% include "ui_style_guide_form.html" %}
   ```

3. Structure your content with the proper layout:
   ```html
   <div class="bg-white rounded-lg shadow overflow-hidden">
     <div class="p-6">
       <!-- Your content here -->
     </div>
   </div>
   ```

4. Use the proper heading structure:
   ```html
   <h3 class="text-lg font-semibold text-gray-900 mb-4 border-b pb-2">Section Title</h3>
   ```

5. For form fields, follow this pattern:
   ```html
   <div class="mb-6">
     <label class="block text-sm font-medium text-gray-700 mb-1">
       Field Label
     </label>
     <input
       class="mt-1 block w-full pl-3 pr-10 py-2 border border-gray-300 rounded-md bg-gray-50
              focus:outline-none focus:ring-2 focus:ring-blue-500"
       type="text"
     />
   </div>
   ```

## Testing Your Implementation

After applying these styles, check that:

1. All typography uses the Inter font family
2. Form fields have consistent styling with gray backgrounds
3. The page background is light gray
4. Content containers have white backgrounds with subtle shadows
5. Spacing between form elements is consistent
6. Navigation elements follow the tab/step bar pattern when appropriate

## Troubleshooting

If styles aren't applying correctly:

1. Check browser console for errors
2. Ensure the base template is properly extended
3. Check for inline styles that might be overriding the style guide
4. Verify that the proper CSS classes are applied to elements

## Additional Resources

For more information, refer to the example pages:
- `members/templates/members/step1_personal_address.html`
- `members/templates/members/step2_policy_details.html`
