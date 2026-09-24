import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "Dataset"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "answers"
LOGS_DIR = PROJECT_ROOT / "logs"

class TigerGraphConfig(BaseModel):
    host: str = os.getenv("TG_HOST", "localhost")
    port: int = int(os.getenv("TG_PORT", "9000"))
    username: str = os.getenv("TG_USERNAME", "tigergraph")
    password: str = os.getenv("TG_PASSWORD", "tigergraph")
    graph_name: str = os.getenv("TG_GRAPHNAME", "fraud_investigation")
    backend: str = os.getenv("GRAPH_BACKEND", "networkx")

class LLMConfig(BaseModel):
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    api_key: str = os.getenv("OPENAI_API_KEY", "")

class FraudConfig(BaseModel):
    confidence_threshold: float = 0.85
    low_confidence_threshold: float = 0.15
    case_open_threshold: float = 0.30
    verification_threshold: float = 0.70
    max_evidence_budget: int = 15
    stopping_marginal_gain: float = 0.05
    sar_exposure_threshold: float = 1000.0
    escalation_exposure_threshold: float = 500.0
    card_testing_window_hours: int = 1
    card_testing_min_count: int = 3
    card_testing_max_amount: float = 5.0
    card_not_present_burst_hours: int = 48
    card_not_present_burst_min: int = 2

tg_config = TigerGraphConfig()
llm_config = LLMConfig()
fraud_config = FraudConfig()
