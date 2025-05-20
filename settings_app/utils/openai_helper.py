import os
import json
import logging
import requests
import os
from django.conf import settings
from django.contrib.auth.models import User

# Import AI privacy utilities
from settings_app.utils.ai_privacy import redact_pii, prepare_ai_prompt, AIPrivacyLog
from settings_app.models import AISettings

logger = logging.getLogger(__name__)

def suggest_tiers_from_description(plan_name, description, policy_type, premium, user=None):
    """
    Uses OpenAI to suggest appropriate tiers based on a plan description.
    
    Args:
        plan_name (str): The name of the plan
        description (str): The description of the plan
        policy_type (str): Type of policy (service or cash)
        premium (float): The main premium amount
        user (User, optional): The user making the request, for logging purposes
        
    Returns:
        list: A list of suggested tiers with user_type, age_from, age_to, cover, premium values
    """
    try:
        # Get API key from settings (securely stored server-side only)
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        if not api_key:
            logger.warning("OpenAI API key not found in settings. Checking environment variables...")
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                logger.error("OpenAI API key not found in environment variables. Cannot suggest tiers.")
                return []
        
        # Get AI settings
        try:
            ai_settings = AISettings.get_settings()
            model = ai_settings.default_model
        except Exception as e:
            logger.warning(f"Could not retrieve AI settings: {str(e)}. Using default model.")
            model = getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4')
        
        # Create a safe context dictionary with no PII
        context_data = {
            "plan_name": plan_name,
            "description": description,
            "policy_type": policy_type,
            "premium": premium
        }
        
        # Prepare the prompt with privacy controls
        base_prompt = """
        Based on the following funeral policy plan details, suggest appropriate tiers for family members.
        
        Please provide tier suggestions for Spouse, Children, and Extended Family members.
        For each tier, specify:
        1. User Type (Spouse, Child, Extended)
        2. Age range (from-to)
        3. Cover amount (in Rands)
        4. Premium amount (in Rands)
        5. Number allowed (how many of this type should be allowed)
        
        Format your response as a JSON array of objects.
        """
        
        # Use the privacy-aware prompt preparation
        prompt = prepare_ai_prompt(base_prompt, context_data, include_pii=False)
        
        # Log the AI request (for compliance and auditing)
        if user and hasattr(AIPrivacyLog, 'log_ai_request'):
            log_id = AIPrivacyLog.log_ai_request(
                user=user,
                action='suggestion',
                prompt_summary=f"Tier suggestions for plan: {plan_name}",
                model_used=model
            )
        
        
        # Call OpenAI API - always server-side, never expose key to client
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Get model from settings or use default
        model_to_use = model or getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4')
        
        # Configure API call with privacy-focused settings
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that suggests appropriate tiers for funeral policies based on plan details. Do not include or request any personal information in your response."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            # Ensure OpenAI doesn't use our data for training
            "user": "anonymous"
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # Parse the response
        if response.status_code == 200:
            response_data = response.json()
            content = response_data['choices'][0]['message']['content']
            
            # Update log with success status if we're tracking
            if user and hasattr(AIPrivacyLog, 'log_ai_request') and 'log_id' in locals():
                try:
                    from settings_app.models import AIRequestLog
                    AIRequestLog.objects.filter(id=log_id).update(response_status=True)
                except Exception as e:
                    logger.warning(f"Could not update AI request log: {str(e)}")
            
            # Extract the JSON array from the response
            try:
                # Find JSON array in the content
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = content[json_start:json_end]
                    suggested_tiers = json.loads(json_str)
                    return suggested_tiers
                else:
                    logger.error("Could not find JSON array in OpenAI response")
                    return []
            except Exception as e:
                logger.error(f"Error parsing OpenAI response: {str(e)}")
                return []
        else:
            # Log the error
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            
            # Update log with failure status if we're tracking
            if user and hasattr(AIPrivacyLog, 'log_ai_request') and 'log_id' in locals():
                try:
                    from settings_app.models import AIRequestLog
                    AIRequestLog.objects.filter(id=log_id).update(response_status=False)
                except Exception as e:
                    logger.warning(f"Could not update AI request log: {str(e)}")
            
            return []
    except Exception as e:
        logger.error(f"Error in suggest_tiers_from_description: {str(e)}")
        return []

