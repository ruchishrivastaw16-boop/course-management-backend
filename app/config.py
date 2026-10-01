from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Database ───
    DATABASE_URL: str

    # ─── JWT Auth ───
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ─── CORS ───
    CORS_ORIGINS: str = "http://localhost:5173"

    # ─── Razorpay ───
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"          # ← YE ZAROORI HAI


settings = Settings()