from django.core.management.base import BaseCommand
from pledges.models import PledgeRecord, format_phone_number


class Command(BaseCommand):
    help = 'Update existing phone numbers to follow the standard format (0 + 10 digits)'

    def handle(self, *args, **options):
        self.stdout.write('Starting phone number format update...')
        
        records = PledgeRecord.objects.all()
        updated_count = 0
        error_count = 0
        
        for record in records:
            original_number = record.mobile_number
            try:
                formatted_number = format_phone_number(original_number)
                if formatted_number != original_number:
                    record.mobile_number = formatted_number
                    record.save()
                    updated_count += 1
                    self.stdout.write(
                        f'Updated: {original_number} -> {formatted_number} ({record.name})'
                    )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error updating {original_number} ({record.name}): {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Phone number update complete. Updated: {updated_count}, Errors: {error_count}'
            )
        )