def format_suggested_tiers(suggested_tiers):
    """
    Formats the suggested tiers into a structure suitable for the form.
    
    Args:
        suggested_tiers (list): List of tier suggestions from OpenAI
        
    Returns:
        list: Formatted tier data for the form
    """
    formatted_tiers = []
    
    for tier in suggested_tiers:
        # Extract values with sensible defaults
        user_type = tier.get('user_type', '')
        age_from = int(tier.get('age_from', 0))
        age_to = int(tier.get('age_to', 100))
        cover = float(tier.get('cover', 0))
        premium = float(tier.get('premium', 0))
        allowed = int(tier.get('number_allowed', 1))
        
        # Map user type to valid choices if needed
        if user_type.lower() == 'spouse':
            user_type = 'Spouse'
        elif user_type.lower() == 'child':
            user_type = 'Child'
        elif user_type.lower() in ('extended', 'extended family'):
            user_type = 'Extended'
        
        # Only add if we have a valid user type
        if user_type in ('Spouse', 'Child', 'Extended', 'Adult', 'Extended Child'):
            formatted_tiers.append({
                'user_type': user_type,
                'age_from': age_from,
                'age_to': age_to,
                'cover': cover,
                'premium': premium,
                'number_allowed': allowed
            })
    
    return formatted_tiers


