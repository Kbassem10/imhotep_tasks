"""
Custom middleware for the application.
"""

class DisableCSRFForAPIMiddleware:
    """
    Middleware to disable CSRF checks for API endpoints.
    
    This is safe because:
    1. API endpoints use JWT authentication (not session-based)
    2. JWT tokens themselves provide CSRF protection
    3. Mobile apps don't send Referer headers, causing CSRF failures
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Mark API requests as CSRF exempt
        # This prevents the CSRF middleware from checking the Referer header
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        
        response = self.get_response(request)
        return response
