import logging

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


def shorten_url(long_url):
    """Create a short share URL using the configured provider."""
    bitly_token = getattr(settings, 'BITLY_ACCESS_TOKEN', '')
    tinyurl_token = getattr(settings, 'TINYURL_API_TOKEN', '')
    timeout = getattr(settings, 'SHORT_LINK_TIMEOUT', 10)

    if bitly_token:
        headers = {
            'Authorization': f'Bearer {bitly_token}',
            'Content-Type': 'application/json',
        }
        response = requests.post(
            'https://api-ssl.bitly.com/v4/shorten',
            json={'long_url': long_url},
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data['link'], 'bitly'

    if tinyurl_token:
        headers = {
            'Authorization': f'Bearer {tinyurl_token}',
            'Content-Type': 'application/json',
        }
        response = requests.post(
            'https://api.tinyurl.com/create',
            json={'url': long_url},
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data['data']['tiny_url'], 'tinyurl'

    raise ValueError('No API-based short-link provider is configured')


def maybe_shorten_url(long_url):
    try:
        return shorten_url(long_url)
    except Exception as exc:
        logger.warning('Short link generation failed for %s: %s', long_url, exc)
        return None, None