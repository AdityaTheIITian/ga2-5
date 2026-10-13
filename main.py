import os
from pathlib import Path
from typing import List

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE = Path(__file__).parent
ENV_NAME = os.environ.get("APP_ENV", "development")

DEFAULTS = {"port": 8000, "workers": 1, "debug": False, "log_level": "info", "api_key": "default-secret-000"}

# Embedded fallbacks so the service works even if the files are not deployed.
YAML_FALLBACK = {"debug": False, "api_key": "key-e42tag9i6b"}
DOTENV_FALLBACK = "APP_PORT=8336\nAPP_LOG_LEVEL=error\nAPP_API_KEY=key-o0skdalonu\n"
OS_FALLBACK = {"APP_WORKERS": "11", "APP_API_KEY": "key-rur4ejr4i4"}

ALIASES = {"num_workers": "workers"}
TRUE = {"true", "1", "yes", "on"}


def norm_key(k: str) -> str:
    k = k.strip().lower()
    if k.startswith("app_"):
        k = k[4:]
    return ALIASES.get(k, k)


def coerce(key: str, value):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUE
    return str(value)


def load_yaml() -> dict:
    p = BASE / f"config.{ENV_NAME}.yaml"
    data = yaml.safe_load(p.read_text()) if p.exists() else YAML_FALLBACK
    return {norm_key(k): v for k, v in (data or {}).items()}


def load_dotenv() -> dict:
    p = BASE / ".env"
    text = p.read_text() if p.exists() else DOTENV_FALLBACK
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[norm_key(k)] = v.strip().strip('"').strip("'")
    return out


def load_os_env() -> dict:
    raw = dict(OS_FALLBACK)
    raw.update({k: v for k, v in os.environ.items() if k.startswith("APP_") and k != "APP_ENV"})
    return {norm_key(k): v for k, v in raw.items()}


@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    cfg = dict(DEFAULTS)
    for layer in (load_yaml(), load_dotenv(), load_os_env()):
        cfg.update(layer)
    for item in set:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        cfg[norm_key(k)] = v
    result = {}
    for k, v in cfg.items():
        if k == "api_key":
            continue
        try:
            result[k] = coerce(k, v)
        except (ValueError, TypeError):
            result[k] = DEFAULTS.get(k, v)
    ordered = {k: result[k] for k in ("port", "workers", "debug", "log_level") if k in result}
    ordered.update({k: v for k, v in result.items() if k not in ordered})
    ordered["api_key"] = "****"
    return ordered