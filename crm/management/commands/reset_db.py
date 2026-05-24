"""
python manage.py reset_db

Полный сброс базы данных:
  - SQLite: удаляет файл db.sqlite3 и запускает migrate заново
  - PostgreSQL: удаляет все таблицы и запускает migrate заново

После сброса предлагает создать суперпользователя.

Опции:
  --yes   Не спрашивать подтверждения
"""
import os
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Полный сброс базы данных с пересозданием структуры'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true',
                            help='Не спрашивать подтверждения')

    def handle(self, *args, **options):
        self.stdout.write(self.style.ERROR(
            '\n🗑  ПОЛНЫЙ СБРОС БАЗЫ ДАННЫХ\n'
            '   Все данные будут удалены безвозвратно!\n'
            '   (заказы, клиенты, пользователи, настройки — всё)'
        ))

        if not options['yes']:
            confirm = input('\nВы уверены? [да/нет]: ').strip().lower()
            if confirm not in ('да', 'д', 'yes', 'y'):
                self.stdout.write('Отменено.')
                return

        db = settings.DATABASES['default']
        engine = db['ENGINE']

        # ── SQLite ────────────────────────────────────────────────────────────
        if 'sqlite3' in engine:
            db_path = Path(db['NAME'])
            if db_path.exists():
                db_path.unlink()
                self.stdout.write(f'  Удалён файл: {db_path}')
            else:
                self.stdout.write('  Файл БД не найден — пересоздаём.')

        # ── PostgreSQL ────────────────────────────────────────────────────────
        elif 'postgresql' in engine:
            self.stdout.write('  Удаляю все таблицы PostgreSQL...')
            with connection.cursor() as cursor:
                cursor.execute("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (
                            SELECT tablename FROM pg_tables
                            WHERE schemaname = 'public'
                        ) LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
            self.stdout.write('  Все таблицы удалены.')

        else:
            self.stdout.write(self.style.ERROR(f'Неизвестный движок БД: {engine}'))
            return

        # ── Пересоздаём структуру ─────────────────────────────────────────────
        self.stdout.write('\n  Применяю миграции...')
        call_command('migrate', '--run-syncdb', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✓ База пересоздана.\n'))

        # ── Предложить создать суперюзера ─────────────────────────────────────
        create = input('Создать суперпользователя прямо сейчас? [да/нет]: ').strip().lower()
        if create in ('да', 'д', 'yes', 'y'):
            call_command('createsuperuser')
        else:
            self.stdout.write(
                '\nСоздать позже:\n'
                '  python manage.py createsuperuser\n'
            )
