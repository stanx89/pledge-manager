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
        print("Checking font path:", p)
        if p and os.path.exists(p):
            print("Using font:", repr(p))
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def add_dear_name(img, invitee_name):
    """Draw 'Dear Name' on the image"""
    draw = ImageDraw.Draw(img)

    # Try to load elegant font from project fonts directory
    font_paths = [
        str(Path(settings.BASE_DIR) / 'static' / 'fonts' / 'GreatVibes-Regular.ttf'),
    ]

    font = load_font(font_paths, 65)

    text = f"Habari"

    # Position (tuned for your card layout)
    x = 500
    y = 160

    # Wedding-style maroon color
    text_color = (120, 80, 40)

    # Draw directly (NO background)
    draw.text((x, y), text, font=font, fill=text_color)

    name = f"{invitee_name}"
    text_color = (120, 80, 40)

    # Position (tuned for your card layout)
    x = 500
    y = 220

    draw.text((x, y), name, font=font, fill=text_color)

    return img


def add_qr(img, qr_data, cardType):
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

    img.paste(qr_img, (x+70, y))

    font_paths = [
        str(Path(settings.BASE_DIR) / 'static' / 'fonts' / 'Roboto-Bold.ttf'),
    ]

    font = load_font(font_paths, 30)

    text = f"{cardType}"

    draw = ImageDraw.Draw(img)

    y = y+190
    x = x+70

    text_color = (120, 80, 40)

    #Card type
    draw.text((x, y), text.upper(), font=font, fill=text_color)

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
        """Generate invitation image using the create_image script - always regenerate to replace existing"""
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
            
            # If image already exists, log that we're replacing it
            if image_path.exists():
                logger.info(f"Replacing existing invitation image for {pledge_record.name}: {image_path}")
            
            # Generate image using the create_image functions
            base_image = Image.open(template_path).convert("RGB")
            
            # Add name to image
            image_with_name = add_dear_name(base_image, pledge_record.name)
            
            # Add QR code with card information
            capacity_text = "double" if pledge_record.card_capacity == 2 else "single"
            qr_data = f"Card: {pledge_record.card_code} | Capacity: {pledge_record.card_capacity} {capacity_text}"
            final_image = add_qr(image_with_name, qr_data, capacity_text)
            
            # Save the image (overwriting if it exists)
            final_image.save(str(image_path), quality=95)
            
            # Generate full URL using configurable BASE_URL
            base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
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
        
        logger.info(f"Sending WhatsApp message to {phone_number}")
        logger.debug(f"WhatsApp API payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(self.base_url, headers=headers, json=payload)
        
        # Log the raw response
        logger.info(f"WhatsApp API response status: {response.status_code}")
        logger.debug(f"WhatsApp API raw response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', '')
            
            # Log successful response details
            logger.info(f"WhatsApp message sent successfully to {phone_number}. Message ID: {message_id}")
            logger.debug(f"WhatsApp success response: {json.dumps(result, indent=2)}")
            
            return {
                'success': True,
                'message_id': message_id,
                'response': result
            }
        else:
            # Log error response details
            error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"WhatsApp API error for {phone_number}: {error_msg}")
            
            try:
                error_details = response.json()
                logger.error(f"WhatsApp error details: {json.dumps(error_details, indent=2)}")
            except:
                logger.error(f"Could not parse error response as JSON: {response.text}")
                
            return {
                'success': False,
                'error': error_msg,
                'response': response.text
            }
            
    def send_invitation_whatsapp(self, pledge_record):
        """Send WhatsApp invitation to a pledge record"""
        logger.info(f"Starting WhatsApp invitation process for {pledge_record.name} (ID: {pledge_record.id})")
        
        try:
            # Format phone number for WhatsApp
            whatsapp_phone = self.format_phone_for_whatsapp(pledge_record.mobile_number)
            if not whatsapp_phone:
                error_msg = f"Invalid phone number format: {pledge_record.mobile_number}"
                logger.error(f"Phone format error for {pledge_record.name}: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
            # Generate or get existing image URL
            logger.info(f"Generating invitation image for {pledge_record.name}")
            image_url = self.generate_invitation_image(pledge_record)
            if not image_url:
                error_msg = "Failed to generate invitation image"
                logger.error(f"Image generation failed for {pledge_record.name}: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
            # Image URL is now already a full URL from generate_invitation_image
            full_image_url = image_url
            logger.info(f"Using image URL for {pledge_record.name}: {full_image_url}")
                
            # Create personalized message
            message_text = f"Habari {pledge_record.name}, unakaribishwa rasmi kwenye sherehe ya harusi.!"
            logger.info(f"Sending WhatsApp to {whatsapp_phone} with message: {message_text}")
            
            # Send WhatsApp message
            result = self.send_whatsapp_template(whatsapp_phone, full_image_url, message_text)
            
            # Log the final result
            if result['success']:
                # Update the record to mark WhatsApp as sent
                pledge_record.whatsapp_sent = True
                pledge_record.save()
                
                logger.info(f"✓ WhatsApp invitation completed successfully for {pledge_record.name} ({whatsapp_phone}). Message ID: {result.get('message_id', 'N/A')}")
            else:
                logger.error(f"✗ WhatsApp invitation failed for {pledge_record.name} ({whatsapp_phone}): {result.get('error', 'Unknown error')}")
                
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error sending WhatsApp to {pledge_record.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }