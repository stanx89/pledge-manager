from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create login user for the application (Note: This user is now auto-created via migration)'

    def handle(self, *args, **options):
        username = 'mubote'
        password = 'kayombo'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f'User {username} already exists. Use this command to reset the password if needed.'
                )
            )
            # Update existing user password
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Password updated for user: {username}')
            )
        else:
            # Create new user
            user = User.objects.create_user(
                username=username,
                password=password,
                is_staff=False,
                is_superuser=False
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created user: {username} with password: {password}'
                )
            )