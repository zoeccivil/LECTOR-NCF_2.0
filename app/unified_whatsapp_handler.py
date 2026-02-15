"""
Unified WhatsApp Handler - Supports both Twilio and Green-API
"""
from loguru import logger as app_logger
from app.whatsapp_handler import whatsapp_handler
from app.greenapi_handler import greenapi_handler
from typing import Optional
import os


class UnifiedWhatsAppHandler:
    def __init__(self):
        self.mode = os.environ.get("WHATSAPP_MODE", "dual").lower()  # dual, twilio, greenapi
        app_logger.info(f"🔧 WhatsApp mode: {self.mode}")
    
    async def send_message(self, to: str, message: str):
        """Send message using available provider(s)"""
        success = False
        
        if self.mode in ["dual", "greenapi"]:
            # Try Green-API first
            if greenapi_handler.enabled:
                result = await greenapi_handler.send_message(to, message)
                if result:
                    app_logger.info("✅ Message sent via Green-API")
                    success = True
                    if self.mode == "greenapi":
                        return result
        
        if self.mode in ["dual", "twilio"] and not success:
            # Try Twilio as fallback or primary
            try:
                result = whatsapp_handler.send_message(to, message)
                if result:
                    app_logger.info("✅ Message sent via Twilio")
                    success = True
            except Exception as e:
                app_logger.error(f"❌ Twilio failed: {e}")
        
        if not success:
            app_logger.error("❌ All providers failed")
        
        return success
    
    async def send_confirmation(self, to: str):
        """Send confirmation message"""
        return await self.send_message(to, "✅ Factura recibida, procesando... ⏳")
    
    async def send_success(self, to: str, ncf: str, total: float):
        """Send success message"""
        message = f"""📄 *Lectura Exitosa*

✅ *NCF:* {ncf}
💰 *Total:* RD${total:,.2f}"""
        return await self.send_message(to, message)
    
    async def send_error(self, to: str, error_msg: str = None):
        """Send error message"""
        if error_msg:
            message = f"❌ Error: {error_msg}"
        else:
            message = "❌ No se pudo procesar la factura. Intenta con otra imagen más clara."
        return await self.send_message(to, message)
    
    async def send_partial_success(self, to: str, warnings: list):
        """Send partial success message"""
        message = f"""⚠️ *Lectura Parcial*

Advertencias:
{chr(10).join(f'• {w}' for w in warnings)}"""
        return await self.send_message(to, message)


# Global instance
unified_handler = UnifiedWhatsAppHandler()