from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    cors_origins: str = "http://localhost:3000"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Firebase
    firebase_project_id: str = ""
    firebase_private_key_id: str = ""
    firebase_private_key: str = ""
    firebase_client_email: str = ""

    # LangChain / Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"   # default chat model
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "chatbot"

    # HuggingFace embeddings (local, no API key required)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"
    chroma_chunk_size: int = 1000
    chroma_chunk_overlap: int = 200
    chroma_cloud_api_key: str = ""
    chroma_cloud_tenant: str = ""
    chroma_cloud_database: str = "default_database"

    # Ingestion pipeline
    ingestion_allowed_types: list[str] = [".pdf", ".txt", ".docx", ".md"]
    ingestion_max_file_size_mb: int = 50
    ingestion_max_batch_files: int = 10

    # Chat / sessions
    chat_max_sessions_per_user: int = 20
    chat_summary_threshold: int = 20   # trigger summarisation after N messages

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
