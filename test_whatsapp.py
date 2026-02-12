#!/usr/bin/env python3
"""
Test WhatsApp functionality
"""
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pledge_manager.settings')
django.setup()

# Now import Django models and services
from pledges.whatsapp_utils import WhatsAppService
from pledges.models import PledgeRecord


def test_image_generation():
    """Test image generation functionality"""
    print("Testing WhatsApp image generation...")
    
    # Create mock record
    class MockRecord:
        def __init__(self):
            self.id = 'test-123'
            self.name = 'Test User'
            self.mobile_number = '0712345678'
            self.card_code = 'T001'
            self.card_capacity = 2
            self.invitation_image_url = 'https://media.istockphoto.com/id/2228011085/photo/woman-chopping-carrots-on-a-table-full-of-healthy-autumnal-fruits-and-vegetables-fresh.jpg?s=1024x1024&w=is&k=20&c=3AfQJUS4XmLiI3gatDu_7jG38ZelByrQItJTSg6_FvY='
        
        def save(self):
            print(f"Mock save called - invitation_image_url would be: {self.invitation_image_url}")
    
    try:
        # Initialize WhatsApp service
        whatsapp_service = WhatsAppService()
        mock_record = MockRecord()
        
        print(f"Generating image for: {mock_record.name}")
        
        # Test image generation
        image_url = whatsapp_service.generate_invitation_image(mock_record)
        
        if image_url:
            print(f"✓ Image URL generated: {image_url}")
            
            # Check if file exists
            filename = image_url.split('/')[-1]
            filepath = os.path.join(settings.BASE_DIR, 'static', 'invitations', filename)
            
            if os.path.exists(filepath):
                print(f"✓ Image file created: {filepath}")
                file_size = os.path.getsize(filepath)
                print(f"✓ File size: {file_size} bytes")
                return True
            else:
                print(f"✗ Image file not found: {filepath}")
                return False
        else:
            print("✗ No image URL returned")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_phone_formatting():
    """Test phone number formatting for WhatsApp"""
    print("\nTesting phone number formatting...")
    
    whatsapp_service = WhatsAppService()
    
    test_numbers = [
        '0712345678',
        '+255712345678', 
        '255712345678',
        '712345678'
    ]
    
    for number in test_numbers:
        formatted = whatsapp_service.format_phone_for_whatsapp(number)
        print(f"  {number} → {formatted}")


if __name__ == "__main__":
    print("WhatsApp Functionality Test")
    print("=" * 40)
    
    # Test image generation
    image_test_passed = test_image_generation()
    
    # Test phone formatting  
    test_phone_formatting()
    
    print("\n" + "=" * 40)
    if image_test_passed:
        print("✓ All tests passed! WhatsApp functionality is ready.")
    else:
        print("✗ Some tests failed. Check the errors above.")