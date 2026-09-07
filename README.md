# Megano — итоговый дипломный проект (интернет-магазин)

## Развёртывание

1. `git clone <ссылка на репозиторий>`
2. Скопировать `.env.example` в `.env` и заполнить значения
3. Создать и активировать виртуальное окружение, установить зависимости: `pip install -r requirements.txt`
4. Собрать и установить пакет `frontend` (см. `diploma-frontend/README.md`)
5. `python manage.py migrate`
6. `python manage.py runserver 0.0.0.0:8000`

Раздел будет дополняться по ходу разработки.
