"""
Configuration management for LECTOR-NCF application
"""
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()


class Settings:
    def __init__(self):
        # Firebase2
        self.firebase_credentials = os.environ.get(
            "FIREBASE_CREDENTIALS",
            "credentials/firebase-credentials.json"
        )
        self.firebase_database_url = os.environ.get(
            "FIREBASE_DATABASE_URL",
            "https://facot-app-default-rtdb.firebaseio.com/"
        )
        
        # Google Cloud Vision
        self.google_credentials = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "credentials/google-vision-credentials.json"
        )
        
        # Legacy config name (for backward compatibility)
        self.google_application_credentials = self.google_credentials
        
        # Twilio
        self.twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.twilio_whatsapp_number = os.environ.get(
            "TWILIO_WHATSAPP_NUMBER",
            "whatsapp:+14155238886"
        )
        
        # Green-API
        self.greenapi_instance_id = os.environ.get("GREENAPI_INSTANCE_ID")
        self.greenapi_token = os.environ.get("GREENAPI_TOKEN")
        
        # WhatsApp Mode
        self.whatsapp_mode = os.environ.get("WHATSAPP_MODE", "dual")
        
        # Server
        self.port = int(os.environ.get("PORT", 8000))
        self.debug = os.environ.get("DEBUG", "False").lower() == "true"
        self.host = os.environ.get("HOST", "0.0.0.0")
        
        # Logging
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        
        # Additional settings
        self.google_cloud_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
        self.twilio_webhook_url = os.environ.get("TWILIO_WEBHOOK_URL")
        self.export_format = os.environ.get("EXPORT_FORMAT", "both")
        self.csv_delimiter = os.environ.get("CSV_DELIMITER", ",")
        self.timezone = os.environ.get("TIMEZONE", "America/Santo_Domingo")
        self.max_image_size_mb = int(os.environ.get("MAX_IMAGE_SIZE_MB", 10))


# Global settings instance
settings = Settings()