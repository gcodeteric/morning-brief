"""SimulaNewsMachine — Configuração central."""
from pathlib import Path

HOME = Path.home()
DESKTOP = HOME / "Desktop"
PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = DESKTOP / "SIMULA_BRIEF_HOJE.md"
ARCHIVE_DIR = PROJECT_DIR / "archive"
LOG_DIR = PROJECT_DIR / "logs"
OUTPUT_DIR = PROJECT_DIR / "output"
DATA_DIR = PROJECT_DIR / "data"

# Ficheiros de estado persistente
SEEN_LINKS_FILE = DATA_DIR / "seen_links.json"
RUN_SUMMARY_FILE = DATA_DIR / "run_summary.json"
EXTRACTED_IDS_FILE = DATA_DIR / "extracted_channel_ids.json"

SCAN_HOUR = 5
SCAN_MINUTE = 0
HOURS_LOOKBACK = 28  # 28h em vez de 24 para não perder nada
MAX_ARTICLES_OUTPUT = 15
FEED_TIMEOUT_SECONDS = 10
MIN_RELEVANCE_SCORE = 15
SEEN_LINKS_MAX_AGE_HOURS = 72  # Limpar links com mais de 3 dias

GUARANTEE_CATEGORIES = {
    "sim_racing": 2,    # Categoria nuclear do negócio
    "nostalgia": 1,
    "hardware": 1,
    "motorsport": 1,
    "racing_games": 1,
}
GUARANTEE_PORTUGAL = True
MAX_PER_SOURCE = 3  # Máximo de artigos por fonte no top 15

# Criar pastas se não existirem
for d in [LOG_DIR, ARCHIVE_DIR, OUTPUT_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)
