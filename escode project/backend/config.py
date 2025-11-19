import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

class Config:
    # ==============================
    # Database
    # ==============================
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/quotations.db')
    
    # ==============================
    # Security
    # ==============================
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    SESSION_TIMEOUT = 3600  # 1 hour in seconds
    
    # ==============================
    # Email Configuration
    # ==============================
    EMAIL_PROVIDER = os.getenv('EMAIL_PROVIDER', 'gmail')  # gmail, outlook, etc
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', 993))
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    
    # ==============================
    # AI Configuration
    # ==============================
    # Flags for which AI to use
    USE_LOCAL_AI = os.getenv('USE_LOCAL_AI', 'True').lower() == 'true'
    USE_EXTERNAL_FREE_AI = os.getenv('USE_EXTERNAL_FREE_AI', 'False').lower() == 'true'
    USE_BEDROCK = os.getenv('USE_BEDROCK', 'False').lower() == 'true'
    
    # Local AI (Ollama)
    LOCAL_AI_BASE_URL = os.getenv('LOCAL_AI_BASE_URL', 'http://localhost:11434')
    LOCAL_AI_MODEL = os.getenv('LOCAL_AI_MODEL', 'ollama-model-name')
    
    # External Free AI (Groq, Together, etc)
    EXTERNAL_AI_API_KEY = os.getenv('EXTERNAL_AI_API_KEY', '')
    EXTERNAL_AI_BASE_URL = os.getenv('EXTERNAL_AI_BASE_URL', 'https://api.groq.com/openai/v1')
    EXTERNAL_AI_MODEL = os.getenv('EXTERNAL_AI_MODEL', 'llama-3.1-70b-versatile')
    
    # Bedrock (AWS) - for future migration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    
    # ==============================
    # Application
    # ==============================
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # ==============================
    # Batch processing
    # ==============================
    BATCH_SIZE = 100  # For processing large publisher database
    MAX_EMAIL_FETCH = 50  # Max emails to fetch per sync
    
    @staticmethod
    def validate():
        """Validate critical configuration"""
        errors = []
        
        if Config.USE_EXTERNAL_FREE_AI and not Config.EXTERNAL_AI_API_KEY:
            errors.append("EXTERNAL_AI_API_KEY is required when using external free AI")
        
        if Config.EMAIL_ADDRESS and not Config.EMAIL_PASSWORD:
            errors.append("EMAIL_PASSWORD is required when EMAIL_ADDRESS is set")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))
        
        return True

# Create instance to import
config = Config()
