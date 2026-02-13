import random
import string
import uuid
from django.db import models
from django.core.exceptions import ValidationError
import re


def format_phone_number(phone_number):
    """
    Format phone number to ensure it follows the correct format:
    - If starts with +, leave as is
    - Otherwise, ensure it starts with 0 and has exactly 10 digits
    """
    if not phone_number:
        return phone_number
    
    phone_str = str(phone_number).strip()
    
    # If starts with +, return as is
    if phone_str.startswith('+'):
        return phone_str
    
    # Remove any non-digit characters except + at the beginning
    phone_digits = re.sub(r'[^0-9]', '', phone_str)
    
    # If phone starts with country code like 255, convert to local format
    if phone_digits.startswith('255') and len(phone_digits) == 12:
        phone_digits = '0' + phone_digits[3:]
    
    # Ensure it starts with 0
    if not phone_digits.startswith('0'):
        phone_digits = '0' + phone_digits
    
    # Ensure it has exactly 10 digits
    if len(phone_digits) > 10:
        # Take the last 10 digits, ensuring the first is 0
        phone_digits = '0' + phone_digits[-9:]
    elif len(phone_digits) < 10:
        # Pad with zeros if too short (unlikely but safe)
        phone_digits = phone_digits.ljust(10, '0')
    
    return phone_digits


def validate_phone_number(phone_number):
    """
    Validate phone number format
    """
    if not phone_number:
        raise ValidationError("Phone number is required")
    
    phone_str = str(phone_number).strip()
    
    # If starts with +, basic validation
    if phone_str.startswith('+'):
        if not re.match(r'^\+[1-9]\d{1,14}$', phone_str):
            raise ValidationError("Invalid international phone number format")
        return
    
    # Local format should be exactly 10 digits starting with 0
    if not re.match(r'^0\d{9}$', phone_str):
        raise ValidationError("Phone number must start with 0 and have exactly 10 digits")


class PledgeRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile_number = models.CharField(max_length=15, unique=True, blank=False, help_text="Mobile number (Unique)")
    name = models.CharField(max_length=255, help_text="Person's name")
    pledge = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Pledged amount")
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount paid")
    remaining = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Remaining amount")
    card_capacity = models.IntegerField(default=0, help_text="Card capacity (0, 1, or 2 based on paid amount)")
    card_code = models.CharField(max_length=10, unique=True, blank=True, null=True, default='', help_text="Unique card identification code")
    invitation_image_url = models.URLField(blank=True, null=True, help_text="URL of the generated invitation image")
    normal_message_sent = models.BooleanField(default=False, help_text="Normal message sent status")
    whatsapp_sent = models.BooleanField(default=False, help_text="WhatsApp message sent status")
    attended_count = models.IntegerField(default=0, help_text="Number of people who attended")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pledge Record"
        verbose_name_plural = "Pledge Records"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.mobile_number})"

    def generate_unique_card_code(self):
        """Generate a unique 3-letter code excluding confusing characters"""
        # Exclude characters that look like numbers: O (looks like 0), I (looks like 1), S (looks like 5), Z (looks like 2)
        allowed_chars = 'ABCDEFGHJKLMNPQRTUVWXY'
        while True:
            code = ''.join(random.choices(allowed_chars, k=3))
            # Exclude current record when checking for uniqueness
            existing_query = PledgeRecord.objects.filter(card_code=code)
            if self.pk:
                existing_query = existing_query.exclude(pk=self.pk)
            if not existing_query.exists():
                return code

    def clean(self):
        """Validate the model fields"""
        super().clean()
        if self.mobile_number:
            validate_phone_number(self.mobile_number)
    
    def save(self, *args, **kwargs):
        # Format phone number
        if self.mobile_number:
            self.mobile_number = format_phone_number(self.mobile_number)
        
        # Generate card code only if it's completely empty/null
        if not self.card_code or self.card_code.strip() == '':
            self.card_code = self.generate_unique_card_code()
        
        # Automatically calculate remaining amount
        self.remaining = self.pledge - self.paid
        
        # Calculate card capacity based on paid amount (only if not manually set to special)
        # Preserve manually set special capacities (> 2)
        if self.card_capacity <= 2:
            if self.paid >= 100000:
                self.card_capacity = 2
            elif self.paid >= 50000:
                self.card_capacity = 1
            else:
                self.card_capacity = 0
        
        # Validate before saving
        self.full_clean()
        super().save(*args, **kwargs)


class UploadLog(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    total_records = models.IntegerField(default=0)
    new_records = models.IntegerField(default=0)
    updated_records = models.IntegerField(default=0)
    errors = models.TextField(blank=True, help_text="Any errors during upload")

    class Meta:
        verbose_name = "Upload Log"
        verbose_name_plural = "Upload Logs"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Upload {self.filename} at {self.uploaded_at}"


class SMSMessage(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    pledge_record = models.ForeignKey(PledgeRecord, on_delete=models.CASCADE, related_name='sms_messages')
    recipient_name = models.CharField(max_length=255, default='Unknown', help_text="Name of the SMS recipient")
    recipient_mobile = models.CharField(max_length=15, default='000000000', help_text="Mobile number of the SMS recipient")
    message_content = models.TextField(help_text="Content of the SMS message")
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message_id = models.CharField(max_length=255, blank=True, help_text="SMS provider message ID")
    error_message = models.TextField(blank=True, help_text="Error details if failed")
    message_type = models.CharField(max_length=50, default='wedding_invitation', help_text="Type of message")
    
    class Meta:
        verbose_name = "SMS Message"
        verbose_name_plural = "SMS Messages"
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"SMS to {self.pledge_record.name} at {self.sent_at} - {self.status}"
