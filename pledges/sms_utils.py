from django.conf import settings
from notify_africa import NotifyAfrica
import logging

logger = logging.getLogger(__name__)


class SMSService:
    def __init__(self):
        self.client = NotifyAfrica(apiToken=settings.NOTIFY_AFRICA_API_TOKEN)
        self.sender_id = settings.NOTIFY_AFRICA_SENDER_ID
    
    def send_pledge_sms(self, pledge_record, custom_message=None):
        """
        Send SMS to a pledge record holder
        """
        from .models import SMSMessage  # Import here to avoid circular imports
        
        # Format card capacity for display
        if pledge_record.card_capacity == 2:
            capacity_display = "DOUBLE"
        elif pledge_record.card_capacity == 1:
            capacity_display = "SINGLE"
        else:
            capacity_display = str(pledge_record.card_capacity)
        
        # Format the message
        if custom_message:
            message = custom_message.format(
                name=pledge_record.name,
                pledge=pledge_record.pledge,
                paid=pledge_record.paid,
                remaining=pledge_record.remaining,
                mobile_number=pledge_record.mobile_number,
                card_code=pledge_record.card_code,
                card_capacity=capacity_display
            )
        else:
            message = settings.SMS_DEFAULT_MESSAGE.format(
                name=pledge_record.name,
                pledge=pledge_record.pledge,
                paid=pledge_record.paid,
                remaining=pledge_record.remaining,
                card_code=pledge_record.card_code,
                card_capacity=capacity_display
            )
        
        # Create SMS record
        sms_record = SMSMessage.objects.create(
            pledge_record=pledge_record,
            recipient_name=pledge_record.name,
            recipient_mobile=pledge_record.mobile_number,
            message_content=message,
            message_type='wedding_invitation' if not custom_message else 'custom',
            status='pending'
        )
        
        try:
            # Send SMS
            response = self.client.send_single_message(
                phoneNumber=pledge_record.mobile_number,
                message=message,
                senderId=self.sender_id,
            )
            
            # Update SMS record with success
            sms_record.status = 'sent'
            sms_record.message_id = response.messageId
            sms_record.save()
            
            logger.info(f"SMS sent to {pledge_record.mobile_number}. Message ID: {response.messageId}, Status: {response.status}")
            
            return {
                'success': True,
                'message_id': response.messageId,
                'status': response.status,
                'message': message,
                'sms_record_id': sms_record.id
            }
            
        except Exception as e:
            # Update SMS record with failure
            sms_record.status = 'failed'
            sms_record.error_message = str(e)
            sms_record.save()
            
            logger.error(f"Failed to send SMS to {pledge_record.mobile_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sms_record_id': sms_record.id
            }
    
    def send_bulk_sms(self, pledge_records, custom_message=None):
        """
        Send SMS to multiple pledge records
        """
        results = []
        for record in pledge_records:
            result = self.send_pledge_sms(record, custom_message)
            result['mobile_number'] = record.mobile_number
            result['name'] = record.name
            results.append(result)
        
        return results
    
    def send_forwarded_sms(self, original_record, recipient_number, recipient_name=None, custom_message=None):
        """
        Forward SMS to a different number without updating the original record
        """
        from .models import SMSMessage  # Import here to avoid circular imports
        
        # Format card capacity for display
        if original_record.card_capacity == 2:
            capacity_display = "Double"
        elif original_record.card_capacity == 1:
            capacity_display = "Single"
        else:
            capacity_display = str(original_record.card_capacity)
        
        # Format the message
        if custom_message:
            message = custom_message.format(
                name=original_record.name,
                pledge=original_record.pledge,
                paid=original_record.paid,
                remaining=original_record.remaining,
                mobile_number=original_record.mobile_number,
                card_code=original_record.card_code,
                card_capacity=capacity_display
            )
        else:
            # Use SMS_DEFAULT_MESSAGE template from settings
            message = settings.SMS_DEFAULT_MESSAGE.format(
                name=original_record.name,
                pledge=original_record.pledge,
                paid=original_record.paid,
                remaining=original_record.remaining,
                card_code=original_record.card_code,
                card_capacity=capacity_display
            )
        
        # Create SMS record linked to original pledge but with different recipient
        sms_record = SMSMessage.objects.create(
            pledge_record=original_record,
            recipient_name=recipient_name or 'Forwarded Guest',
            recipient_mobile=recipient_number,
            message_content=message,
            message_type='forwarded',
            status='pending'
        )
        
        try:
            # Send SMS to forwarded number
            response = self.client.send_single_message(
                phoneNumber=recipient_number,
                message=message,
                senderId=self.sender_id,
            )
            
            # Update SMS record with success
            sms_record.status = 'sent'
            sms_record.message_id = response.messageId
            sms_record.save()
            
            logger.info(f"SMS forwarded to {recipient_number} for {original_record.name}. Message ID: {response.messageId}, Status: {response.status}")
            
            return {
                'success': True,
                'message_id': response.messageId,
                'status': response.status,
                'message': message,
                'sms_record_id': sms_record.id,
                'recipient_number': recipient_number,
                'recipient_name': recipient_name
            }
            
        except Exception as e:
            # Update SMS record with failure
            sms_record.status = 'failed'
            sms_record.error_message = str(e)
            sms_record.save()
            
            logger.error(f"Failed to forward SMS to {recipient_number} for {original_record.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sms_record_id': sms_record.id,
                'recipient_number': recipient_number,
                'recipient_name': recipient_name
            }