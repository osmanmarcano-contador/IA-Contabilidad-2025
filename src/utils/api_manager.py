"""
Gestor centralizado y seguro para todas las APIs del proyecto
Incluye rate limiting, manejo de errores y logging
"""

import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from src.config import APIConfig, logger

class APIRateLimiter:
    """Control de límites de rate para APIs"""
    
    def __init__(self):
        self.api_calls = {}
    
    def can_make_request(self, api_name: str) -> bool:
        """Verificar si se puede hacer una petición a la API"""
        now = datetime.now()
        
        if api_name not in self.api_calls:
            self.api_calls[api_name] = []
        
        # Limpiar llamadas antiguas
        rate_limit = APIConfig.API_RATE_LIMITS.get(api_name, {})
        if not rate_limit:
            return True
            
        period = rate_limit.get("period", "day")
        max_requests = rate_limit.get("requests", 1000)
        
        if period == "day":
            cutoff = now - timedelta(days=1)
        elif period == "15_minutes":
            cutoff = now - timedelta(minutes=15)
        else:
            cutoff = now - timedelta(hours=1)
        
        self.api_calls[api_name] = [
            call_time for call_time in self.api_calls[api_name] 
            if call_time > cutoff
        ]
        
        return len(self.api_calls[api_name]) < max_requests
    
    def record_request(self, api_name: str):
        """Registrar una petición realizada"""
        if api_name not in self.api_calls:
            self.api_calls[api_name] = []
        
        self.api_calls[api_name].append(datetime.now())

class AlphaVantageAPI:
    """Cliente para Alpha Vantage API"""
    
    def __init__(self, rate_limiter: APIRateLimiter):
        self.api_key = APIConfig.ALPHA_VANTAGE_API_KEY
        self.base_url = APIConfig.ALPHA_VANTAGE_BASE_URL
        self.rate_limiter = rate_limiter
        
        if not self.api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY no configurada")
    
    def get_stock_data(self, symbol: str, function: str = "TIME_SERIES_DAILY") -> Dict:
        """Obtener datos de acciones"""
        if not self.rate_limiter.can_make_request("alpha_vantage"):
            raise Exception("Rate limit excedido para Alpha Vantage")
        
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            self.rate_limiter.record_request("alpha_vantage")
            logger.info(f"Datos obtenidos para {symbol} desde Alpha Vantage")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener datos de Alpha Vantage: {e}")
            raise

class NewsAPI:
    """Cliente para News API"""
    
    def __init__(self, rate_limiter: APIRateLimiter):
        self.api_key = APIConfig.NEWS_API_KEY
        self.base_url = APIConfig.NEWS_API_BASE_URL
        self.rate_limiter = rate_limiter
        
        if not self.api_key:
            raise ValueError("NEWS_API_KEY no configurada")
    
    def get_financial_news(self, query: str = "financial", language: str = "en") -> Dict:
        """Obtener noticias financieras"""
        if not self.rate_limiter.can_make_request("news_api"):
            raise Exception("Rate limit excedido para News API")
        
        headers = {"X-API-Key": self.api_key}
        params = {
            "q": query,
            "language": language,
            "sortBy": "publishedAt",
            "pageSize": 20
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/everything", 
                headers=headers, 
                params=params, 
                timeout=30
            )
            response.raise_for_status()
            
            self.rate_limiter.record_request("news_api")
            logger.info(f"Noticias obtenidas para query: {query}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener noticias: {e}")
            raise

class TwitterAPI:
    """Cliente para Twitter API v2"""
    
    def __init__(self, rate_limiter: APIRateLimiter):
        self.bearer_token = APIConfig.TWITTER_BEARER_TOKEN
        self.base_url = APIConfig.TWITTER_API_BASE_URL
        self.rate_limiter = rate_limiter
        
        if not self.bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN no configurado")
    
    def search_tweets(self, query: str, max_results: int = 10) -> Dict:
        """Buscar tweets relacionados con el query"""
        if not self.rate_limiter.can_make_request("twitter"):
            raise Exception("Rate limit excedido para Twitter API")
        
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,context_annotations"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            self.rate_limiter.record_request("twitter")
            logger.info(f"Tweets obtenidos para query: {query}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener tweets: {e}")
            raise

class APIManager:
    """Gestor centralizado de todas las APIs"""
    
    def __init__(self):
        self.rate_limiter = APIRateLimiter()
        self.alpha_vantage = AlphaVantageAPI(self.rate_limiter)
        self.news_api = NewsAPI(self.rate_limiter)
        self.twitter_api = TwitterAPI(self.rate_limiter)
    
    def get_comprehensive_market_data(self, symbol: str) -> Dict[str, Any]:
        """Obtener datos completos de mercado de todas las fuentes"""
        data = {}
        
        try:
            # Datos de Alpha Vantage
            data["stock_data"] = self.alpha_vantage.get_stock_data(symbol)
            logger.info(f"✅ Datos de acciones obtenidos para {symbol}")
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de acciones: {e}")
            data["stock_data"] = None
        
        try:
            # Noticias relacionadas
            data["news"] = self.news_api.get_financial_news(symbol)
            logger.info(f"✅ Noticias obtenidas para {symbol}")
        except Exception as e:
            logger.error(f"❌ Error obteniendo noticias: {e}")
            data["news"] = None
        
        try:
            # Sentiment de Twitter
            data["social_sentiment"] = self.twitter_api.search_tweets(f"${symbol}")
            logger.info(f"✅ Datos de Twitter obtenidos para {symbol}")
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de Twitter: {e}")
            data["social_sentiment"] = None
        
        return data