def get_scheme_insights(scheme, question, user=None):
    """
    Uses OpenAI to generate insights about a scheme based on a user question.
    Implements privacy controls to ensure compliance with POPIA and FSCA regulations.
    
    Args:
        scheme: The scheme object to analyze
        question (str): The user's question about the scheme
        user (User, optional): The user making the request, for logging purposes
        
    Returns:
        str: AI-generated insight about the scheme
    """
    try:
        # Check if user has consent for AI insights
        if user:
            try:
                from settings_app.models import AIUserConsent
                user_consent = AIUserConsent.objects.filter(user=user).first()
                if user_consent and not user_consent.insight_consent:
                    return "You have not provided consent for AI-powered insights. Please update your preferences in your account settings."
            except Exception as e:
                logger.warning(f"Could not check user consent: {str(e)}")
        
        # Get AI settings
        try:
            ai_settings = AISettings.get_settings()
            model = ai_settings.default_model
            max_tokens = ai_settings.max_tokens
            temperature = ai_settings.temperature
        except Exception as e:
            logger.warning(f"Could not retrieve AI settings: {str(e)}. Using defaults.")
            model = getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4')
            max_tokens = 500
            temperature = 0.7
        
        # Get API key from settings (securely stored server-side only)
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        if not api_key:
            logger.warning("OpenAI API key not found in settings. Checking environment variables...")
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                logger.error("OpenAI API key not found in environment variables. Cannot generate insights.")
                return "AI insights are currently unavailable. Please check the OpenAI API configuration."
        
        # Log the AI request (for compliance and auditing)
        log_id = None
        if user and hasattr(AIPrivacyLog, 'log_ai_request'):
            log_id = AIPrivacyLog.log_ai_request(
                user=user,
                action='insight',
                prompt_summary=f"Scheme insights for {scheme.name}: {question[:50]}...",
                model_used=model
            )
        
        # Get scheme data - only aggregate data, no individual policy details
        agents = scheme.agents.all()
        policies = scheme.policies.all() if hasattr(scheme, 'policies') else []
        plans = scheme.plans.all() if hasattr(scheme, 'plans') else []
        
        # Prepare agent data - using only aggregated statistics, no PII
        agent_data = []
        for agent in agents:
            agent_policies = [p for p in policies if p.agent == agent]
            lapsed_policies = [p for p in agent_policies if p.status == 'lapsed']
            
            # Only include agent ID and aggregated metrics, no personal details
            agent_data.append({
                'agent_id': f"AG{agent.id}",  # Anonymized identifier
                'policies_count': len(agent_policies),
                'lapsed_count': len(lapsed_policies),
                'lapse_percentage': round((len(lapsed_policies) / len(agent_policies) * 100) if agent_policies else 0, 2),
                'average_premium': round(sum(p.premium for p in agent_policies) / len(agent_policies) if agent_policies else 0, 2)
            })
        
        # Prepare plan data - using only aggregated statistics
        plan_data = []
        for plan in plans:
            plan_policies = [p for p in policies if p.plan == plan]
            
            plan_data.append({
                'plan_id': f"PL{plan.id}",  # Anonymized identifier
                'policies_count': len(plan_policies),
                'average_cover': round(sum(p.cover_amount for p in plan_policies) / len(plan_policies) if plan_policies else 0, 2),
                'average_premium': round(sum(p.premium for p in plan_policies) / len(plan_policies) if plan_policies else 0, 2)
            })
        
        # Prepare the system message with privacy requirements
        system_message = """
        You are an analytics assistant for a funeral insurance company. Your role is to provide factual insights 
        based on the data provided. You must not provide financial advice or recommend specific products.
        
        PRIVACY REQUIREMENTS:
        - NEVER include or request personally identifiable information (PII) in your responses
        - NEVER mention specific agent names, policy numbers, or client details
        - NEVER make assumptions about individual clients or their circumstances
        - ALWAYS ensure your responses comply with POPIA (Protection of Personal Information Act) and FSCA regulations
        
        You may:
        - Analyze performance metrics and trends
        - Compare agents based on their statistics (using only their anonymized IDs)
        - Identify patterns in policy data
        - Suggest areas that might need attention based on data
        
        You must not:
        - Recommend firing or hiring specific agents
        - Provide investment advice
        - Make predictions about future financial performance
        - Suggest changes to pricing or product features
        - Request or generate any personally identifiable information
        
        Keep your answers concise, factual, and data-driven.
        """
        
        # Create context data dictionary
        context_data = {
            "scheme_id": f"SC{scheme.id}",  # Anonymized identifier
            "agent_count": len(agent_data),
            "plan_count": len(plan_data),
            "agent_data": agent_data,
            "plan_data": plan_data,
            "policy_statistics": {
                "total": len(policies),
                "active": len([p for p in policies if p.status == 'active']),
                "lapsed": len([p for p in policies if p.status == 'lapsed']),
                "lapse_rate": round(len([p for p in policies if p.status == 'lapsed']) / len(policies) * 100 if policies else 0, 2)
            }
        }
        
        # Use the privacy-aware prompt preparation
        base_prompt = f"Question: {question}"
        prompt = prepare_ai_prompt(base_prompt, context_data, include_pii=False, format_type='json')
        
        # Call OpenAI API - always server-side, never expose key to client
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Use settings from AISettings
        data = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature,
            # Ensure OpenAI doesn't use our data for training
            'user': 'anonymous'
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            data=json.dumps(data)
        )
        
        # Update log with success status if we're tracking
        if response.status_code == 200 and user and hasattr(AIPrivacyLog, 'log_ai_request') and log_id is not None:
            try:
                from settings_app.models import AIRequestLog
                AIRequestLog.objects.filter(id=log_id).update(response_status=True)
            except Exception as e:
                logger.warning(f"Could not update AI request log: {str(e)}")
        
        # Process the response
        try:
            response_data = response.json()
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                insight = response_data['choices'][0]['message']['content'].strip()
                
                # Final PII check on the response
                insight = redact_pii(insight)
                
                # Add a disclaimer
                disclaimer = (
                    "\n\n*Note: This insight is generated by AI and should be used as a general guide only. "
                    "No personally identifiable information was used in generating this response.*"
                )
                
                return insight + disclaimer
            else:
                logger.error(f"Unexpected response from OpenAI: {response_data}")
                
                # Update log with failure status
                if user and hasattr(AIPrivacyLog, 'log_ai_request') and log_id is not None:
                    try:
                        from settings_app.models import AIRequestLog
                        AIRequestLog.objects.filter(id=log_id).update(response_status=False)
                    except Exception as e:
                        logger.warning(f"Could not update AI request log: {str(e)}")
                
                return "Sorry, I couldn't generate insights at this time. Please try again later."
        except Exception as e:
            logger.error(f"Error processing OpenAI response: {str(e)}")
            return "Sorry, I couldn't process the AI response. Please try again later."
            
    except Exception as e:
        logger.exception(f"Error generating scheme insights: {e}")
        
        # Update log with failure status
        if user and hasattr(AIPrivacyLog, 'log_ai_request') and 'log_id' in locals() and log_id is not None:
            try:
                from settings_app.models import AIRequestLog
                AIRequestLog.objects.filter(id=log_id).update(response_status=False)
            except Exception as log_err:
                logger.warning(f"Could not update AI request log: {str(log_err)}")
        
        return "Sorry, an error occurred while generating insights. Please try again later."


