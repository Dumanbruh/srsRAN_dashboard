#!/bin/bash
# srsRAN Dashboard — быстрый старт
set -e

echo "=== srsRAN Dashboard Setup ==="

# 1. Виртуальное окружение
if [ ! -d "venv" ]; then
  python3 -m venv venv
  echo "[OK] venv создан"
fi
source venv/bin/activate

# 2. Зависимости
pip install -q -r requirements.txt
echo "[OK] Зависимости установлены"

# 3. Миграции
python manage.py makemigrations users
python manage.py makemigrations
python manage.py migrate
echo "[OK] База данных готова"

# 4. Суперпользователь (если не существует)
python manage.py shell -c "
from users.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@local.dev', 'admin123', role='admin')
    print('[OK] Создан admin / admin123')
else:
    print('[--] admin уже существует')
"

# 5. Тестовый viewer
python manage.py shell -c "
from users.models import User
if not User.objects.filter(username='viewer').exists():
    User.objects.create_user('viewer', 'viewer@local.dev', 'viewer123', role='viewer')
    print('[OK] Создан viewer / viewer123')
else:
    print('[--] viewer уже существует')
"

echo ""
echo "=== Запуск сервера ==="
echo "  Дашборд:  http://localhost:8000"
echo "  Admin:    admin / admin123"
echo "  Viewer:   viewer / viewer123"
echo ""

python manage.py runserver 0.0.0.0:8000
