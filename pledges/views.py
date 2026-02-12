from decimal import Decimal
import threading
import time

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .forms import FileUploadForm, PledgeRecordForm, SMSForwardForm
from .models import PledgeRecord, UploadLog, format_phone_number
from .sms_utils import SMSService
from .whatsapp_utils import WhatsAppService


class PledgeListView(LoginRequiredMixin, ListView):
    """List view for pledge records with search functionality"""
    model = PledgeRecord
    template_name = 'pledges/list.html'
    context_object_name = 'pledges'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                name__icontains=search_query
            ) | queryset.filter(
                mobile_number__icontains=search_query
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context


@login_required
def upload_file(request):
    """Handle file upload for pledge records"""
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            
            try:
                # Read the file based on extension
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file)
                else:
                    messages.error(request, "Unsupported file format. Please upload CSV or Excel files.")
                    return redirect('upload_file')  # Redirect instead of render
                
                # Process the data
                result = process_upload_data(df, uploaded_file.name)
                messages.success(request, result['message'])
                return redirect('pledge_list')
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect('upload_file')  # Redirect instead of falling through
        else:
            # Form has validation errors, redirect to prevent resubmission
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('upload_file')
    else:
        form = FileUploadForm()
    
    return render(request, 'pledges/upload.html', {'form': form})


def process_upload_data(df, filename):
    """Process uploaded data and update/create records"""
    # Normalize column names (remove spaces, lowercase)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # Map possible column names
    column_mapping = {
        'name': ['name', 'full_name', 'person_name'],
        'mobile_number': ['mobile_number', 'mobile', 'phone', 'phone_number', 'contact'],
        'pledge': ['pledge', 'pledged', 'pledge_amount'],
        'paid': ['paid', 'amount_paid', 'paid_amount'],
        'remaining': ['remaining', 'balance', 'remaining_amount']
    }
    
    # Find actual column names
    actual_columns = {}
    for standard_name, possible_names in column_mapping.items():
        for possible_name in possible_names:
            if possible_name in df.columns:
                actual_columns[standard_name] = possible_name
                break
    
    # Check required columns
    required_columns = ['name', 'mobile_number', 'pledge', 'paid']
    missing_columns = [col for col in required_columns if col not in actual_columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    total_records = len(df)
    new_records = 0
    updated_records = 0
    errors = []
    
    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                mobile_number = str(row[actual_columns['mobile_number']]).strip()
                name = str(row[actual_columns['name']]).strip()
                pledge = Decimal(str(row[actual_columns['pledge']]).replace(',', ''))
                paid = Decimal(str(row[actual_columns['paid']]).replace(',', ''))
                
                # Calculate remaining if not provided
                if 'remaining' in actual_columns:
                    remaining = Decimal(str(row[actual_columns['remaining']]).replace(',', ''))
                else:
                    remaining = pledge - paid
                
                # Format phone number
                if mobile_number and mobile_number.lower() not in ['nan', 'none']:
                    mobile_number = format_phone_number(mobile_number)
                
                # Skip empty rows
                if not mobile_number or mobile_number.lower() in ['nan', 'none']:
                    continue
                
                # Check if record exists
                record, created = PledgeRecord.objects.get_or_create(
                    mobile_number=mobile_number,
                    defaults={
                        'name': name,
                        'pledge': pledge,
                        'paid': paid,
                        'remaining': remaining
                    }
                )
                
                if created:
                    new_records += 1
                else:
                    # Update existing record
                    record.name = name
                    record.pledge = pledge
                    record.paid = paid
                    record.remaining = remaining
                    record.save()
                    updated_records += 1
                    
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
        
        # Create upload log
        UploadLog.objects.create(
            filename=filename,
            total_records=total_records,
            new_records=new_records,
            updated_records=updated_records,
            errors='; '.join(errors) if errors else ''
        )
    
    message = f"Processed {total_records} records. New: {new_records}, Updated: {updated_records}"
    if errors:
        message += f". Errors: {len(errors)}"
    
    return {
        'total_records': total_records,
        'new_records': new_records,
        'updated_records': updated_records,
        'errors': errors,
        'message': message
    }


@login_required
def edit_record(request, record_id):
    """Edit a pledge record"""
    record = get_object_or_404(PledgeRecord, id=record_id)
    
    if request.method == 'POST':
        form = PledgeRecordForm(request.POST, instance=record)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Record for {record.name} updated successfully!")
                return redirect('pledge_list')
            except Exception as e:
                messages.error(request, f"Error saving record: {str(e)}")
        else:
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PledgeRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record
    }
    return render(request, 'pledges/edit_record.html', context)


@login_required
@require_POST
def delete_record(request, record_id):
    """Delete a pledge record"""
    record = get_object_or_404(PledgeRecord, id=record_id)
    record_name = record.name
    record.delete()
    messages.success(request, f"Record for {record_name} deleted successfully!")
    return redirect('pledge_list')


@login_required
def upload_logs(request):
    """Display upload logs"""
    logs = UploadLog.objects.all().order_by('-uploaded_at')
    return render(request, 'pledges/upload_logs.html', {'logs': logs})


