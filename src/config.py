"""
Configuración centralizada para el proyecto de IA en Contabilidad
Manejo seguro de variables de entorno y configuraciones
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración base del proyecto"""
    
    # Configuración de directorios
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "datos"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    RESULTS_DIR = BASE_DIR / "resultados"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Configuración de ambiente
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Configuración de logging
    LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
    
    @classmethod
    def create_directories(cls):
        """Crear directorios necesarios si no existen"""
        for directory in [cls.DATA_DIR, cls.RAW_DATA_DIR, 
                         cls.PROCESSED_DATA_DIR, cls.RESULTS_DIR, cls.LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            
    @classmethod
    def validate_api_keys(cls):
        """Validar que las API keys estén configuradas"""
        required_keys = [
            "ALPHA_VANTAGE_API_KEY",
            "NEWS_API_KEY",
            "TWITTER_BEARER_TOKEN"
        ]
        
        missing_keys = []
        for key in required_keys:
            if not os.getenv(key):
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Faltan las siguientes API keys: {', '.join(missing_keys)}")
        
        return True

class APIConfig:
    """Configuración específica de APIs"""
    
    # Alpha Vantage
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
    
    # News API
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    NEWS_API_BASE_URL = "https://newsapi.org/v2"
    
    # Twitter API
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
    TWITTER_API_BASE_URL = "https://api.twitter.com/2"
    
    # Rate limiting
    API_RATE_LIMITS = {
        "alpha_vantage": {"requests": 25, "period": "day"},
        "news_api": {"requests": 1000, "period": "day"},
        "twitter": {"requests": 300, "period": "15_minutes"}
    }

class DatabaseConfig:
    """Configuración de base de datos (si aplica)"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    
# Configuración de logging
def setup_logging():
    """Configurar sistema de logging"""
    Config.create_directories()
    
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOGS_DIR / 'app.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

# Instancia global del logger
logger = setup_logging()
