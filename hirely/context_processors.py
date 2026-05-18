from django.conf import settings


def analytics_keys(request):
    return {
        'POSTHOG_API_KEY': settings.POSTHOG_API_KEY,
        'SENTRY_DSN': settings.SENTRY_DSN,
    }
