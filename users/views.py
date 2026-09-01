import json

from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect

from dashboard.spa import spa_shell_html


def login_view(request):
    if request.method == 'POST':
        is_json = request.headers.get('Content-Type', '').startswith('application/json')
        if is_json:
            body = json.loads(request.body or b'{}')
            username, password = body.get('username'), body.get('password')
        else:
            username = request.POST.get('username')
            password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)  # unchanged call
        if user:
            login(request, user)  # unchanged call
            return JsonResponse({'ok': True}) if is_json else redirect('/')
        error = 'Неверный логин или пароль'
        if is_json:
            return JsonResponse({'ok': False, 'error': error}, status=401)
        return redirect('/login/')
    return HttpResponse(spa_shell_html(), content_type='text/html')


def logout_view(request):
    logout(request)
    return redirect('/login/')