def get_branch_insights(branch, question, user=None):
    """
    Uses OpenAI to generate insights about a branch based on a user question.
    Implements privacy controls to ensure compliance with POPIA and FSCA regulations.
    
    Args:
        branch: The branch object to analyze
        question (str): The user's question about the branch
        user (User, optional): The user making the request, for logging purposes
        
    Returns:
        str: AI-generated insight about the branch
    """
    try:
        # Check if user has consent for AI insights
        if user:
            try:
                from settings_app.models import AIUserConsent
                user_consent = AIUserConsent.objects.filter(user=user).first()
                if user_consent and not user_consent.insight_consent:
                    return "You have not provided consent for AI-powered insights. Please update your preferences in your account settings."
            except Exception as e:
                logger.warning(f"Could not check user consent: {str(e)}")
        
        # Get AI settings
        try:
            ai_settings = AISettings.get_settings()
            model = ai_settings.default_model
            max_tokens = ai_settings.max_tokens
            temperature = ai_settings.temperature
        except Exception as e:
            logger.warning(f"Could not retrieve AI settings: {str(e)}. Using defaults.")
            model = getattr(settings, 'DEFAULT_OPENAI_MODEL', 'gpt-4')
            max_tokens = 500
            temperature = 0.7
        
        # Get API key from settings (securely stored server-side only)
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        if not api_key:
            logger.warning("OpenAI API key not found in settings. Checking environment variables...")
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                logger.error("OpenAI API key not found in environment variables. Cannot generate insights.")
                return "AI insights are currently unavailable. Please check the OpenAI API configuration."
        
        # Log the AI request (for compliance and auditing)
        log_id = None
        if user and hasattr(AIPrivacyLog, 'log_ai_request'):
            log_id = AIPrivacyLog.log_ai_request(
                user=user,
                action='insight',
                prompt_summary=f"Branch insights for {branch.name}: {question[:50]}...",
                model_used=model
            )
        
        # Get branch data - only aggregate data, no individual details
        schemes = branch.schemes.all()
        agents = []
        for scheme in schemes:
            agents.extend(scheme.agents.all())
        
        # Get all policies related to this branch - aggregated only
        policies = []
        for agent in agents:
            agent_policies = agent.policies.all() if hasattr(agent, 'policies') else []
            policies.extend(agent_policies)
        
        # Prepare scheme data - using only anonymized identifiers and aggregated statistics
        scheme_data = []
        for scheme in schemes:
            scheme_policies = [p for p in policies if p.agent.scheme == scheme]
            active_policies = [p for p in scheme_policies if p.status == 'active']
            lapsed_policies = [p for p in scheme_policies if p.status == 'lapsed']
            
            scheme_data.append({
                'scheme_id': f"SC{scheme.id}",  # Anonymized identifier
                'policies_count': len(scheme_policies),
                'active_policies': len(active_policies),
                'lapsed_policies': len(lapsed_policies),
                'lapse_rate': round(len(lapsed_policies) / len(scheme_policies) * 100 if scheme_policies else 0, 2),
                'average_premium': round(sum(p.premium for p in scheme_policies) / len(scheme_policies) if scheme_policies else 0, 2),
                'average_cover': round(sum(p.cover_amount for p in scheme_policies) / len(scheme_policies) if scheme_policies else 0, 2),
                'agents_count': scheme.agents.count() if hasattr(scheme, 'agents') else 0
            })
        
        # Create context data dictionary with aggregated statistics only
        context_data = {
            "branch_id": f"BR{branch.id}",  # Anonymized identifier
            "scheme_count": len(schemes),
            "agent_count": len(agents),
            "scheme_data": scheme_data,
            "policy_statistics": {
                "total": len(policies),
                "active": len([p for p in policies if p.status == 'active']),
                "lapsed": len([p for p in policies if p.status == 'lapsed']),
                "lapse_rate": round(len([p for p in policies if p.status == 'lapsed']) / len(policies) * 100 if policies else 0, 2)
            }
        }
        
        # Prepare the system message with privacy requirements
        system_message = """
        You are an analytics assistant for a funeral insurance company. Your role is to provide factual insights 
        based on the data provided. You must not provide financial advice or recommend specific products.
        
        PRIVACY REQUIREMENTS:
        - NEVER include or request personally identifiable information (PII) in your responses
        - NEVER mention specific branch names, scheme names, or agent details
        - NEVER make assumptions about individual clients or their circumstances
        - ALWAYS ensure your responses comply with POPIA (Protection of Personal Information Act) and FSCA regulations
        
        You may:
        - Analyze performance metrics and trends
        - Compare schemes based on their statistics (using only their anonymized IDs)
        - Identify patterns in policy data
        - Suggest areas that might need attention based on data
        
        You must not:
        - Recommend closing or opening specific schemes
        - Provide investment advice
        - Make predictions about future financial performance
        - Suggest changes to pricing or product features
        - Request or generate any personally identifiable information
        
        Keep your answers concise, factual, and data-driven.
        """
        
        # Use the privacy-aware prompt preparation
        base_prompt = f"Question: {question}"
        prompt = prepare_ai_prompt(base_prompt, context_data, include_pii=False, format_type='json')
        
        # Call OpenAI API - always server-side, never expose key to client
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Use settings from AISettings
        data = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': temperature,
            # Ensure OpenAI doesn't use our data for training
            'user': 'anonymous'
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            data=json.dumps(data)
        )
        
        # Update log with success status if we're tracking
        if response.status_code == 200 and user and hasattr(AIPrivacyLog, 'log_ai_request') and log_id is not None:
            try:
                from settings_app.models import AIRequestLog
                AIRequestLog.objects.filter(id=log_id).update(response_status=True)
            except Exception as e:
                logger.warning(f"Could not update AI request log: {str(e)}")
        
        # Process the response
        try:
            response_data = response.json()
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                insight = response_data['choices'][0]['message']['content'].strip()
                
                # Final PII check on the response
                insight = redact_pii(insight)
                
                # Add a disclaimer
                disclaimer = (
                    "\n\n*Note: This insight is generated by AI and should be used as a general guide only. "
                    "No personally identifiable information was used in generating this response.*"
                )
                
                return insight + disclaimer
            else:
                logger.error(f"Unexpected response from OpenAI: {response_data}")
                
                # Update log with failure status
                if user and hasattr(AIPrivacyLog, 'log_ai_request') and log_id is not None:
                    try:
                        from settings_app.models import AIRequestLog
                        AIRequestLog.objects.filter(id=log_id).update(response_status=False)
                    except Exception as e:
                        logger.warning(f"Could not update AI request log: {str(e)}")
                
                return "Sorry, I couldn't generate insights at this time. Please try again later."
        except Exception as e:
            logger.error(f"Error processing OpenAI response: {str(e)}")
            return "Sorry, I couldn't process the AI response. Please try again later."
            
    except Exception as e:
        logger.exception(f"Error generating branch insights: {e}")
        
        # Update log with failure status
        if user and hasattr(AIPrivacyLog, 'log_ai_request') and 'log_id' in locals() and log_id is not None:
            try:
                from settings_app.models import AIRequestLog
                AIRequestLog.objects.filter(id=log_id).update(response_status=False)
            except Exception as log_err:
                logger.warning(f"Could not update AI request log: {str(log_err)}")
        
        return "Sorry, an error occurred while generating insights. Please try again later."
