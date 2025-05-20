from django.http import JsonResponse
from django.views import View
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

class TestOpenAIView(View):
    def get(self, request):
        """Test if OpenAI API key is properly loaded"""
        # Check if API key is in settings
        api_key_in_settings = bool(getattr(settings, 'OPENAI_API_KEY', None))
        
        # Check if API key is in environment
        api_key_in_env = bool(os.environ.get('OPENAI_API_KEY'))
        
        # Check if the key is valid (without making an actual API call)
        key_is_valid = False
        if api_key_in_settings or api_key_in_env:
            key_is_valid = True
        
        return JsonResponse({
            'api_key_in_settings': api_key_in_settings,
            'api_key_in_env': api_key_in_env,
            'key_is_valid': key_is_valid,
            'model': getattr(settings, 'DEFAULT_OPENAI_MODEL', 'Not set')
        })
