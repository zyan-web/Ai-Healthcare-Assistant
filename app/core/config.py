"""
Central configuration for Stage A (standalone agent).

Nothing here touches FastAPI, a real database, or auth — those are added
only after the standalone agent is stable (see project docs, section 29).
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    agent_model: str = os.getenv("AGENT_MODEL", "llama-3.3-70b-versatile")
    synthetic_data_seed: int = int(os.getenv("SYNTHETIC_DATA_SEED", "42"))


settings = Settings()
