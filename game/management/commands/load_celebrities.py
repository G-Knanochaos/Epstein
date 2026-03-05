"""
Management command to load celebrity data from celebrities.json into the DB.

Usage:
    python manage.py load_celebrities
    python manage.py load_celebrities --clear   # wipe table first
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from game.models import Celebrity


class Command(BaseCommand):
    help = 'Load celebrities from celebrities.json into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing celebrities before loading',
        )
        parser.add_argument(
            '--prune-zeros',
            action='store_true',
            help='Delete existing celebrities with 0 or negative epstein_mentions',
        )

    def handle(self, *args, **options):
        json_path = Path(__file__).resolve().parents[4] / 'Epstein' / 'celebrities.json'
        if not json_path.exists():
            # fallback: same directory as manage.py
            json_path = Path(__file__).resolve().parents[4] / 'celebrities.json'
        if not json_path.exists():
            self.stderr.write(f'File not found: {json_path}')
            return

        if options['clear']:
            count = Celebrity.objects.count()
            Celebrity.objects.all().delete()
            self.stdout.write(f'Cleared {count} existing celebrities.')

        if options['prune_zeros']:
            count = Celebrity.objects.filter(epstein_mentions__lte=0).count()
            Celebrity.objects.filter(epstein_mentions__lte=0).delete()
            self.stdout.write(f'Pruned {count} celebrities with 0 mentions.')

        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)

        created = updated = skipped = 0
        for item in data:
            if item.get('epstein_mentions', 0) <= 0:
                skipped += 1
                continue
            obj, was_created = Celebrity.objects.update_or_create(
                full_name=item['full_name'],
                defaults={
                    'description': item.get('description', ''),
                    'extract': item.get('extract', ''),
                    'image_url': item.get('image_url', ''),
                    'wikipedia_url': item.get('wikipedia_url', ''),
                    'wikipedia_slug': item.get('wikipedia_slug', ''),
                    'epstein_mentions': item.get('epstein_mentions', 0),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done: {created} created, {updated} updated, {skipped} skipped (0 mentions) '
                f'({len(data)} total in file)'
            )
        )
