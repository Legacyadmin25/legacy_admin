import json
import logging
import openai
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = settings.OPENAI_API_KEY

def parse_ai_query(query, user):
    """
    Parse natural language query into structured format using OpenAI
    
    Args:
        query (str): Natural language query from user
        user (User): The user making the request
        
    Returns:
        dict: Parsed query with report_type and filters
    """
    try:
        # Define the system message with instructions for the AI
        system_message = """You are a Django reporting assistant. Convert user questions into structured JSON with report_type and filters. 
        
        Available report types:
        - commissions: Agent commission reports
        - lapses: Policy lapse reports
        - claims: Insurance claims reports
        - payments: Payment reports
        - debit_orders: Debit order collection reports
        
        Example outputs:
        
        User: "Show me commissions for John in March"
        {"report_type": "commissions", "filters": {"agent": "John", "month": "2024-03"}}
        
        User: "List all lapsed policies this month"
        {"report_type": "lapses", "filters": {"start_date": "2024-05-01", "end_date": "2024-05-31"}}
        
        User: "Claims paid last quarter"
        {"report_type": "claims", "filters": {"status": "paid", "start_date": "2024-01-01", "end_date": "2024-03-31"}}
        
        Only return valid JSON. Do not include any other text or formatting."""
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # Extract and parse the response
        result = response.choices[0].message.content.strip()
        parsed = json.loads(result)
        
        # Log the AI request
        log_ai_request(
            user=user,
            request_type='query_parsing',
            input_data=query,
            output_data=parsed,
            success=True
        )
        
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {result}")
        log_ai_request(
            user=user,
            request_type='query_parsing',
            input_data=query,
            output_data=str(e),
            success=False
        )
        raise ValueError("Could not process your query. Please try rephrasing.")
    except Exception as e:
        logger.exception("Error in parse_ai_query")
        log_ai_request(
            user=user,
            request_type='query_parsing',
            input_data=query,
            output_data=str(e),
            success=False
        )
        raise


def generate_ai_summary(report_type, report_data, filters):
    """
    Generate a natural language summary of the report data using AI
    
    Args:
        report_type (str): Type of report
        report_data (dict): The report data to summarize
        filters (dict): Filters applied to the report
        
    Returns:
        str: Natural language summary
    """
    try:
        # Prepare the prompt
        prompt = f"""You are a data analyst. Create a concise, insightful summary of this {report_type} report.
        
        Report filters: {json.dumps(filters, indent=2)}
        
        Summary statistics: {json.dumps(report_data.get('summary', {}), indent=2)}
        
        First few rows of data: {json.dumps(report_data.get('rows', [])[:5], indent=2)}
        
        Focus on key insights, trends, and any notable patterns. Keep it under 3 sentences."""
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful data analyst assistant that provides clear, concise summaries of data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Log the AI request
        log_ai_request(
            user=None,  # System-generated, no specific user
            request_type=f'summary_{report_type}',
            input_data={"filters": filters, "row_count": len(report_data.get('rows', []))},
            output_data=summary,
            success=True
        )
        
        return summary
        
    except Exception as e:
        logger.exception("Error generating AI summary")
        log_ai_request(
            user=None,
            request_type=f'summary_{report_type}',
            input_data={"filters": filters},
            output_data=str(e),
            success=False
        )
        return ""


def log_ai_request(user, request_type, input_data, output_data, success):
    """
    Log an AI request to the database
    
    Args:
        user: The user making the request (or None for system)
        request_type (str): Type of request (e.g., 'query_parsing', 'summary_commissions')
        input_data: The input sent to the AI
        output_data: The output received from the AI
        success (bool): Whether the request was successful
    """
    from .models import AIRequestLog
    
    try:
        # Convert input/output to string if they're not already
        if not isinstance(input_data, str):
            input_data = json.dumps(input_data, indent=2)
        if not isinstance(output_data, str):
            output_data = json.dumps(output_data, indent=2)
        
        # Truncate if necessary
        input_data = input_data[:4000] if input_data else ""
        output_data = output_data[:4000] if output_data else ""
        
        # Create the log entry
        AIRequestLog.objects.create(
            user=user,
            request_type=request_type,
            input_data=input_data,
            response_data=output_data,
            success=success,
            response_time=0  # We don't track this for now
        )
        
    except Exception as e:
        logger.exception(f"Failed to log AI request: {str(e)}")


def get_date_range_description(filters):
    """Generate a human-readable date range description from filters"""
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    
    if start_date and end_date:
        return f"from {start_date} to {end_date}"
    elif start_date:
        return f"since {start_date}"
    elif end_date:
        return f"until {end_date}"
    else:
        return "for all time"


def get_relative_date_range(days=30):
    """Get a date range relative to today"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    return {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
