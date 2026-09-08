from django.middleware.csrf import get_token


class EnsureCsrfCookieMiddleware:
    """Гарантирует, что cookie csrftoken выставляется на каждой странице.

    Шаблоны пакета `frontend` (index.html, signIn.html, signUp.html и т.д.)
    не везде содержат {% csrf_token %} — там, где его нет, Django cookie
    csrftoken без явного вызова не выставит. А JS фронтенда на каждый
    POST/DELETE к /api/ берёт токен именно из этой cookie (заголовок
    X-CSRFToken). Трогать вёрстку/шаблоны пакета нельзя по ТЗ, поэтому
    cookie гарантируем на своей стороне — как это делает декоратор
    @ensure_csrf_cookie, но сразу для всех страниц.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        get_token(request)
        return self.get_response(request)
