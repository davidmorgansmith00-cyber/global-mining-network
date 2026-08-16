from app.settings import settings


def database_is_configured() -> bool:
    return bool(settings.database_url)