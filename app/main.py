"""
Main FastAPI application with WhatsApp webhook endpoint
"""
from fastapi import FastAPI, Form, Request, HTTPException, UploadFile, File
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import json
import asyncio
import httpx

from app.utils.logger import app_logger
from app.utils.config import settings
from app.utils.image_processor import optimize_image_for_ocr, validate_image_format
from app.models import WhatsAppMessage, ProcessingResult, Invoice
from app.whatsapp_handler import whatsapp_handler
from app.greenapi_handler import greenapi_handler
from app.unified_whatsapp_handler import unified_handler
from app.ocr_processor import ocr_processor
from app.ncf_parser import ncf_parser
from app.export_handler import export_handler
from app.firebase_handler import firebase_handler

# Create FastAPI app
app = FastAPI(
    title="LECTOR-NCF",
    description="Sistema de Lectura OCR de Facturas NCF desde WhatsApp",
    version="1.0.0"
)

# Constants for Credentials
CREDENTIALS_DIR = Path("credentials")
FIREBASE_CRED_PATH = CREDENTIALS_DIR / "firebase-credentials.json"


def check_firebase_credentials():
    """Returns True if Firebase credentials are configured (file or Base64)."""
    # Check if file exists locally
    if FIREBASE_CRED_PATH.exists():
        return True
    
    # Check if Base64 credentials exist in environment
    if os.environ.get("FIREBASE_CREDENTIALS_BASE64"):
        return True
    
    return False


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    app_logger.info("=" * 50)
    app_logger.info("LECTOR-NCF Starting...")
    app_logger.info(f"Debug mode: {settings.debug}")
    app_logger.info(f"WhatsApp mode: {settings.whatsapp_mode}")
    app_logger.info("=" * 50)
    
    # Create necessary directories
    os.makedirs("data/temp", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    
    if not check_firebase_credentials():
        app_logger.warning("⚠️ FIREBASE CREDENTIALS NOT FOUND. Please visit /setup to configure them.")
    
    # Start Green-API polling if enabled (BACKUP para webhook)
    if greenapi_handler.enabled:
        app_logger.info("🔄 Starting Green-API polling task...")
        asyncio.create_task(greenapi_polling_loop())
        app_logger.info("✅ Green-API polling started (webhook + polling dual mode)")


async def greenapi_polling_loop():
    """Background task to poll Green-API for incoming messages (backup to webhook)"""
    app_logger.info("🔄 Green-API polling loop started")
    
    # Esperar 10 segundos antes de iniciar polling
    await asyncio.sleep(10)
    
    while True:
        try:
            notification = await greenapi_handler.receive_notification()
            
            if notification:
                app_logger.info(f"📥 POLLING RECEIVED: {notification.get('typeWebhook')}")
                
                # Process incoming message (mismo handler que webhook)
                await process_greenapi_notification(notification)
            
            # Poll every 5 seconds
            await asyncio.sleep(5)
            
        except Exception as e:
            app_logger.error(f"Error in polling loop: {e}")
            await asyncio.sleep(10)


async def process_greenapi_notification(notification: dict):
    """Process incoming Green-API notification (usado por webhook Y polling)"""
    try:
        # Extract notification type
        type_webhook = notification.get("typeWebhook")
        
        app_logger.info("=" * 70)
        app_logger.info("📥 GREEN-API MESSAGE")
        app_logger.info(f"Type: {type_webhook}")
        app_logger.info("=" * 70)
        
        # Ignorar mensajes salientes
        if type_webhook in ["outgoingMessageStatus", "outgoingAPIMessageReceived"]:
            app_logger.info("⏭️ Skipping outgoing message")
            return
        
        # Only process incoming messages
        if type_webhook != "incomingMessageReceived":
            return
        
        # Extract message data
        message_data = notification.get("messageData", {})
        sender_data = notification.get("senderData", {})
        
        # Get sender
        chat_id = sender_data.get("chatId", "")
        sender = sender_data.get("sender", "")
        message_type = message_data.get("typeMessage", "")
        
        # Extract phone number
        phone = chat_id.split("@")[0] or sender.split("@")[0]
        from_number = f"whatsapp:+{phone}"
        
        app_logger.info(f"From: {from_number}, Type: {message_type}")
        
        # Process image messages
        if message_type == "imageMessage":
            app_logger.info(f"Processing image from {from_number}")
            
            # Send confirmation
            await unified_handler.send_confirmation(from_number)
            
            # Extract download URL from multiple possible locations
            file_message_data = message_data.get("fileMessageData", {})
            download_url = (
                file_message_data.get("downloadUrl") or
                message_data.get("downloadUrl") or
                message_data.get("imageMessageData", {}).get("downloadUrl")
            )
            
            app_logger.info(f"🔍 Extracted download_url: {download_url}")
            
            if not download_url:
                app_logger.error("❌ downloadUrl not found in messageData")
                app_logger.error(f"📋 messageData keys: {list(message_data.keys())}")
                app_logger.error(f"📋 Full messageData: {json.dumps(message_data, indent=2)}")
                await unified_handler.send_error(from_number, "No se pudo obtener URL de descarga")
                return
            
            app_logger.info(f"⬇️ Downloading from: {download_url}")
            
            # Download image
            try:
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(download_url, timeout=30.0)
                    img_response.raise_for_status()
                    image_bytes = img_response.content
                
                app_logger.info(f"✅ Image downloaded: {len(image_bytes)} bytes")
            except Exception as e:
                app_logger.error(f"❌ Download failed: {e}")
                await unified_handler.send_error(from_number, f"Error descargando imagen: {str(e)}")
                return
            
            # Process invoice
            await process_invoice_image(from_number, image_bytes)
        
        elif message_type in ["textMessage", "extendedTextMessage"]:
            # Extract text from either format
            text_message_data = message_data.get("textMessageData", {})
            extended_text_data = message_data.get("extendedTextMessageData", {})
            
            text_message = (
                text_message_data.get("textMessage", "") or
                extended_text_data.get("text", "")
            )
            
            app_logger.info(f"📝 Text message: {text_message}")
            
            await unified_handler.send_message(
                from_number,
                "Por favor envía una foto de la factura. 📸"
            )
        
        else:
            app_logger.info(f"⚠️ Unsupported message type: {message_type}")
    
    except Exception as e:
        app_logger.error(f"❌ Error processing Green-API notification: {e}")
        import traceback
        app_logger.error(traceback.format_exc())


async def process_invoice_image(sender: str, image_bytes: bytes):
    """Process invoice image (shared by both Twilio and Green-API)"""
    try:
        # Check Firebase credentials
        if not check_firebase_credentials():
            app_logger.error("Firebase not configured")
            await unified_handler.send_error(sender, "Sistema no configurado")
            return
        
        # Save temporary image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"factura_{timestamp}.jpg"
        temp_path = Path("data/temp") / image_filename
        
        with open(temp_path, 'wb') as f:
            f.write(image_bytes)
        
        app_logger.info(f"💾 Saved to: {temp_path}")
        
        # Optimize and process OCR
        app_logger.info("🔍 Processing image with OCR...")
        optimized_image = optimize_image_for_ocr(image_bytes)
        ocr_text, confidence = ocr_processor.process_invoice_image(optimized_image)
        
        if not ocr_text:
            await unified_handler.send_error(sender, "No se pudo leer texto en la imagen")
            return
        
        app_logger.info(f"✅ OCR completed with confidence: {confidence}")
        
        # Parse invoice data
        invoice = ncf_parser.parse_invoice(ocr_text, confidence, image_filename)
        
        app_logger.info(f"📊 Extracted data: NCF={invoice.ncf}, RNC={invoice.rnc}, Total={invoice.montos.total}")
        
        # Check for warnings
        warnings = []
        if not invoice.ncf:
            warnings.append("NCF no encontrado")
        if not invoice.montos.total:
            warnings.append("Monto total no encontrado")
        
        # Export to CSV/JSON
        export_handler.export([invoice])
        
        # Save to Firebase
        try:
            app_logger.info("💾 Saving to Firebase...")
            firebase_handler.save_invoice(invoice)
            app_logger.info(f"✅ Invoice saved to Firebase: {invoice.id}")
        except Exception as e:
            app_logger.error(f"Firebase save failed: {e}")
        
        # Move to processed
        processed_path = Path("data/processed") / image_filename
        temp_path.rename(processed_path)
        
        # Send response
        if warnings:
            await unified_handler.send_partial_success(sender, warnings)
        elif invoice.ncf:
            await unified_handler.send_success(sender, invoice.ncf, invoice.montos.total)
        else:
            await unified_handler.send_error(sender)
        
        app_logger.info("✅ Image processing completed successfully")
        
    except Exception as e:
        app_logger.error(f"Error processing invoice image: {e}")
        import traceback
        traceback.print_exc()
        await unified_handler.send_error(sender, "Error interno del sistema")


@app.get("/")
async def root():
    """Root endpoint - redirects to setup if credentials are missing"""
    if not check_firebase_credentials():
        return RedirectResponse(url="/setup")
        
    return {
        "status": "running",
        "service": "LECTOR-NCF",
        "firebase_configured": True,
        "whatsapp_mode": settings.whatsapp_mode,
        "greenapi_enabled": greenapi_handler.enabled,
        "endpoints": {
            "webhook_twilio": "/webhook/whatsapp",
            "webhook_greenapi": "/webhook/greenapi",
            "setup": "/setup"
        }
    }


# ==========================================
# SETUP UI (WEB CREDENTIAL SELECTOR)
# ==========================================

@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    """Displays the web UI to upload Firebase credentials"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LECTOR-NCF | Configuración</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { background-color: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 500px; text-align: center; }
            h2 { color: #333; }
            .upload-box { border: 2px dashed #4CAF50; padding: 30px; margin: 20px 0; border-radius: 5px; }
            .btn { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; width: 100%; margin-top: 10px;}
            .btn:hover { background-color: #45a049; }
            .success { color: green; font-weight: bold; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔥 Configuración de Firebase</h2>
            <p>El sistema requiere el archivo <b>firebase-credentials.json</b> para funcionar.</p>
            
            <form action="/setup/upload" method="post" enctype="multipart/form-data">
                <div class="upload-box">
                    <input type="file" name="file" accept=".json" required>
                </div>
                <input type="text" name="database_url" placeholder="URL de la Base de Datos (ej. https://...firebaseio.com)" required style="width: 100%; padding: 10px; margin-bottom: 15px; box-sizing: border-box;">
                <button type="submit" class="btn">💾 Guardar y Conectar</button>
            </form>
            
            """ + (f"<div class='success'>✅ Credenciales configuradas. El servidor está listo.</div>" if check_firebase_credentials() else "") + """
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/setup/upload")
async def upload_credentials(file: UploadFile = File(...), database_url: str = Form(...)):
    """Handles the upload of the credentials file and saves it"""
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="El archivo debe ser un JSON")

        # Create credentials directory if it doesn't exist
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        
        # Save the uploaded file
        with open(FIREBASE_CRED_PATH, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Verify it's a valid JSON
        try:
            with open(FIREBASE_CRED_PATH, "r") as f:
                json.load(f)
        except json.JSONDecodeError:
            os.remove(FIREBASE_CRED_PATH)
            raise HTTPException(status_code=400, detail="El archivo JSON es inválido o está corrupto.")

        # Re-initialize Firebase Handler
        settings.firebase_credentials = str(FIREBASE_CRED_PATH)
        settings.firebase_database_url = database_url
        firebase_handler.__init__()

        return RedirectResponse(url="/setup", status_code=303)
        
    except Exception as e:
        app_logger.error(f"Error saving credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# WEBHOOK ENDPOINTS
# ==========================================

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(...),
    NumMedia: str = Form("0"),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
    Body: Optional[str] = Form(None)
):
    """WhatsApp webhook endpoint for receiving messages from Twilio"""
    
    # Check Firebase credentials before processing
    if not check_firebase_credentials():
        app_logger.error("Message received but Firebase is not configured.")
        return Response(content="", status_code=200)

    app_logger.info(f"📥 TWILIO MESSAGE from {From}")
    
    try:
        num_media = int(NumMedia)
        
        if num_media == 0:
            await unified_handler.send_message(From, "Por favor envía una foto de la factura. 📸")
            return Response(content="", status_code=200)
        
        await unified_handler.send_confirmation(From)
        
        # Download image from Twilio
        image_bytes = await whatsapp_handler.download_media(MediaUrl0, settings.twilio_auth_token)
        if not image_bytes:
            await unified_handler.send_error(From, "No se pudo descargar la imagen")
            return Response(content="", status_code=200)
        
        # Process invoice
        await process_invoice_image(From, image_bytes)
        
        return Response(content="", status_code=200)
        
    except Exception as e:
        app_logger.error(f"Error processing Twilio message: {e}")
        import traceback
        traceback.print_exc()
        try:
            await unified_handler.send_error(From, "Error interno del sistema")
        except:
            pass
        return Response(content="", status_code=200)


@app.post("/webhook/greenapi")
async def greenapi_webhook(request: Request):
    """Webhook endpoint for Green-API (alternative to polling)"""
    try:
        notification = await request.json()
        app_logger.info(f"📥 GREEN-API WEBHOOK: {notification.get('typeWebhook')}")
        
        await process_greenapi_notification(notification)
        
        return {"status": "ok"}
        
    except Exception as e:
        app_logger.error(f"Error processing Green-API webhook: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)