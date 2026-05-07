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

# Official content classification
# FIX 2026-05-11: centralizar regras de classificação oficial/não oficial.
OFFICIAL_ANNOUNCEMENT_KEYWORDS = [
    # Direct announcements
    "announces", "announced", "launches", "launched", "releases", "released",
    "confirms", "confirmed", "reveals", "revealed", "introduces", "introduced",
    # Product/update language
    "new product", "new hardware", "patch notes", "update v", "version ",
    "changelog", "hotfix", "firmware", "driver update",
    # Press/official language
    "press release", "official statement", "partnership", "sponsorship",
    "acquisition", "merger", "signs deal", "exclusive",
    # Series/racing official language
    "race results", "championship standings", "official results",
    "FIA confirms", "series announces", "regulation",
]

COMMUNITY_KEYWORDS = [
    "review", "opinion", "guide", "tutorial", "setup guide", "how to",
    "best", "worst", "ranked", "tier list", "comparison", "vs",
    "discussion", "reddit", "community", "fan", "modding", "mod release",
]

# Source type display labels (for brief and dashboard)
SOURCE_TYPE_LABELS = {
    "hardware":  "🔧 HARDWARE",
    "simulator": "🎮 SIMULADOR",
    "media":     "📰 MEDIA",
    "series":    "🏆 SÉRIE",
    "community": "💬 COMUNIDADE",
    "esports":   "🎯 ESPORTS",
}

OFFICIAL_BADGE = "🟢 OFICIAL"
UNOFFICIAL_BADGE = "⚪ NÃO OFICIAL"

CATEGORY_WEIGHTS = {
    "sim_racing":  0.60,
    "motorsport":  0.20,
    "truck":       0.15,
    "farming":     0.05,
}

# FIX 2026-05-11: alinhar garantias com a nova distribuição editorial.
GUARANTEE_CATEGORIES = {
    "sim_racing":  6,   # minimum 6 sim racing articles per brief
    "motorsport":  2,   # minimum 2 motorsport articles
    "truck":       2,   # minimum 2 truck articles
    "farming":     1,   # minimum 1 farming article
}
GUARANTEE_PORTUGAL = True
MAX_PER_SOURCE = 3  # Máximo de artigos por fonte no top 15
MAX_PER_SOURCE_YOUTUBE = 1  # Máximo de artigos por canal YouTube por brief

# Geração de social cards (requer Pillow + assets/)
# Mudar para True depois de colocar fontes e logo em assets/
GENERATE_IMAGES = False

# --- Email digest delivery ---
SEND_EMAIL_DIGEST = False   # mudar para True quando SMTP estiver configurado

EMAIL_SMTP_HOST = ""
EMAIL_SMTP_PORT = 587
EMAIL_SMTP_USER = ""
EMAIL_SMTP_PASSWORD = ""
EMAIL_FROM = ""
EMAIL_TO = ""

EMAIL_ATTACH_MARKDOWN = True
EMAIL_ATTACH_CARDS = True

# Criar pastas se não existirem
for d in [LOG_DIR, ARCHIVE_DIR, OUTPUT_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)
