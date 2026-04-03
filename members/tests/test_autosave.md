# DIY Application Auto-Save Test Plan

This document outlines the test cases for verifying the DIY application auto-save functionality.

## Backend Tests

### Middleware Tests

1. **AutoSaveSessionMiddleware**
   - Verify that new sessions are assigned a unique auto-save token
   - Verify that the last activity time is updated on each request
   - Verify that existing tokens are preserved across requests

2. **AgentDetectionMiddleware**
   - Verify agent detection from URL parameters
   - Verify agent information is stored in session
   - Verify error handling when agent doesn't exist

### API Endpoint Tests

1. **Auto-Save Application Endpoint**
   - Verify saving form data for a new application
   - Verify updating form data for an existing application
   - Verify error handling for invalid requests

2. **Check Application Exists Endpoint**
   - Verify response when application exists
   - Verify response when application doesn't exist
   - Verify security checks for user/session matching

3. **Mark Application Abandoned/Completed Endpoints**
   - Verify status changes correctly
   - Verify security checks for user/session matching

### Resume Application View Tests

1. **ResumeApplicationView**
   - Verify rendering with valid application token
   - Verify security checks for user/session matching
   - Verify error handling for invalid tokens

## Frontend Tests

### Auto-Save JavaScript Tests

1. **Initialization**
   - Verify event listeners are attached to form inputs
   - Verify periodic auto-save interval is started
   - Verify check for incomplete applications runs on init

2. **Form Data Collection**
   - Verify all form input types are correctly collected
   - Verify data is correctly formatted for API

3. **Auto-Save Functionality**
   - Verify debounced save on input changes
   - Verify periodic save on interval
   - Verify retry logic on save failure

4. **Incomplete Application Check**
   - Verify token retrieval from URL and localStorage
   - Verify API call to check for incomplete application
   - Verify resume modal is shown when application exists

5. **Save for Later**
   - Verify immediate save on button click
   - Verify modal display with token and resume link
   - Verify copy to clipboard functionality

### Auto-Save Modal Tests

1. **Modal Display**
   - Verify modal shows during saving
   - Verify modal shows success message after save
   - Verify modal shows error message on failure
   - Verify modal shows resume option for existing applications

2. **Modal Interactions**
   - Verify close button functionality
   - Verify resume button redirects to correct URL
   - Verify continue button closes modal
   - Verify copy link button copies URL to clipboard

## Integration Tests

1. **End-to-End Flow**
   - Complete a form step and verify auto-save
   - Close browser and reopen to verify resume functionality
   - Test save-for-later flow with link sharing
   - Test agent association with saved applications

2. **Edge Cases**
   - Test with network interruptions
   - Test with very large form data
   - Test with multiple tabs/browsers
   - Test with session expiration

## Manual Testing Checklist

- [ ] Auto-save works on all DIY application steps
- [ ] Auto-save status indicator updates correctly
- [ ] Save-for-later button works and shows modal
- [ ] Resume link works when shared with others
- [ ] Agent information is correctly associated with applications
- [ ] Session token persists across page reloads
- [ ] Application data is correctly loaded when resuming
