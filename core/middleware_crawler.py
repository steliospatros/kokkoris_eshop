"""Strip session cookies from crawler-facing endpoints (sitemap / robots)."""


class StripCrawlerCookiesMiddleware:
    """
    Google Search Console sometimes reports "Couldn't fetch" when /sitemap.xml
    sets a session cookie. Keep these responses cookie-free and cacheable.
    """

    PATHS = frozenset({"/sitemap.xml", "/robots.txt"})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path not in self.PATHS:
            return response
        if hasattr(response, "cookies"):
            response.cookies.clear()
        if "Set-Cookie" in response:
            del response["Set-Cookie"]
        vary = response.get("Vary", "")
        if vary:
            parts = [p.strip() for p in vary.split(",") if p.strip().lower() != "cookie"]
            if parts:
                response["Vary"] = ", ".join(parts)
            else:
                del response["Vary"]
        response["Cache-Control"] = "public, max-age=3600"
        return response
