from django.urls import path
from . import views

urlpatterns = [
    path('', views.PledgeListView.as_view(), name='pledge_list'),
    path('upload/', views.upload_file, name='upload_file'),
    path('add/', views.add_record, name='add_record'),
    path('view/<uuid:record_id>/', views.view_pledge_detail, name='view_pledge_detail'),
    path('edit/<uuid:record_id>/', views.edit_record, name='edit_record'),
    path('delete/<uuid:record_id>/', views.delete_record, name='delete_record'),
    path('logs/', views.upload_logs, name='upload_logs'),
    path('send-sms/<uuid:record_id>/', views.send_sms, name='send_sms'),
    path('send-bulk-sms/', views.send_bulk_sms, name='send_bulk_sms'),
    path('sms-form/', views.sms_form, name='sms_form'),
    path('forward-sms/<uuid:record_id>/', views.forward_sms, name='forward_sms'),
    path('forward-sms-modal/<uuid:record_id>/', views.forward_sms_modal, name='forward_sms_modal'),
    path('send-background-sms-all/', views.send_background_sms_all, name='send_background_sms_all'),
    
    # WhatsApp URLs
    path('send-whatsapp/<uuid:record_id>/', views.send_whatsapp, name='send_whatsapp'),
    path('send-bulk-whatsapp/', views.send_bulk_whatsapp, name='send_bulk_whatsapp'),
    path('send-background-whatsapp-all/', views.send_background_whatsapp_all, name='send_background_whatsapp_all'),
]