@login_required
def view_pledge_detail(request, record_id):
    """
    View detailed information about a pledge record including SMS history
    """
    record = get_object_or_404(PledgeRecord, id=record_id)
    sms_messages = record.sms_messages.all().order_by('-sent_at')
    
    context = {
        'record': record,
        'sms_messages': sms_messages,
        'total_messages_sent': sms_messages.filter(status='sent').count(),
        'total_messages_failed': sms_messages.filter(status='failed').count(),
    }
    return render(request, 'pledges/pledge_detail.html', context)


@login_required
@require_POST
def send_sms(request, record_id):
    """Send SMS to a specific pledge record"""
    record = get_object_or_404(PledgeRecord, id=record_id)
    
    try:
        sms_service = SMSService()
        custom_message = request.POST.get('message')
        result = sms_service.send_pledge_sms(record, custom_message)
        
        if result['success']:
            record.normal_message_sent = True
            record.save()
            messages.success(request, f"SMS sent successfully to {record.name}")
        else:
            messages.error(request, f"Failed to send SMS to {record.name}: {result['error']}")
            
    except Exception as e:
        messages.error(request, f"Error sending SMS: {str(e)}")
    
    return redirect('pledge_list')


@login_required
@require_POST
def send_bulk_sms(request):
    """Send SMS to multiple records"""
    record_ids = request.POST.getlist('selected_records')
    
    if not record_ids:
        messages.error(request, "No records selected for SMS")
        return redirect('pledge_list')
    
    try:
        records = PledgeRecord.objects.filter(id__in=record_ids)
        custom_message = request.POST.get('message')
        
        sms_service = SMSService()
        results = sms_service.send_bulk_sms(records, custom_message)
        
        successful = sum(1 for result in results if result['success'])
        failed = len(results) - successful
        
        # Update status for successful sends
        if successful > 0:
            successful_numbers = [
                result['mobile_number'] for result in results 
                if result['success']
            ]
            PledgeRecord.objects.filter(
                mobile_number__in=successful_numbers
            ).update(normal_message_sent=True)
            
            messages.success(request, f"SMS sent successfully to {successful} record(s)")
            
        if failed > 0:
            messages.warning(request, f"Failed to send SMS to {failed} record(s)")
            
    except Exception as e:
        messages.error(request, f"Error sending bulk SMS: {str(e)}")
    
    return redirect('pledge_list')


@login_required
def sms_form(request):
    """Display SMS sending form"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'single':
            record_id = request.POST.get('record_id')
            return send_sms(request, record_id)
        elif action == 'bulk':
            return send_bulk_sms(request)
    
    context = {
        'records': PledgeRecord.objects.all(),
        'default_message': settings.SMS_DEFAULT_MESSAGE
    }
    return render(request, 'pledges/sms_form.html', context)


def forward_sms(request, record_id):
    """Forward SMS to a different number without updating the original record"""
    record = get_object_or_404(PledgeRecord, id=record_id)
    
    if request.method == 'POST':
        form = SMSForwardForm(request.POST)
        if form.is_valid():
            try:
                sms_service = SMSService()
                
                # Get form data
                recipient_number = form.cleaned_data['recipient_number']
                recipient_name = form.cleaned_data.get('recipient_name', 'Guest')
                custom_message = form.cleaned_data.get('custom_message')
                
                # Send SMS to the new number
                result = sms_service.send_forwarded_sms(
                    original_record=record,
                    recipient_number=recipient_number,
                    recipient_name=recipient_name,
                    custom_message=custom_message
                )
                
                if result['success']:
                    messages.success(
                        request, 
                        f"SMS forwarded successfully to {recipient_number} ({recipient_name or 'Guest'})"
                    )
                    return redirect('edit_record', record_id=record.id)
                else:
                    messages.error(request, f"Failed to forward SMS: {result['error']}")
                    
            except Exception as e:
                messages.error(request, f"Error forwarding SMS: {str(e)}")
    else:
        form = SMSForwardForm()
    
    context = {
        'form': form,
        'record': record
    }
    return render(request, 'pledges/forward_sms.html', context)


@require_POST
@login_required
def forward_sms_modal(request, record_id):
    """Simple modal-based SMS forwarding that only takes phone number and sends default message"""
    record = get_object_or_404(PledgeRecord, id=record_id)
    
    try:
        recipient_number = request.POST.get('recipient_number', '').strip()
        
        if not recipient_number:
            messages.error(request, "Phone number is required")
            return redirect(request.META.get('HTTP_REFERER', 'pledge_list'))
        
        sms_service = SMSService()
        
        # Send SMS using default message
        result = sms_service.send_forwarded_sms(
            original_record=record,
            recipient_number=recipient_number,
            recipient_name='Forwarded Guest',
            custom_message=None  # Use default message
        )
        
        if result['success']:
            messages.success(
                request, 
                f"SMS forwarded successfully to {recipient_number}"
            )
        else:
            messages.error(request, f"Failed to forward SMS: {result['error']}")
            
    except Exception as e:
        messages.error(request, f"Error forwarding SMS: {str(e)}")
    
    # Redirect back to the referring page
    return redirect(request.META.get('HTTP_REFERER', 'pledge_list'))


def send_background_sms_worker(unsent_records):
    """Background worker function to send SMS to unsent records"""
    sms_service = SMSService()
    successful = 0
    failed = 0
    
    for record in unsent_records:
        try:
            result = sms_service.send_pledge_sms(record)
            if result['success']:
                record.normal_message_sent = True
                record.save()
                successful += 1
                # Small delay to avoid rate limiting
                time.sleep(1)
            else:
                failed += 1
        except Exception as e:
            print(f"Error sending SMS to {record.name} ({record.mobile_number}): {str(e)}")
            failed += 1
    
    print(f"Background SMS batch completed: {successful} successful, {failed} failed")

@login_required
@require_POST
def send_background_sms_all(request):
    """Send SMS to all records that haven't received normal messages yet - in background"""
    try:
        # Get all records that haven't received normal SMS
        unsent_records = PledgeRecord.objects.filter(normal_message_sent=False)
        total_count = unsent_records.count()
        
        if total_count == 0:
            messages.info(request, "No unsent messages found. All records have already received SMS.")
            return redirect('pledge_list')
        
        # Start background thread to send SMS
        thread = threading.Thread(
            target=send_background_sms_worker, 
            args=(list(unsent_records),)
        )
        thread.daemon = True
        thread.start()
        
        messages.success(
            request, 
            f"Started sending SMS to {total_count} records in the background. "
            f"This will take approximately {total_count} minutes to complete."
        )
        
    except Exception as e:
        messages.error(request, f"Error starting background SMS send: {str(e)}")
    
    return redirect('pledge_list')


