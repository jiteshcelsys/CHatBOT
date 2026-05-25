import logging

from supabase import acreate_client, AsyncClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None


async def get_supabase() -> AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set."
            )
        _client = await acreate_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("Supabase client initialised | url=%s", settings.supabase_url[:40])
    return _client
