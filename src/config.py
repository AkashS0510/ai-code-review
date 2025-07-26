import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL")

    # PostgreSQL Configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL")

    # Celery Configuration
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # API Configuration
    API_V1_STR = "/api/v1"
