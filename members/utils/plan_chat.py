import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def get_plan_answer(question, plan, tiers=None):
    """
    Get an answer to a question about a plan using AI.
    
    Args:
        question (str): The user's question
        plan (Plan): The plan object
        tiers (list): Optional list of tier objects
        
    Returns:
        str: The AI-generated answer
    """
    try:
        # Try OpenAI if configured
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            return get_answer_from_openai(question, plan, tiers)
        
        # Fallback to a simple rule-based approach
        return get_answer_from_rules(question, plan, tiers)
    except Exception as e:
        logger.error(f"Error getting plan answer: {str(e)}")
        return "I'm sorry, I couldn't process your question. Please try again or contact customer support."

def get_answer_from_openai(question, plan, tiers=None):
    """
    Get an answer using OpenAI API
    
    Args:
        question (str): The user's question
        plan (Plan): The plan object
        tiers (list): Optional list of tier objects
        
    Returns:
        str: The AI-generated answer
    """
    try:
        api_key = settings.OPENAI_API_KEY
        
        # Prepare plan information
        plan_info = f"""
        Plan Name: {plan.name}
        Description: {plan.description}
        Policy Type: {plan.policy_type}
        Main Premium: R{plan.premium}
        Main Cover: R{plan.main_cover}
        Waiting Period: {plan.waiting_period} months
        Lapse Period: {plan.lapse_period} months
        Spouses Allowed: {plan.spouses_allowed}
        Children Allowed: {plan.children_allowed}
        Extended Family Members Allowed: {plan.extended_allowed}
        """
        
        # Add tier information if available
        tier_info = ""
        if tiers:
            tier_info = "Tier Information:\n"
            for tier in tiers:
                tier_info += f"""
                Type: {tier.user_type}
                Age Range: {tier.age_from} to {tier.age_to}
                Cover Amount: R{tier.cover}
                Premium: R{tier.premium}
                """
        
        # Add terms and conditions if available
        terms_info = ""
        if plan.terms_text:
            terms_info = f"Terms and Conditions:\n{plan.terms_text}"
        
        # Prepare the prompt
        prompt = f"""
        You are a helpful assistant that explains funeral policy plans to customers. You are NOT a financial advisor.
        
        Answer the following question about this funeral policy plan:
        
        {plan_info}
        
        {tier_info}
        
        {terms_info}
        
        Question: {question}
        
        Provide a clear, concise answer based ONLY on the information provided above. If you don't know the answer based on the information provided, say so clearly. DO NOT make up information.
        
        Always include this disclaimer at the end of your response: "This explanation is for informational purposes only and does not constitute financial advice."
        """
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that explains funeral policy plans to customers."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return content
        
        # Fallback to rule-based if API fails
        logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
        return get_answer_from_rules(question, plan, tiers)
    except Exception as e:
        logger.error(f"Error with OpenAI: {str(e)}")
        return get_answer_from_rules(question, plan, tiers)

def get_answer_from_rules(question, plan, tiers=None):
    """
    Get an answer using simple rule-based approach
    
    Args:
        question (str): The user's question
        plan (Plan): The plan object
        tiers (list): Optional list of tier objects
        
    Returns:
        str: The answer
    """
    question = question.lower()
    
    # Define some common questions and answers
    if any(keyword in question for keyword in ['cover', 'payout', 'benefit']):
        return f"The main cover amount for this plan is R{plan.main_cover}. This explanation is for informational purposes only and does not constitute financial advice."
    
    elif any(keyword in question for keyword in ['premium', 'cost', 'pay', 'price']):
        return f"The monthly premium for this plan is R{plan.premium}. This explanation is for informational purposes only and does not constitute financial advice."
    
    elif any(keyword in question for keyword in ['spouse', 'husband', 'wife', 'partner']):
        if plan.spouses_allowed > 0:
            spouse_tier = next((t for t in tiers if t.user_type == 'Spouse'), None) if tiers else None
            if spouse_tier:
                return f"This plan covers {plan.spouses_allowed} spouse(s) with a cover amount of R{spouse_tier.cover}. This explanation is for informational purposes only and does not constitute financial advice."
            return f"This plan allows for {plan.spouses_allowed} spouse(s). This explanation is for informational purposes only and does not constitute financial advice."
        return "This plan does not include spouse coverage. This explanation is for informational purposes only and does not constitute financial advice."
    
    elif any(keyword in question for keyword in ['child', 'children', 'kid']):
        if plan.children_allowed > 0:
            child_tier = next((t for t in tiers if t.user_type == 'Child'), None) if tiers else None
            if child_tier:
                return f"This plan covers up to {plan.children_allowed} children with a cover amount of R{child_tier.cover}. This explanation is for informational purposes only and does not constitute financial advice."
            return f"This plan allows for up to {plan.children_allowed} children. This explanation is for informational purposes only and does not constitute financial advice."
        return "This plan does not include children coverage. This explanation is for informational purposes only and does not constitute financial advice."
    
    elif any(keyword in question for keyword in ['extended', 'parent', 'family', 'relative']):
        if plan.extended_allowed > 0:
            extended_tier = next((t for t in tiers if t.user_type == 'Extended'), None) if tiers else None
            if extended_tier:
                return f"This plan covers up to {plan.extended_allowed} extended family members with a cover amount of R{extended_tier.cover}. This explanation is for informational purposes only and does not constitute financial advice."
            return f"This plan allows for up to {plan.extended_allowed} extended family members. This explanation is for informational purposes only and does not constitute financial advice."
        return "This plan does not include extended family coverage. This explanation is for informational purposes only and does not constitute financial advice."
    
    elif any(keyword in question for keyword in ['wait', 'waiting', 'period']):
        return f"This plan has a waiting period of {plan.waiting_period} months. This means benefits will only be payable after this period has passed. This explanation is for informational purposes only and does not constitute financial advice."
    
    elif any(keyword in question for keyword in ['lapse', 'missed', 'payment']):
        return f"This plan has a lapse period of {plan.lapse_period} months. If payments are missed for longer than this period, the policy may lapse. This explanation is for informational purposes only and does not constitute financial advice."
    
    # Default response for unknown questions
    return f"I don't have specific information about that in the plan details. Please contact customer support for more information about {plan.name}. This explanation is for informational purposes only and does not constitute financial advice."
