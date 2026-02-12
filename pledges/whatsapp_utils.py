import os
import json
import logging
import requests
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from django.conf import settings
from django.urls import reverse
from .models import PledgeRecord

logger = logging.getLogger(__name__)


def safe_filename(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "invitee"


def load_font(paths, size):
    for p in paths:
        if p and os.path.exists(p):
            print("Using font:", p)
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def add_dear_name(img, invitee_name):
    """Draw 'Dear Name' on the image"""
    draw = ImageDraw.Draw(img)

    # Try to load elegant font
    font_paths = [
        "/Users/stan/Library/Fonts/DejaVu Serif Italic.ttf",
    ]

    font = load_font(font_paths, 30)

    text = f"Dear {invitee_name}"

    # Position (tuned for your card layout)
    x = 250
    y = 170

    # Wedding-style maroon color
    text_color = (95, 28, 28)

    # Draw directly (NO background)
    draw.text((x, y), text, font=font, fill=text_color)

    return img


def add_qr(img, qr_data):
    """Add QR code to bottom center of image"""
    w, h = img.size

    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=2
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    qr_img = qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")

    qr_size = int(min(w, h) * 0.18)
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

    # Bottom center
    x = (w - qr_size) // 2
    y = h - qr_size - int(h * 0.06)

    img.paste(qr_img, (x, y))

    return img


class WhatsAppService:
    """Service for sending WhatsApp messages using Meta Business API"""
    
    def __init__(self):
        self.api_token = getattr(settings, 'WHATSAPP_API_TOKEN', '')
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        self.template_name = getattr(settings, 'WHATSAPP_TEMPLATE_NAME', 'kadi_mualiko')
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        
    def format_phone_for_whatsapp(self, phone_number):
        """Format phone number for WhatsApp API (255xxxxxxxxx format)"""
        if not phone_number:
            return None
            
        phone_str = str(phone_number).strip()
        
        # If already starts with +, remove + and return
        if phone_str.startswith('+'):
            return phone_str[1:]
            
        # If starts with 0, replace with 255
        if phone_str.startswith('0') and len(phone_str) == 10:
            return '255' + phone_str[1:]
            
        # If already starts with 255, return as is
        if phone_str.startswith('255') and len(phone_str) == 12:
            return phone_str
            
        return None
        
    def generate_invitation_image(self, pledge_record):
        """Generate invitation image using the create_image script"""
        if pledge_record.invitation_image_url:
            # Image already exists, return the URL
            return pledge_record.invitation_image_url
            
        try:
            # Path to template image
            template_path = Path(settings.BASE_DIR) / 'static' / 'invitations' / 'template.png'
            
            if not template_path.exists():
                logger.error(f"Template image not found: {template_path}")
                return None
                
            # Create invitations directory if it doesn't exist
            invitations_dir = Path(settings.BASE_DIR) / 'static' / 'invitations'
            invitations_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            safe_name = safe_filename(pledge_record.name)
            image_filename = f"invite_{safe_name}_{pledge_record.card_code}.png"
            image_path = invitations_dir / image_filename
            
            # Generate image using the create_image functions
            base_image = Image.open(template_path).convert("RGB")
            
            # Add name to image
            image_with_name = add_dear_name(base_image, pledge_record.name)
            
            # Add QR code with card information
            qr_data = f"Card: {pledge_record.card_code} | Capacity: {pledge_record.card_capacity}"
            final_image = add_qr(image_with_name, qr_data)
            
            # Save the image
            final_image.save(str(image_path), quality=95)
            
            # Generate full URL for Django URLField validation
            # For development, use localhost. In production, this should be your domain
            base_url = "http://127.0.0.1:8000"  # Update this for production
            image_url = f"{base_url}{settings.STATIC_URL}invitations/{image_filename}"
            
            # Update the pledge record with the URL
            pledge_record.invitation_image_url = image_url
            pledge_record.save()
            
            logger.info(f"Generated invitation image for {pledge_record.name}: {image_url}")
            return image_url
            
        except Exception as e:
            logger.error(f"Error generating invitation image for {pledge_record.name}: {str(e)}")
            return None
            
    def send_whatsapp_template(self, phone_number, image_url, message_text="Your wedding invitation"):
        """Send WhatsApp template message"""
        if not self.api_token or not self.phone_number_id:
            raise Exception("WhatsApp API credentials not configured")
            
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": self.template_name,
                "language": {
                    "code": "en"
                },
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "image",
                                "image": {
                                    "link": image_url
                                }
                            }
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": message_text,
                                "parameter_name": "message"
                            }
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(self.base_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('messages', [{}])[0].get('id', ''),
                'response': result
            }
        else:
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text}",
                'response': response.text
            }
            
    def send_invitation_whatsapp(self, pledge_record):
        """Send WhatsApp invitation to a pledge record"""
        try:
            # Format phone number for WhatsApp
            whatsapp_phone = self.format_phone_for_whatsapp(pledge_record.mobile_number)
            if not whatsapp_phone:
                return {
                    'success': False,
                    'error': f"Invalid phone number format: {pledge_record.mobile_number}"
                }
                
            # Generate or get existing image URL
            image_url = self.generate_invitation_image(pledge_record)
            if not image_url:
                return {
                    'success': False,
                    'error': "Failed to generate invitation image"
                }
                
            # Image URL is now already a full URL from generate_invitation_image
            full_image_url = image_url
                
            # Create personalized message
            message_text = f"Dear {pledge_record.name}, you are cordially invited to the wedding celebration!"
            
            # Send WhatsApp message
            result = self.send_whatsapp_template(whatsapp_phone, full_image_url, message_text)
            
            if result['success']:
                # Update the record to mark WhatsApp as sent
                pledge_record.whatsapp_sent = True
                pledge_record.save()
                
                logger.info(f"WhatsApp invitation sent successfully to {pledge_record.name} ({whatsapp_phone})")
                
            return result
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp to {pledge_record.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }