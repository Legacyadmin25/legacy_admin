import uuid
from django.utils import timezone
from django.conf import settings

class AutoSaveSessionMiddleware:
    """
    Middleware to ensure sessions have a unique token for auto-save functionality.
    This middleware also tracks the last activity time for sessions.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request - ensure session has auto-save token
        if not request.session.get('autosave_token'):
            request.session['autosave_token'] = str(uuid.uuid4())
            request.session['autosave_created'] = timezone.now().isoformat()
        
        # Update last activity time for the session
        request.session['autosave_last_activity'] = timezone.now().isoformat()
        
        # Continue processing the request
        response = self.get_response(request)
        
        return response


class AgentDetectionMiddleware:
    """
    Middleware to detect and store agent information in the session.
    This is useful for associating incomplete applications with agents.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if we need to detect an agent from URL parameters
        agent_code = request.GET.get('agent')
        if agent_code and not request.session.get('agent_code'):
            # Store the agent code in the session
            request.session['agent_code'] = agent_code
            
            # Try to load the agent from the database
            try:
                from settings_app.models import Agent
                agent = Agent.objects.filter(code=agent_code).first()
                if agent:
                    request.session['agent_id'] = agent.id
                    request.session['agent_name'] = f"{agent.first_name} {agent.last_name}"
                    request.session['branch_id'] = agent.branch_id if agent.branch_id else None
                    request.session['scheme_id'] = agent.scheme_id if agent.scheme_id else None
            except:
                # If there's an error, just continue without setting agent info
                pass
        
        # Continue processing the request
        response = self.get_response(request)
        
        return response
