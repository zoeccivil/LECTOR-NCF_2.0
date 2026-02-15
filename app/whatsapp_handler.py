"""
WhatsApp message handler using Twilio API
"""
from twilio.rest import Client
from typing import Optional
import httpx
from app.utils.logger import app_logger
from app.utils.config import settings


class WhatsAppHandler:
    """Handles WhatsApp messaging via Twilio"""
    
    def __init__(self):
        """Initialize Twilio client"""
        try:
            if settings.twilio_account_sid and settings.twilio_auth_token:
                self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
                
                # Asegurar que el número de origen tenga el prefijo whatsapp:
                raw_number = settings.twilio_whatsapp_number
                if raw_number and not raw_number.startswith('whatsapp:'):
                    self.from_number = f"whatsapp:{raw_number}"
                else:
                    self.from_number = raw_number
                    
                app_logger.info(f"Twilio WhatsApp client initialized. Sender: {self.from_number}")
            else:
                self.client = None
                self.from_number = None
                app_logger.warning("Twilio credentials not configured")
        except Exception as e:
            app_logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None
            self.from_number = None
    
    async def download_media(self, media_url: str, auth_token: Optional[str] = None) -> Optional[bytes]:
        """
        Download media from Twilio URL handling redirects (Fix for 307 error)
        
        Args:
            media_url: URL of the media file
            auth_token: Twilio auth token for authentication
            
        Returns:
            Media content as bytes or None if failed
        """
        try:
            app_logger.info(f"Downloading media from: {media_url}")
            
            # Use auth if provided, otherwise check settings
            auth = None
            if not auth_token and settings.twilio_auth_token:
                auth_token = settings.twilio_auth_token
                
            if settings.twilio_account_sid and auth_token:
                auth = (settings.twilio_account_sid, auth_token)
            
            # IMPORTANTE: follow_redirects=True es necesario para las URLs de medios de Twilio
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(media_url, auth=auth, timeout=30.0)
                
                if response.status_code == 200:
                    content = response.content
                    app_logger.info(f"Downloaded {len(content)} bytes successfully")
                    return content
                else:
                    app_logger.error(f"Failed to download media. Status: {response.status_code}")
                    return None
                
        except Exception as e:
            app_logger.error(f"Error downloading media: {e}")
            return None
    
    def send_message(self, to_number: str, message: str) -> bool:
        """
        Send WhatsApp message to a number
        
        Args:
            to_number: Recipient's WhatsApp number (format: whatsapp:+1234567890)
            message: Message text to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.client or not self.from_number:
            app_logger.error("Twilio client not initialized or sender number missing")
            return False
        
        try:
            # Ensure TO number has whatsapp: prefix
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            app_logger.info(f"Sending WhatsApp message to {to_number} from {self.from_number}")
            
            message_obj = self.client.messages.create(
                from_=self.from_number,
                to=to_number,
                body=message
            )
            
            app_logger.info(f"Message sent successfully. SID: {message_obj.sid}")
            return True
            
        except Exception as e:
            app_logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def send_confirmation(self, to_number: str) -> bool:
        """
        Send confirmation message that invoice is being processed
        """
        message = "✅ Factura recibida, procesando... ⏳"
        return self.send_message(to_number, message)
    
    def send_success(self, to_number: str, ncf: str, total: Optional[float] = None) -> bool:
        """
        Send success message with invoice details
        """
        if total is not None:
            message = f"🧾 *Lectura Exitosa*\n\n✅ **NCF:** {ncf}\n💰 **Total:** RD${total:,.2f}"
        else:
            message = f"🧾 *Lectura Exitosa*\n\n✅ **NCF:** {ncf}"
        
        return self.send_message(to_number, message)
    
    def send_error(self, to_number: str, error_detail: Optional[str] = None) -> bool:
        """
        Send error message
        """
        message = "❌ No se pudo leer la factura. Por favor, envía una foto más clara."
        if error_detail:
            message += f"\n\nDetalle: {error_detail}"
        
        return self.send_message(to_number, message)
    
    def send_partial_success(self, to_number: str, warnings: list) -> bool:
        """
        Send partial success message with warnings
        """
        message = "⚠️ *Factura procesada con alertas*\n\n"
        for warning in warnings:
            message += f"• {warning}\n"
        message += "\nRevisar manualmente."
        
        return self.send_message(to_number, message)


# Global WhatsApp handler instance
whatsapp_handler = WhatsAppHandler()