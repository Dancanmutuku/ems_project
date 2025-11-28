from django.core.exceptions import PermissionDenied
from functools import wraps

def group_required(group_name):
    """
    Restrict access to users in a specific group.
    Unauthenticated users are redirected to login.
    Authenticated users without the group get 403.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                # Redirect to login page automatically
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

            if user.groups.filter(name=group_name).exists():
                return view_func(request, *args, **kwargs)

            # Authenticated but not in the group
            raise PermissionDenied("You do not have access to this page.")
        return _wrapped_view
    return decorator

