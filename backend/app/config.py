from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "格物学术"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    jwt_secret: str = "change_me_in_prod"
    jwt_expire_minutes: int = 60 * 24 * 7

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "root"
    mysql_database: str = "wuhongai"
    sqlite_path: str = "wuhongai.db"
    db_fallback_sqlite: bool = True

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0

    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    celery_result_backend: str = "redis://127.0.0.1:6379/0"

    initial_credits: int = 2000
    referral_register_inviter_credits: int = 500
    referral_register_invitee_bonus: int = 500
    max_code_retry: int = 3
    phone_lock_minutes: int = 5
    auth_send_code_ip_1h_limit: int = 30
    auth_login_ip_10m_limit: int = 120
    auth_return_debug_code: bool = False

    admin_init_username: str = "admin"
    admin_init_password: str = "admin123456"
    payment_sign_secret: str = "change_me_payment_sign_key"
    payment_callback_ttl_seconds: int = 900
    payment_test_mode: bool = True
    frontend_base_url: str = ""
    sms_api_key: str = ""
    sms_gateway_url: str = ""

    algorithm_package_root: str = ""
    algorithm_package_max_mb: int = 200
    algorithm_package_exec_timeout_seconds: int = 8
    docx_process_table_text: bool = True

    llm_enabled_default: bool = False
    llm_api_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 25

    @property
    def mysql_dsn(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def sqlite_dsn(self) -> str:
        db_file = Path(__file__).resolve().parent.parent / self.sqlite_path
        return f"sqlite:///{db_file}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def upload_dir(self) -> Path:
        p = Path(__file__).resolve().parent.parent / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_dir(self) -> Path:
        p = Path(__file__).resolve().parent.parent / "output"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def algorithm_package_dir(self) -> Path:
        if self.algorithm_package_root:
            p = Path(self.algorithm_package_root)
            if not p.is_absolute():
                p = Path(__file__).resolve().parent.parent / p
        else:
            p = Path(__file__).resolve().parent.parent / "algorithm_packages"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
