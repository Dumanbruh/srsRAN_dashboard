# srsRAN Control Dashboard

Django-дашборд для мониторинга и управления srsRAN с ролевой авторизацией.

## Быстрый старт

```bash
cd srsran_dashboard
chmod +x setup.sh
./setup.sh
```

Откройте http://localhost:8000

## Пользователи

| Логин   | Пароль    | Роль   | Возможности                          |
|---------|-----------|--------|--------------------------------------|
| admin   | admin123  | admin  | Всё: управление UE, pathloss, помехи |
| viewer  | viewer123 | viewer | Только просмотр графиков и метрик    |

Создать дополнительных пользователей: http://localhost:8000/admin/

## Настройки подключения

`proja/settings.py`:

```python
INFLUX_URL   = 'http://localhost:8086'   # InfluxDB v1
INFLUX_DB    = 'srsran'
GNURADIO_URL = 'http://localhost:8080/RPC2'  # GNU Radio XML-RPC
```

## API эндпоинты

| Метод | URL                          | Роль   | Описание                    |
|-------|------------------------------|--------|-----------------------------|
| GET   | /api/stats/                  | any    | Текущие метрики UE          |
| GET   | /api/history/?metric=dl&...  | any    | История для графика         |
| GET   | /api/export/?metric=dl&...   | any    | Скачать CSV                 |
| POST  | /api/ue/<id>/toggle/         | admin  | Вкл/выкл UE                 |
| POST  | /api/ue/<id>/pathloss/       | admin  | Установить pathloss         |
| POST  | /api/noise/                  | admin  | Установить тип/уровень шума |

### Параметры /api/history/

| Параметр | Значения                            | По умолчанию |
|----------|-------------------------------------|--------------|
| metric   | dl, ul, cqi, mcs                    | dl           |
| start    | -5m, -30m, -1h, -6h, ISO datetime  | -30m         |
| end      | now(), ISO datetime                 | now()        |
| interval | 10s, 30s, 1m, 5m                   | 30s          |

## Структура проекта

```
srsran_dashboard/
├── dashboard/          # основное приложение
│   ├── influx.py       # клиент InfluxDB
│   ├── gnuradio.py     # XML-RPC клиент GNU Radio
│   ├── views.py        # все API и страница
│   └── templates/
├── users/              # авторизация и роли
│   ├── models.py       # кастомный User с role
│   └── views.py        # login / logout
├── proja/              # конфиг Django
├── setup.sh            # быстрый старт
└── requirements.txt
```

## Docker

```bash
docker-compose up --build
```
# srsRAN_dashboard
# srsRAN_dashboard