# WhatsApp Functions
@login_required
@require_POST
def send_whatsapp(request, record_id):
    """Send WhatsApp invitation to a specific pledge record"""
    record = get_object_or_404(PledgeRecord, id=record_id)
    
    try:
        whatsapp_service = WhatsAppService()
        result = whatsapp_service.send_invitation_whatsapp(record)
        
        if result['success']:
            messages.success(request, f"WhatsApp invitation sent successfully to {record.name}")
        else:
            messages.error(request, f"Failed to send WhatsApp to {record.name}: {result['error']}")
            
    except Exception as e:
        messages.error(request, f"Error sending WhatsApp: {str(e)}")
    
    return redirect('pledge_list')


@login_required
@require_POST
def send_bulk_whatsapp(request):
    """Send WhatsApp invitations to multiple records"""
    record_ids = request.POST.getlist('selected_records')
    
    if not record_ids:
        messages.error(request, "No records selected for WhatsApp")
        return redirect('pledge_list')
    
    try:
        records = PledgeRecord.objects.filter(id__in=record_ids)
        whatsapp_service = WhatsAppService()
        successful = 0
        failed = 0
        
        for record in records:
            if not record.whatsapp_sent:
                result = whatsapp_service.send_invitation_whatsapp(record)
                if result['success']:
                    successful += 1
                else:
                    failed += 1
                    
        messages.success(request, f"WhatsApp invitations: {successful} sent, {failed} failed")
        
    except Exception as e:
        messages.error(request, f"Error sending bulk WhatsApp: {str(e)}")
    
    return redirect('pledge_list')


@login_required
@login_required
@require_POST 
def send_background_whatsapp_all(request):
    """Send WhatsApp invitations to all unsent records in the background"""
    try:
        # Get all records that haven't received WhatsApp yet
        unsent_records = PledgeRecord.objects.filter(whatsapp_sent=False)
        total_count = unsent_records.count()
        
        if total_count == 0:
            messages.info(request, "No unsent WhatsApp invitations found. All records have already received WhatsApp.")
            return redirect('pledge_list')
        
        # Start background thread to send WhatsApp
        thread = threading.Thread(
            target=send_background_whatsapp_worker, 
            args=(list(unsent_records),)
        )
        thread.daemon = True
        thread.start()
        
        messages.success(
            request, 
            f"Started sending WhatsApp invitations to {total_count} records in the background. "
            f"This will take some time to complete."
        )
        
    except Exception as e:
        messages.error(request, f"Error starting background WhatsApp send: {str(e)}")
    
    return redirect('pledge_list')


def send_background_whatsapp_worker(records):
    """Background worker function to send WhatsApp invitations"""
    whatsapp_service = WhatsAppService()
    successful_count = 0
    failed_count = 0
    
    for record in records:
        try:
            result = whatsapp_service.send_invitation_whatsapp(record)
            if result['success']:
                successful_count += 1
                logger.info(f"WhatsApp invitation sent to {record.name}")
            else:
                failed_count += 1
                logger.error(f"Failed to send WhatsApp to {record.name}: {result['error']}")
                
            # Add small delay to avoid rate limiting
            time.sleep(2)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Error sending WhatsApp to {record.name}: {str(e)}")
    
    logger.info(f"Background WhatsApp batch completed: {successful_count} successful, {failed_count} failed")
