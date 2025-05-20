"""
AI Privacy Controls Module

This module implements privacy safeguards for all AI interactions in the system,
ensuring compliance with POPIA, FSCA, and ethical data handling standards.

Key features:
- PII detection and redaction
- AI request logging
- Consent management
- Secure API handling
"""

import re
import json
import logging
import datetime
from django.conf import settings
from django.contrib.auth.models import User

# Configure logging
logger = logging.getLogger(__name__)

# PII detection patterns
PII_PATTERNS = {
    'sa_id_number': r'\b(((\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01]))\d{7})\b',
    'phone_number': r'\b(0\d{9}|27\d{9}|\+27\d{9})\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'banking_info': r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b',  # Credit card pattern
    'account_number': r'\b\d{10,12}\b'  # Bank account number pattern
}

class AIPrivacyLog:
    """Model for logging AI requests"""
    
    @staticmethod
    def log_ai_request(user, action, prompt_summary=None, model_used=None):
        """
        Log an AI request to the database
        
        Args:
            user: The user making the request
            action: The type of AI action (e.g., 'search', 'summarize')
            prompt_summary: A high-level summary of the prompt (no PII)
            model_used: The AI model used
        """
        from settings_app.models import AIRequestLog
        
        try:
            # Create log entry
            log_entry = AIRequestLog(
                user=user,
                action=action,
                prompt_summary=prompt_summary,
                model_used=model_used or settings.DEFAULT_OPENAI_MODEL,
                timestamp=datetime.datetime.now()
            )
            log_entry.save()
            return log_entry.id
        except Exception as e:
            logger.error(f"Failed to log AI request: {str(e)}")
            return None


def redact_pii(text):
    """
    Redact personally identifiable information from text
    
    Args:
        text: The text to redact
        
    Returns:
        Redacted text with PII replaced by placeholders
    """
    if not text:
        return text
        
    redacted = text
    
    # Apply each PII pattern
    for pii_type, pattern in PII_PATTERNS.items():
        placeholder = f"[REDACTED_{pii_type.upper()}]"
        redacted = re.sub(pattern, placeholder, redacted)
    
    # Additional patterns specific to funeral policies and financial services
    policy_patterns = {
        'policy_number': r'\b([A-Z]{2,3}\d{5,7})\b',  # Common policy number format
        'claim_number': r'\b(CL\d{6,8})\b',  # Claim number format
    }
    
    for pii_type, pattern in policy_patterns.items():
        placeholder = f"[REDACTED_{pii_type.upper()}]"
        redacted = re.sub(pattern, placeholder, redacted)
    
    # Name redaction for specific contexts
    # This is a simplified approach - in production, you might use NER models
    name_indicators = [
        "dependent name", "beneficiary name", "child name", "spouse name",
        "dependent:", "beneficiary:", "child:", "spouse:", "main member:", "main member name",
        "policyholder:", "policyholder name", "claimant:", "claimant name"
    ]
    
    # Address redaction indicators
    address_indicators = [
        "address:", "residential address", "postal address", "physical address",
        "street address", "home address", "work address"
    ]
    
    lines = redacted.split('\n')
    for i, line in enumerate(lines):
        # Check for name indicators
        for indicator in name_indicators:
            if indicator.lower() in line.lower():
                # Redact the rest of the line after the indicator
                pattern = re.compile(f"({re.escape(indicator)})(.*)", re.IGNORECASE)
                lines[i] = pattern.sub(r"\1 [REDACTED_NAME]", line)
                break
        
        # Check for address indicators
        for indicator in address_indicators:
            if indicator.lower() in line.lower():
                # Redact the rest of the line after the indicator
                pattern = re.compile(f"({re.escape(indicator)})(.*)", re.IGNORECASE)
                lines[i] = pattern.sub(r"\1 [REDACTED_ADDRESS]", line)
                break
    
    # Redact any potential ID numbers that might not match the standard format
    # Look for sequences that might be ID numbers (digit sequences of appropriate length)
    potential_id_pattern = r'\b\d{10,13}\b'
    redacted = re.sub(potential_id_pattern, "[REDACTED_POTENTIAL_ID]", '\n'.join(lines))
    
    return redacted


