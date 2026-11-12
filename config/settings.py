"""Uygulama ayarları — .env dosyasından pydantic-settings ile okunur."""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """JWT ve veritabanı bağlantı yapılandırması."""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Şema kurulumu ve seed: postgres süper kullanıcısı (RLS'i bypass eder).
    DATABASE_URL: str
    # API veri erişimi: kısıtlı school_app rolü (NOSUPERUSER, NOBYPASSRLS).
    APP_DATABASE_URL: str
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str
    # Boş bırakılırsa niyet analizi LLM_MODEL kullanır.
    INTENT_MODEL: str = ""
    # Çalıştırılan SELECT metnini /query yanıtına ekler. SHOW_SQL=false ile kapanır.
    SHOW_SQL: bool = True
    # Virgülle ayrılmış tarayıcı kökenleri. Yıldız kabul edilmez.
    CORS_ORIGINS: str = "http://localhost:8501"
    # Okul yönetmeliği: 100'lük sistemde ders geçme notu.
    PASS_GRADE: int = 50
    # 5'lik veya harf dönüşümü. Boşsa dönüşüm yapılmaz.
    GRADE_LABELS: str = ""
    # Şema özetindeki "bugün". Boşsa takvim günü kullanılır.
    REFERENCE_DATE: str = ""

    def cors_origin_list(self) -> list[str]:
        return [parca.strip() for parca in self.CORS_ORIGINS.split(",") if parca.strip()]

    @model_validator(mode="after")
    def _intent_model_varsayilan(self) -> "Settings":
        if not self.INTENT_MODEL.strip():
            self.INTENT_MODEL = self.LLM_MODEL
        return self


settings = Settings()
