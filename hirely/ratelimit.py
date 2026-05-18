"""
Simple IP-based rate limiter using Django's cache framework.
No third-party packages required.
"""
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse


def rate_limit(max_calls: int, period: int, key_prefix: str = ''):
    """
    Decorator: allow at most `max_calls` requests per `period` seconds per IP.
    Returns 429 when exceeded.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method not in ('POST',):
                return view_func(request, *args, **kwargs)
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR', 'unknown')
            )
            cache_key = f'rl:{key_prefix}:{ip}'
            count = cache.get(cache_key, 0)
            if count >= max_calls:
                return HttpResponse(
                    'Too many attempts. Please wait a moment and try again.',
                    status=429,
                    content_type='text/plain',
                )
            cache.set(cache_key, count + 1, timeout=period)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