def prepare_ai_prompt(prompt_text, context_data=None, include_pii=False, format_type='default'):
    """
    Prepare a prompt for sending to the AI, with PII redaction if needed
    
    Args:
        prompt_text: The base prompt text
        context_data: Additional context data to include
        include_pii: Whether to include PII (should almost always be False)
        format_type: How to format the context data ('default', 'json', 'table', 'key_value')
        
    Returns:
        Prepared prompt with context and PII handling
    """
    full_prompt = prompt_text.strip()
    
    # Add privacy reminder to all prompts
    privacy_reminder = (
        "\n\nIMPORTANT: Do not include, request, or generate any personally identifiable "
        "information (PII) in your response. All responses must comply with POPIA "
        "and FSCA regulations for data protection."
    )
    
    # Add context data if provided
    if context_data:
        # Format the context data based on the specified format type
        if format_type == 'json' and isinstance(context_data, (dict, list)):
            # Format as JSON
            try:
                context_str = json.dumps(context_data, indent=2)
            except Exception as e:
                logger.warning(f"Error formatting context as JSON: {str(e)}")
                context_str = str(context_data)
        
        elif format_type == 'table' and isinstance(context_data, list) and all(isinstance(item, dict) for item in context_data):
            # Format as ASCII table for lists of dictionaries
            try:
                # Get all unique keys
                all_keys = set()
                for item in context_data:
                    all_keys.update(item.keys())
                
                # Create header row
                header = " | ".join(all_keys)
                separator = "-" * len(header)
                
                # Create data rows
                rows = []
                for item in context_data:
                    row_values = [str(item.get(key, '')) for key in all_keys]
                    rows.append(" | ".join(row_values))
                
                context_str = f"{header}\n{separator}\n" + "\n".join(rows)
            except Exception as e:
                logger.warning(f"Error formatting context as table: {str(e)}")
                context_str = str(context_data)
        
        elif format_type == 'key_value' and isinstance(context_data, dict):
            # Format as key-value pairs
            try:
                context_str = "\n".join([f"{key}: {value}" for key, value in context_data.items()])
            except Exception as e:
                logger.warning(f"Error formatting context as key-value pairs: {str(e)}")
                context_str = str(context_data)
        
        else:
            # Default formatting
            context_str = str(context_data)
        
        # Redact PII from context if needed
        if not include_pii:
            context_str = redact_pii(context_str)
            
        full_prompt += f"\n\nContext:\n{context_str}"
    
    # Final PII check on the full prompt
    if not include_pii:
        full_prompt = redact_pii(full_prompt)
    
    # Add the privacy reminder
    full_prompt += privacy_reminder
    
    return full_prompt


def get_ai_consent_message():
    """
    Get the standard AI consent message to display to users
    
    Returns:
        HTML-formatted consent message
    """
    return """
    <div class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
        <p class="text-sm text-blue-700">
            <strong>Note:</strong> This assistant helps explain products but does not provide financial advice. 
            Data is processed securely and never stored.
        </p>
    </div>
    """


def verify_api_key_security():
    """
    Verify that the OpenAI API key is properly secured
    
    Returns:
        (bool, str): Success status and message
    """
    # Check if API key is configured
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        return False, "OpenAI API key is not configured"
    
    # Check if API key is in environment variables
    import os
    if 'OPENAI_API_KEY' not in os.environ:
        return False, "OpenAI API key should be stored in environment variables"
    
    # Check if default model is configured
    default_model = getattr(settings, 'DEFAULT_OPENAI_MODEL', None)
    if not default_model:
        return False, "Default OpenAI model is not configured"
    
    return True, "API key security verified"
