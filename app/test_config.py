from app.core.config import settings

def test_settings_load():
    assert settings.APP_NAME == "NewGWSH"
    assert "postgresql+asyncpg" in settings.ASYNC_DATABASE_URL
    assert "postgresql+psycopg2" in settings.SYNC_DATABASE_URL
    print("Settings validation passed!")

if __name__ == "__main__":
    try:
        test_settings_load()
    except Exception as e:
        print(f"Validation failed: {e}")
        exit(1)
