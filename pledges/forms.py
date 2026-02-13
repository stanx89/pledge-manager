from django import forms
from .models import PledgeRecord, format_phone_number, validate_phone_number


class FileUploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            'accept': '.csv,.xlsx,.xls'
        }),
        help_text="Upload a CSV or Excel file with columns: Name, Mobile Number, Pledge, Paid, Remaining"
    )


class PledgeRecordForm(forms.ModelForm):
    mobile_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter mobile number'
        })
    )
    
    class Meta:
        model = PledgeRecord
        fields = ['name', 'mobile_number', 'pledge', 'paid']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Enter full name'
            }),
            'pledge': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'step': '0.01',
                'placeholder': 'Enter pledge amount'
            }),
            'paid': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'step': '0.01',
                'placeholder': 'Enter paid amount'
            }),
        }
        
    def clean_mobile_number(self):
        mobile_number = self.cleaned_data.get('mobile_number')
        if not mobile_number or mobile_number.strip() == '':
            raise forms.ValidationError("Mobile number is required")
        
        # Format and validate phone number
        try:
            formatted_number = format_phone_number(mobile_number.strip())
            validate_phone_number(formatted_number)
            
            # Check for uniqueness (exclude current instance if editing)
            queryset = PledgeRecord.objects.filter(mobile_number=formatted_number)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError("A record with this mobile number already exists")
                
            return formatted_number
        except ValidationError as e:
            raise forms.ValidationError(f"Invalid phone number: {str(e)}")
        except Exception as e:
            raise forms.ValidationError(f"Error processing phone number: {str(e)}")


class SMSForwardForm(forms.Form):
    recipient_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter phone number to forward SMS to'
        }),
        help_text="Enter the phone number to forward the SMS message to"
    )
    recipient_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter recipient name (optional)'
        }),
        help_text="Optional: Name of the person receiving the SMS"
    )
    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'rows': 3,
            'placeholder': 'Optional: Custom message (leave blank to use default)'
        }),
        help_text="Leave blank to use the default message template"
    )
    
    def clean_recipient_number(self):
        recipient_number = self.cleaned_data.get('recipient_number')
        if recipient_number:
            # Format and validate phone number
            formatted_number = format_phone_number(recipient_number)
            validate_phone_number(formatted_number)
            return formatted_number
        return recipient_number