from django.contrib import admin
from .models import PledgeRecord, UploadLog, SMSMessage


@admin.register(PledgeRecord)
class PledgeRecordAdmin(admin.ModelAdmin):
    list_display = ['mobile_number', 'name', 'pledge', 'paid', 'remaining', 'card_capacity', 'card_code',
                   'normal_message_sent', 'whatsapp_sent', 'updated_at']
    list_filter = ['card_capacity', 'normal_message_sent', 'whatsapp_sent', 'created_at', 'updated_at']
    search_fields = ['name', 'mobile_number', 'card_code']
    list_editable = ['name', 'pledge', 'paid', 'normal_message_sent', 'whatsapp_sent']
    readonly_fields = ['id', 'remaining', 'card_capacity', 'card_code', 'created_at', 'updated_at']
    ordering = ['-updated_at']


@admin.register(UploadLog)
class UploadLogAdmin(admin.ModelAdmin):
    list_display = ['filename', 'uploaded_at', 'total_records', 'new_records', 'updated_records']
    list_filter = ['uploaded_at']
    search_fields = ['filename']
    readonly_fields = ['uploaded_at', 'filename', 'total_records', 'new_records', 'updated_records', 'errors']
    ordering = ['-uploaded_at']


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ['recipient_name', 'recipient_mobile', 'message_type', 'status', 'sent_at', 'message_id']
    list_filter = ['status', 'message_type', 'sent_at']
    search_fields = ['recipient_name', 'recipient_mobile', 'pledge_record__name', 'pledge_record__mobile_number', 'message_id']
    readonly_fields = ['sent_at', 'message_id']
    ordering = ['-sent_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pledge_record')
