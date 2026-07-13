from core.breadcrumbs import update_breadcrumb_trail


class BreadcrumbMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.breadcrumbs = []
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.breadcrumbs = update_breadcrumb_trail(request)
        return None
