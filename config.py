"""
Production Configuration for Football Predictions App
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""

    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    # API Keys
    SOFASCORE_API_KEY = os.getenv('SOFASCORE_API_KEY')
    RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST', 'sofascore.p.rapidapi.com')

    # Security
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

    # Feature Flags
    ENABLE_BBC_SCRAPER = os.getenv('ENABLE_BBC_SCRAPER', 'True').lower() == 'true'
    ENABLE_SOFA_SCORE_API = os.getenv('ENABLE_SOFA_SCORE_API', 'True').lower() == 'true'
    ENABLE_BTTS_TRACKER = os.getenv('ENABLE_BTTS_TRACKER', 'True').lower() == 'true'

    # Backup Settings
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', 30))
    BACKUP_PATH = os.getenv('BACKUP_PATH', 'data/backups')

class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    LOG_LEVEL = 'WARNING'

    # In production, ensure these are set via environment variables
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")

    SOFASCORE_API_KEY = os.getenv('SOFASCORE_API_KEY')
    if not SOFASCORE_API_KEY:
        raise ValueError("SOFASCORE_API_KEY environment variable must be set in production")

class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    LOG_LEVEL = 'DEBUG'

    # Development can use default values
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

    # Use test-specific settings
    SECRET_KEY = 'test-secret-key'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration object"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    return config.get(config_name, config['default'])()