from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

_INDEX_PATH = Path(settings.BASE_DIR) / 'dashboard' / 'static' / 'spa' / 'index.html'


def spa_shell_html():
    return _INDEX_PATH.read_text(encoding='utf-8')


@login_required
def spa_shell(request):
    return HttpResponse(spa_shell_html(), content_type='text/html')


@login_required
@require_GET
def api_whoami(request):
    return JsonResponse({
        'ok': True,
        'username': request.user.username,
        'role': request.user.role,
        'is_admin': request.user.is_admin_role,
    })


@ensure_csrf_cookie
@require_GET
def api_csrf(request):
    return JsonResponse({'ok': True})
