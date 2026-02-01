from django.shortcuts import redirect
from django.urls import resolve

class AdminLoginRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request path is for login
        if request.path == '/accounts/login/' and 'next' in request.GET:
            # Redirect to admin login with the same next parameter
            next_url = request.GET.get('next', '/')
            return redirect(f'/admin/login/?next={next_url}')
        
        response = self.get_response(request)
        return response