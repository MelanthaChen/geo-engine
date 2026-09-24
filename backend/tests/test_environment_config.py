import os
from pathlib import Path
import subprocess
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_config_import(**environment):
    env = {
        "PATH": os.environ["PATH"],
        "PYTHONPATH": str(BACKEND_DIR),
        **environment,
    }
    return subprocess.run(
        [sys.executable, "-c", "from app.core.config import settings; print(settings.APP_ENV)"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def production_environment(**overrides):
    values = {
        "APP_ENV": "production",
        "OPENAI_API_KEY": "test-key",
        "DATABASE_URL": "postgresql://user:password@database.internal/geo_engine",
        "DEMO_TARGET_URL": "https://resume.example.com/guide",
        "FRONTEND_ORIGINS": "https://frontend.example.com",
        "BACKEND_URL": "https://backend.example.com",
    }
    values.update(overrides)
    return values


def test_production_configuration_uses_process_environment():
    result = run_config_import(**production_environment())
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "production"


def test_production_rejects_local_database():
    result = run_config_import(**production_environment(
        DATABASE_URL="postgresql://user:password@127.0.0.1:5433/geo_engine"
    ))
    assert result.returncode != 0
    assert "Production DATABASE_URL must not use localhost" in result.stderr


def test_production_requires_public_demo_target():
    result = run_config_import(**production_environment(
        DEMO_TARGET_URL="http://127.0.0.1:8000"
    ))
    assert result.returncode != 0
    assert "Production DEMO_TARGET_URL must be a public HTTPS URL" in result.stderr


def test_production_requires_frontend_origins():
    result = run_config_import(**production_environment(FRONTEND_ORIGINS=""))
    assert result.returncode != 0
    assert "FRONTEND_ORIGINS is required in production" in result.stderr
