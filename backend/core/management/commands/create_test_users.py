"""
Django management command to create 15 test users with premium access.
These users can login without authentication for testing purposes.

Run with: python manage.py create_test_users
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import User


# 15 Test user emails - these bypass authentication
TEST_USERS = [
    {'email': 'testuser1@volusignal.com', 'first_name': 'Test', 'last_name': 'User1'},
    {'email': 'testuser2@volusignal.com', 'first_name': 'Test', 'last_name': 'User2'},
    {'email': 'testuser3@volusignal.com', 'first_name': 'Test', 'last_name': 'User3'},
    {'email': 'testuser4@volusignal.com', 'first_name': 'Test', 'last_name': 'User4'},
    {'email': 'testuser5@volusignal.com', 'first_name': 'Test', 'last_name': 'User5'},
    {'email': 'testuser6@volusignal.com', 'first_name': 'Test', 'last_name': 'User6'},
    {'email': 'testuser7@volusignal.com', 'first_name': 'Test', 'last_name': 'User7'},
    {'email': 'testuser8@volusignal.com', 'first_name': 'Test', 'last_name': 'User8'},
    {'email': 'testuser9@volusignal.com', 'first_name': 'Test', 'last_name': 'User9'},
    {'email': 'testuser10@volusignal.com', 'first_name': 'Test', 'last_name': 'User10'},
    {'email': 'testuser11@volusignal.com', 'first_name': 'Test', 'last_name': 'User11'},
    {'email': 'testuser12@volusignal.com', 'first_name': 'Test', 'last_name': 'User12'},
    {'email': 'testuser13@volusignal.com', 'first_name': 'Test', 'last_name': 'User13'},
    {'email': 'testuser14@volusignal.com', 'first_name': 'Test', 'last_name': 'User14'},
    {'email': 'testuser15@volusignal.com', 'first_name': 'Test', 'last_name': 'User15'},
]

# List of test emails for easy checking
TEST_USER_EMAILS = [user['email'] for user in TEST_USERS]


class Command(BaseCommand):
    help = 'Create 15 test users with premium access for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete existing test users before creating new ones',
        )

    def handle(self, *args, **options):
        if options['delete']:
            deleted_count, _ = User.objects.filter(email__in=TEST_USER_EMAILS).delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing test users'))

        created_count = 0
        updated_count = 0

        for user_data in TEST_USERS:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'username': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_active': True,
                    'subscription_plan': 'enterprise',
                    'is_premium_user': True,
                    'plan_start_date': timezone.now(),
                    'plan_end_date': timezone.now() + timedelta(days=365),  # 1 year access
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {user.email}'))
            else:
                # Update existing user to have premium access
                user.is_active = True
                user.subscription_plan = 'enterprise'
                user.is_premium_user = True
                user.plan_start_date = timezone.now()
                user.plan_end_date = timezone.now() + timedelta(days=365)
                user.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated: {user.email}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created: {created_count}, Updated: {updated_count}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'\nTest users can login via: POST /api/test-login/ with {{"email": "testuser1@volusignal.com"}}'
        ))
