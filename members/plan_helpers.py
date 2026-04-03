import logging

logger = logging.getLogger(__name__)

def get_plan_answer(question, plan, tiers=None):
    """
    Get an answer to a question about a plan using simplified logic.
    
    Args:
        question (str): The user's question
        plan (Plan): The plan object
        tiers (list): Optional list of tier objects
        
    Returns:
        str: The answer
    """
    try:
        # Simple rule-based approach
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
        
        # Default response for unknown questions
        return f"I don't have specific information about that in the plan details. Please contact customer support for more information about {plan.name}. This explanation is for informational purposes only and does not constitute financial advice."
    except Exception as e:
        logger.error(f"Error getting plan answer: {str(e)}")
        return "I'm sorry, I couldn't process your question. Please try again or contact customer support."
