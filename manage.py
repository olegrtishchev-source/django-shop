#!/usr/bin/env python
"""Утилита командной строки Django для административных задач."""
import os
import sys


def main():
    """Точка входа для административных задач."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megano.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что он установлен и "
            "доступен в переменной окружения PYTHONPATH. Вы забыли активировать "
            "виртуальное окружение?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
