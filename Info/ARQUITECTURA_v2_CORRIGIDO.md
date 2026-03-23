# SIMULA PROJECT — Morning Brief Machine v2.0

Arquitectura Definitiva para Claude Code

Março 2026 — Integra 7 Investigações + 500+
Fontes


## VISÃO GERAL
Sistema Python que corre TODAS AS NOITES às 05:00 no Windows PC, varre ~57-79 feeds
operacionais (57 prontos + ~22 via channel_id_extractor.py, escalável para 150+), organiza por relevância, e de manhã entrega ficheiro .md no
Desktop com daily brief + 5 prompts prontos a colar no Claude.

Stack: Python 3.11+ | feedparser | requests | python-dateutil | Windows Task Scheduler
Custo: €0/mês | Output: C:\Users\Bernardo\Desktop\SIMULA_BRIEF_HOJE.md


## ESTRUTURA DO PROJECTO

C:\Users\Bernardo\SimulaNewsMachine\
│
├── main.py                            # Orquestrador — corre tudo em sequência
├── config.py                          # Paths, horários, constantes
├── scanner.py                         # Módulo 1: Lê RSS feeds
├── curator.py                         # Módulo 2: Deduplica, classifica, seleciona
├── formatter.py                       # Módulo 3: Gera .md + prompts
├── feeds.py                           # RSS feeds (57 + dinâmicos do JSON)
├── channel_id_extractor.py            # Extrai YouTube channel_ids (correr 1x)
├── feed_validator.py                  # Testa feeds (1x + manutenção semanal)
├── requirements.txt                   # Dependências
├── setup_scheduler.bat                # Agenda Task Scheduler 05:00
├── README.md                          # Instruções non-coder
├── data\
│    ├── extracted_channel_ids.json # YouTube IDs (gerado pelo extractor)
│    ├── seen_links.json               # Cache cross-dia (evitar repetições)
│    └── run_summary.json              # Status última run (monitorização)
├── logs\
│     ├── YYYY-MM-DD.log                # Log diário
│     └── scheduler.log                 # Log do Task Scheduler
├── archive\
│     └── YYYY-MM-DD_brief.md
└── output\
```
└── latest_brief.md


```
MÓDULO 1: SCANNER (scanner.py)


### Lógica

PARA CADA feed em feeds.py:
```
TENTA ler com feedparser (timeout 10s)
SE ok:
PARA CADA artigo:
SE tem data publicação E publicado nas últimas 28 horas:
GUARDA {title, link, summary[:300], published, source, category, tier}
SE NÃO tem data:
GUARDA com published=None e flag "no_date=True"
(será penalizado no scoring, só incluído se fonte Tier 1)
SE data no futuro:
IGNORA (provavelmente erro de parsing)
SE falhar:
LOG warning, continua (NUNCA parar)
```
RETORNA lista_artigos


### Tratamento de Erros
```
Feed offline → log + continua

Formato estranho → log + continua

Timeout 10s → log + continua

Encoding → force UTF-8 + continua

Artigo sem data → marcar published=None, penalizar -15 no score, só incluir se Tier 1

Artigo com data futura → ignorar silenciosamente

Regra de ouro: o script NUNCA para por causa de 1 feed


```

### Categorias
CATEGORIES = [
```
"sim_racing",         # iRacing, ACC, AC EVO, LMU, BeamNG, AMS2, RaceRoom, Rennsport
"motorsport",         # F1, WEC, NASCAR, MotoGP, Rally, DTM — real
"hardware",           # Fanatec, MOZA, Simagic, Simucube, Heusinkveld, etc.
"nostalgia",          # ETS2, ATS, FS25, MSFS, X-Plane, SnowRunner, SimRail, Bus Sim
"racing_games",       # Forza, NFS, GT7, F1 game, The Crew, WRC, TDU, JDM, drift
"esports",            # Campeonatos, resultados, transfers, prize pools
"community",          # Ligas, eventos, comunidade, Discord
"deals",              # Descontos, promoções, Black Friday
"portugal",           # Tudo PT/IB: FPAK, SRP, retailers, centros, Rally PT
```
]


LISTA COMPLETA DE RSS FEEDS (feeds.py)


## NOTA PARA CLAUDE CODE:
```
Muitos sites expõem RSS em /feed/ , /rss/ , /feed/rss/ , /atom.xml

O script deve ter discover_feed(url) que tenta variações comuns

Se não encontrar RSS, registar como “manual_check” no log

YouTube RSS: youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID

Para channel_ids PARCIAIS, correr channel_id_extractor.py primeiro


```
# feeds.py — TODAS AS FONTES (~57-79 operacionais, escalável para 150+)
# Organizado por Tier (prioridade) e Categoria
# priority: 1-10 (10 = máxima)


FEEDS = {


```
# ═══════════════════════════════════════════════
# TIER 1 — VERIFICAR DIARIAMENTE (priority 8-10)
# ═══════════════════════════════════════════════


# --- Sim Racing News (8 sites) ---
"Traxion.GG":                  {"url": "https://traxion.gg/feed/", "cat": "sim_racing", "p":
"OverTake.gg":                 {"url": "https://www.overtake.gg/news/index.rss", "cat": "sim
"BoxThisLap":                  {"url": "https://boxthislap.org/feed/", "cat": "sim_racing",
"BSIMRacing":                  {"url": "https://www.bsimracing.com/feed/", "cat": "sim_racin
"Race Sim Central":            {"url": "https://racesimcentral.net/feed/", "cat": "sim_racin
"SimRacingSetup":              {"url": "https://simracingsetup.com/feed/", "cat": "sim_racin
"SimRacingCockpit.gg":         {"url": "https://simracingcockpit.gg/feed/", "cat": "sim_raci
```
"RacingGames.gg":           {"url": "https://racinggames.gg/feed/", "cat": "racing_games"


# --- Sim Official Blogs (10 sims) ---
"iRacing News":             {"url": "https://www.iracing.com/feed/", "cat": "sim_racing",
"Kunos AC EVO":             {"url": "https://assettocorsa.gg/feed/", "cat": "sim_racing",
"Studio 397 LMU":           {"url": "https://www.studio-397.com/feed/", "cat": "sim_racin
"BeamNG Blog":              {"url": "https://www.beamng.com/feed/", "cat": "sim_racing",
"Reiza Studios Forum":      {"url": "https://forum.reizastudios.com/forums/-/index.rss",
"Rennsport":                {"url": "https://rennsport.gg/feed/", "cat": "sim_racing", "p
"RaceRoom":                 {"url": "https://raceroomracingexperience.com/feed/", "cat":


# --- Nostalgia Official Blogs (5 sims) ---
"SCS Software Blog":        {"url": "https://blog.scssoft.com/feeds/posts/default?alt=rss
"GIANTS Software News":     {"url": "https://www.farming-simulator.com/feed.php", "cat":
"SimulatorNews":            {"url": "https://simulatornews.com/feed/", "cat": "nostalgia"
"Flightsim.to":             {"url": "https://flightsim.to/feed", "cat": "nostalgia", "p":


# --- Motorsport Real (4 sites) ---
"Motorsport.com":           {"url": "https://www.motorsport.com/rss/all/news/", "cat": "m
"Autosport":                {"url": "https://www.autosport.com/rss/feed/all", "cat": "mot
"The Race":                 {"url": "https://the-race.com/feed/", "cat": "motorsport", "p
"RACER":                    {"url": "https://racer.com/feed/", "cat": "motorsport", "p":


# --- Racing Games Official (5 sites) ---
"GTPlanet":                 {"url": "https://www.gtplanet.net/feed/", "cat": "racing_game
"DirtFish":                 {"url": "https://dirtfish.com/feed/", "cat": "racing_games",


# ═══════════════════════════════════════════════
# TIER 2 — VERIFICAR DIARIAMENTE (priority 5-7)
# ═══════════════════════════════════════════════


# --- Sim Racing Secondary (15 sites) ---
"OC Racing":                {"url": "https://ocracing.com/feed/", "cat": "sim_racing", "p
"Boosted Media":            {"url": "https://boostedmedia.net/feed/", "cat": "hardware",
"Coach Dave Academy":       {"url": "https://coachdaveacademy.com/feed/", "cat": "sim_rac
"Grid Finder Blog":         {"url": "https://blog.gridfinder.com/feed/", "cat": "communit
"SimRace247":               {"url": "https://simrace247.com/feed/", "cat": "sim_racing",
"OnlineRaceDriver":         {"url": "https://onlineracedriver.com/feed/", "cat": "sim_rac
"Inside Sim Racing":        {"url": "https://isrtv.com/feed/", "cat": "sim_racing", "p":
"SimRacing-PC":             {"url": "https://simracing-pc.de/en/feed/", "cat": "hardware"
"Random Callsign":          {"url": "https://www.randomcallsign.com/blog-feed.xml", "cat"
"Apex Sim Racing Blog":     {"url": "https://www.apexsimracing.com/blogs/sim-racing-blog.
"VCO Esports":              {"url": "https://vco-esports.com/feed/", "cat": "esports", "p
"SimRacing.GP Blog":        {"url": "https://www.simracing.gp/sgp-blog/feed", "cat": "com


# --- Deals (2 sites) ---
"SimRacingDeal":            {"url": "https://simracingdeal.com/feed/", "cat": "deals", "p
# --- Regional (3 sites) ---
"DrivingItalia":               {"url": "https://www.drivingitalia.net/feed/", "cat": "sim_ra
"vRacingnews DE":              {"url": "https://vracingnews.de/feed/", "cat": "sim_racing",


# --- Hardware Blogs (verificar RSS) ---
"Fanatec Blog":                {"url": "https://fanatec.com/blog/feed/", "cat": "hardware",
"MOZA Blog":                   {"url": "https://mozaracing.com/blog/feed/", "cat": "hardware


# --- Nostalgia Extra (2 sites) ---
"FlightSim.com":               {"url": "https://www.flightsim.com/feed/", "cat": "nostalgia"
"MSFS Addons":                 {"url": "https://msfsaddons.org/feed/", "cat": "nostalgia", "


# ═══════════════════════════════════════════════
# TIER 3 — YouTube RSS Feeds (50+ canais)
# ═══════════════════════════════════════════════


# --- CONFIRMADOS (channel_id verificado) ---
"YT Jimmy Broadbent":          {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT Boosted Media":            {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT Dave Cam":                 {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT Driver61":                 {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT Chris Haye":               {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT The Simpit":               {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT GamerMuscle":              {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT Random Callsign":          {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT Tiametmarduk":             {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT aarava":                   {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT SLAPTrain":                {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT eSimRacing PT":            {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=
"YT SimRacing Portugal":       {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=


# --- PARCIAIS (carregados de extracted_channel_ids.json) ---
# NÃO editar feeds.py manualmente para adicionar estes.
# Correr channel_id_extractor.py → gera data/extracted_channel_ids.json
# O scanner.py carrega esse JSON e adiciona dinamicamente aos feeds.
# Lista de canais para extrair:
# "YT Traxion.GG":          youtube.com/traxiongg
# "YT Super GT":            youtube.com/c/SuperGT
# "YT Sim Racing Garage":   youtube.com/c/SimRacingGarage
# "YT Kireth":              youtube.com/c/Kireth
# "YT BlackPanthaa":        youtube.com/blackpanthaa
# "YT AR12Gaming":          youtube.com/user/AR12Gaming
# "YT FailRace":            youtube.com/failrace
# "YT Benjamin Daly":       youtube.com/@benjamindaly300
# "YT Squirrel":            youtube.com/user/NorthernAlexUK
# "YT Daggerwin":           youtube.com/@Daggerwin
```
# "YT DjGoHam":                     youtube.com/@DjGoHamGaming
# "YT Hudson Playground":           youtube.com/@HudsonsPlaygroundGaming
# "YT MrSealyP":                    youtube.com/@MrSealyP
# "YT C.W. Lemoine":                youtube.com/@CWLemoine
# "YT ObsidianAnt":                 youtube.com/@ObsidianAnt
# "YT 320 Sim Pilot":               youtube.com/@320SimPilot
# "YT MajorTom":                    youtube.com/@MajorTom.
# "YT Ermin Hamidovic":             youtube.com/@ErminHamidovic
# "YT Dan Suzuki":                  youtube.com/@DanSuzuki
# "YT iRacing Official":            youtube.com/@iRacingOfficial
# "YT That Sim Racing Bloke": youtube.com/@ThatSimRacingBloke
# "YT Reiza Studios":               youtube.com/user/ReizaStudios
```
}


# Função para carregar YouTube feeds extraídos (chamada pelo scanner.py)
def load_extracted_youtube_feeds():
```
"""Carrega channel_ids do JSON e devolve dict compatível com FEEDS."""
import json
from config import EXTRACTED_IDS_FILE
extra = {}
try:
with open(EXTRACTED_IDS_FILE, "r") as f:
data = json.load(f)
for name, info in data.items():
key = f"YT {name}"
extra[key] = {
"url": info["rss"],
"cat": info.get("cat", "sim_racing"),
"p": info.get("p", 6)
}
except FileNotFoundError:
pass       # Ainda não foi extraído — OK, corre sem estes feeds
return extra


```
MÓDULO: CHANNEL ID EXTRACTOR (channel_id_extractor.py)

"""
Extrai channel_id (UC...) de canais YouTube via HTML scraping.
Corre UMA VEZ na instalação. Resultados guardados em data/extracted_channel_ids.json.
O scanner.py carrega este JSON automaticamente — NÃO editar feeds.py manualmente.
"""
import requests, re, time, json


CHANNELS_TO_EXTRACT = [
```
("Traxion.GG",               "https://www.youtube.com/traxiongg"),
("Super GT",                 "https://www.youtube.com/c/SuperGT"),
("Sim Racing Garage",        "https://www.youtube.com/c/SimRacingGarage"),
("Kireth",                   "https://www.youtube.com/c/Kireth"),
("BlackPanthaa",             "https://www.youtube.com/blackpanthaa"),
("AR12Gaming",               "https://www.youtube.com/user/AR12Gaming"),
("FailRace",                 "https://www.youtube.com/failrace"),
("Benjamin Daly",            "https://www.youtube.com/@benjamindaly300"),
("Squirrel",                 "https://www.youtube.com/user/NorthernAlexUK"),
("Daggerwin",                "https://www.youtube.com/@Daggerwin"),
("DjGoHam",                  "https://www.youtube.com/@DjGoHamGaming"),
("Hudson Playground",        "https://www.youtube.com/@HudsonsPlaygroundGaming"),
("MrSealyP",                 "https://www.youtube.com/@MrSealyP"),
("C.W. Lemoine",             "https://www.youtube.com/@CWLemoine"),
("ObsidianAnt",              "https://www.youtube.com/@ObsidianAnt"),
("320 Sim Pilot",            "https://www.youtube.com/@320SimPilot"),
("MajorTom",                 "https://www.youtube.com/@MajorTom."),
("Ermin Hamidovic",          "https://www.youtube.com/@ErminHamidovic"),
("Dan Suzuki",               "https://www.youtube.com/@DanSuzuki"),
("iRacing Official",         "https://www.youtube.com/@iRacingOfficial"),
("That Sim Racing Bloke","https://www.youtube.com/@ThatSimRacingBloke"),
("Reiza Studios",            "https://www.youtube.com/user/ReizaStudios"),
```
]


def extract_channel_id(url):
```
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}
try:
r = requests.get(url, headers=headers, timeout=10)
m = re.search(r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"', r.text)
if m: return m.group(1)
m2 = re.search(r'channel_id=(UC[a-zA-Z0-9_-]{22})', r.text)
if m2: return m2.group(1)
except Exception as e:
print(f"ERRO {url}: {e}")
return None


```
if __name__ == "__main__":
```
results = {}
for name, url in CHANNELS_TO_EXTRACT:
cid = extract_channel_id(url)
rss = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}" if cid else "FALHO
status = "OK" if cid else "FALHOU"
print(f"{status} | {name} | {cid or 'N/A'} | {rss}")
if cid:
results[name] = {"channel_id": cid, "rss": rss}
time.sleep(2)   # Rate limiting
# Guardar resultados com categoria para o scanner usar
with open("data/extracted_channel_ids.json", "w") as f:
json.dump(results, f, indent=2)
print(f"\n{len(results)}/{len(CHANNELS_TO_EXTRACT)} extraídos. Ver data/extracted_channel
print("O scanner.py vai carregar estes feeds automaticamente na próxima run.")


```
MÓDULO: FEED VALIDATOR (feed_validator.py)

"""
Testa TODOS os feeds em feeds.py. Reporta quais funcionam e quais falharam.
Corre UMA VEZ na instalação e depois semanalmente para manutenção.
"""
import feedparser, time
from feeds import FEEDS


if __name__ == "__main__":
```
ok, fail = [], []
for name, cfg in FEEDS.items():
try:
d = feedparser.parse(cfg["url"])
if d.entries:
ok.append((name, len(d.entries)))
print(f"OK   | {name} | {len(d.entries)} artigos")
else:
fail.append((name, "0 artigos"))
print(f"WARN| {name} | 0 artigos (feed vazio ou formato inesperado)")
except Exception as e:
fail.append((name, str(e)))
print(f"FAIL| {name} | {e}")
time.sleep(1)
print(f"\n=== RESUMO ===")
print(f"OK: {len(ok)} feeds | FALHARAM: {len(fail)} feeds")
if fail:
print("\nFeeds a corrigir:")
for name, reason in fail:
print(f"   - {name}: {reason}")


```
MÓDULO 2: CURADOR (curator.py)


### Algoritmo de Relevância v2.1 (Scoring 0-100)

### Deduplicação (antes do scoring)

"""

### Deduplicação em 3+1 camadas:
1. Link canónico: normalizar URL (remover tracking params ?utm_*, www, trailing slash, query strings)
```
Se 2 artigos apontam para o mesmo link canónico → manter o de maior priority
```
2. Título normalizado: lowercase, remover stopwords EN/PT (the, a, an, is, in, de, o, um, etc.), remover pontuação
```
Se 2 títulos normalizados têm >65% de tokens em comum → manter o de maior priority
```
3. Cache cross-dia: manter ficheiro seen_links.json com links dos últimos 3 dias
```
Se link já apareceu num brief anterior → excluir (evita repetição entre dias)
```
"""
# O seen_links.json é actualizado no final de cada run pelo main.py
# Limpar entries com mais de 72h automaticamente


# Keywords por categoria
HIGH_KEYWORDS = {
```json
"hardware_brands": ["moza", "fanatec", "simagic", "simucube", "heusinkveld",
"asetek", "sim-lab", "trak racer", "next level", "logitech",
"thrustmaster", "cube controls", "conspit", "pimax"],
"our_brands": ["moza", "simucube", "sim-lab", "heusinkveld", "akracing"],
"sim_titles": ["iracing", "assetto corsa", "acc", "ac evo", "le mans ultimate",
"beamng", "raceroom", "rennsport", "automobilista", "project motor"],
"nostalgia_titles": ["euro truck", "ets2", "farming simulator", "fs25",
"flight simulator", "msfs", "snowrunner", "simrail",
"x-plane", "bus simulator", "train sim"],
"racing_games": ["forza horizon", "forza motorsport", "need for speed", "nfs",
"gran turismo", "gt7", "f1 24", "f1 25", "f1 game",
"the crew", "wrc", "dirt rally", "test drive unlimited",
"japanese drift master", "grid", "motogp"],
"action_words": ["launch", "release", "update", "patch", "announced", "new",
"review", "comparison", "vs", "deal", "discount", "sale"],
"crossover": ["sim racer", "real driver", "virtual", "esports", "sim-to-real",
"f1 esports", "le mans virtual", "gt world series"],
"portugal": ["portugal", "portuguese", "fpak", "estoril", "portimão",
"torres vedras", "ibéria", "iberian", "simracing portugal"],
```
}


def calculate_relevance(article):
```
score = 0
text = (article["title"] + " " + article["summary"]).lower()


# Base: prioridade do feed (0-30)
score += article["priority"] * 3


# Keywords gerais (+5 cada, max +20)
```
kw_hits = 0
for group in ["hardware_brands", "sim_titles", "action_words"]:
```
for kw in HIGH_KEYWORDS[group]:
if kw in text:
kw_hits += 1
```
score += min(kw_hits * 5, 20)


# Boost: nossas marcas (+10)
for brand in HIGH_KEYWORDS["our_brands"]:
```
if brand in text:
score += 10
break


```
# Boost: Nostalgia (+10)
for title in HIGH_KEYWORDS["nostalgia_titles"]:
```
if title in text:
score += 10
break


```
# Boost: Racing Games (+8)
for game in HIGH_KEYWORDS["racing_games"]:
```
if game in text:
score += 8
break


```
# Boost: Crossover real-sim (+15)
for kw in HIGH_KEYWORDS["crossover"]:
```
if kw in text:
score += 15
break


```
# Boost: Portugal/Ibéria (+12)
for kw in HIGH_KEYWORDS["portugal"]:
```
if kw in text:
score += 12
break


```
# Penalização: conteúdo de baixo valor editorial (-10)
# Nota: "mod release" NÃO é penalizado cegamente — certos mods são notícia
# Só penalizar quando combinado com termos genéricos
low_value_strict = ["livery pack", "skin pack", "reshade preset", "texture mod"]
for lv in low_value_strict:
```
if lv in text:
score -= 10


```
# Penalização: artigo sem data de publicação (-15)
if article.get("no_date"):
```
score -= 15


# Bónus: novidade de fonte pouco recorrente (+5)
# Evita que o brief fique dominado pelas mesmas 5-6 fontes todos os dias
# O curator mantém um contador de "aparições por fonte nos últimos 3 briefs"
# Se a fonte apareceu <2x nos últimos 3 dias → bónus
if article.get("source_rarity_bonus"):
score += 5


return min(score, 100)


```

### Seleção Final
1. Ordenar por score (desc)

2. Garantias de diversidade (mínimo por brief diário):

```
1 notícia Nostalgia

1 notícia hardware (marcas parceiras)

1 notícia motorsport real

1 notícia racing games (Forza/NFS/GT/F1 game)

1 notícia PT/IB (quando disponível)

```
3. Selecionar top 15

4. Marcar top 5 como         destaque


MÓDULO 3: FORMATTER (formatter.py)


### Estrutura do Ficheiro Output

#      SIMULA BRIEF — [DIA], [DATA]
[X] fontes varridas | [Y] artigos novos | [Z] selecionados


---


     TOP 15


     DESTAQUES (1-5)
[título, fonte, resumo, link, score, categoria emoji]
      RESTANTES (6-15)
[título, fonte, link]


---


      DISTRIBUIÇÃO
```
Sim Racing: X |      Motorsport: X |       Hardware: X
Nostalgia: X |     Racing Games: X |        Esports: X
Portugal: X |     Deals: X


```
---


      PROMPTS — COPIAR → COLAR NO CLAUDE


═══ PROMPT 1: INSTAGRAM + X/TWITTER ═══

═══ PROMPT 2: YOUTUBE SHORT ═══

═══ PROMPT 3: YOUTUBE LONGO ═══

═══ PROMPT 4: REDDIT ═══

═══ PROMPT 5: DISCORD ═══


## NOTA LEGAL EM TODOS OS PROMPTS
Cada prompt inclui no final:

REGRAS LEGAIS OBRIGATÓRIAS (Portugal/UE):
- Se mencionares produto cedido: #OFERTA no início
- Se link de afiliado: indicar "link de afiliado"
- Vídeos YouTube com NotebookLLM: incluir na descrição
```
"Este vídeo utiliza narração gerada por inteligência artificial (IA)."
```
- NUNCA inventar claims de performance de hardware não verificados


## PROMPTS PRÉ-FORMATADOS

Os 5 prompts são IDÊNTICOS aos da v1 (já validados) com estas ADIÇÕES:
PROMPT 1 (IG + X): Adicionada regra “pelo menos 1 dos 4 posts deve cobrir racing games
(Forza/NFS/GT/F1) se houver notícia relevante” + nota legal

PROMPT 2 (YT Short): Adicionada linha obrigatória na descrição: “Este vídeo utiliza
narração gerada por inteligência artificial (IA). O conteúdo informativo foi verificado pela
equipa Simula Project.” + tag “AI Voice”

PROMPT 3 (YT Longo): Mesma adição legal + formato inclui agora “Secção Racing Games”
como opção de tema + “Secção Nostalgia” como opção

PROMPT 4 (Reddit): Adicionada sugestão de subreddits racing games (r/ForzaHorizon,
r/needforspeed, r/granturismo, r/F1Game) como alvos além de r/simracing

PROMPT 5 (Discord): Sem alterações

REGRA EDITORIAL EM TODOS OS PROMPTS: Cada prompt inclui a instrução: “Se alguma
das notícias for fraca, redundante, excessivamente promocional ou sem substância
suficiente para gerar valor, responde ‘NÃO PUBLICAR — [motivo]’ em vez de forçar um post.
Melhor não publicar do que publicar lixo.”


RUN SUMMARY (gerado pelo main.py)
No final de cada execução, o main.py gera data/run_summary.json :


{
```json
"started_at": "2026-03-23T05:00:02",
"ended_at": "2026-03-23T05:03:47",
"feeds_total": 90,
"feeds_ok": 84,
"feeds_fail": 6,
"feeds_failed_names": ["Fanatec Blog", "Rennsport", ...],
"articles_scanned": 347,
"articles_new_24h": 52,
"duplicates_removed": 8,
"articles_selected": 15,
"top_sources": ["Traxion.GG", "iRacing News", "SCS Software Blog"],
"categories_distribution": {"sim_racing": 5, "hardware": 3, ...},
"brief_file": "C:\\Users\\Bernardo\\Desktop\\SIMULA_BRIEF_HOJE.md",
"status": "OK"
```
}


Para o Bernardo: abrir data/run_summary.json para ver “o sistema está vivo?” sem abrir
logs.


CONFIG (config.py)

from pathlib import Path


HOME = Path.home()
DESKTOP = HOME / "Desktop"
PROJECT_DIR = HOME / "SimulaNewsMachine"
OUTPUT_FILE = DESKTOP / "SIMULA_BRIEF_HOJE.md"
ARCHIVE_DIR = PROJECT_DIR / "archive"
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR = PROJECT_DIR / "data"


# Ficheiros de estado persistente
SEEN_LINKS_FILE = DATA_DIR / "seen_links.json"         # Cache cross-dia (evitar repetições)
RUN_SUMMARY_FILE = DATA_DIR / "run_summary.json"        # Status da última run (para monitorizaç
EXTRACTED_IDS_FILE = DATA_DIR / "extracted_channel_ids.json"     # YouTube IDs extraídos


SCAN_HOUR = 5
SCAN_MINUTE = 0
HOURS_LOOKBACK = 28
MAX_ARTICLES_OUTPUT = 15
FEED_TIMEOUT_SECONDS = 10
MIN_RELEVANCE_SCORE = 15
SEEN_LINKS_MAX_AGE_HOURS = 72     # Limpar links com mais de 3 dias


# Garantias de diversidade
GUARANTEE_CATEGORIES = {
```json
"nostalgia": 1,
"hardware": 1,
"motorsport": 1,
"racing_games": 1,
```
}
GUARANTEE_PORTUGAL = True


# Criar pastas se não existirem
for d in [LOG_DIR, ARCHIVE_DIR, DATA_DIR]:
```
d.mkdir(parents=True, exist_ok=True)


```

## SETUP WINDOWS


### requirements.txt

feedparser>=6.0.0
requests>=2.28.0
python-dateutil>=2.8.0


### setup_scheduler.bat
@echo off
echo ========================================
echo     SimulaNewsMachine — Configuracao
echo ========================================
echo.


REM Detectar caminho do Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
```batch
echo ERRO: Python nao encontrado no PATH.
echo Instala Python de python.org e marca "Add to PATH".
pause
exit /b 1
```
)


REM Obter caminho absoluto do Python
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i


REM Definir working directory
set WORK_DIR=C:\Users\%USERNAME%\SimulaNewsMachine


REM Criar tarefa com caminho absoluto, working directory, e log redirect
schtasks /create /tn "SimulaNewsMachine" ^
```
/tr "cmd /c cd /d %WORK_DIR% && \"%PYTHON_PATH%\" main.py >> logs\scheduler.log 2>&1" ^
/sc daily /st 05:00 /f


```
echo.
echo Tarefa agendada para as 05:00 todos os dias.
echo Python: %PYTHON_PATH%
echo Pasta: %WORK_DIR%
echo.
echo Para verificar: Task Scheduler ^> SimulaNewsMachine
echo Para testar agora: cd %WORK_DIR% ^&^& python main.py
echo.
pause


### Instalação (README.md)

1. Instalar Python 3.11+ de python.org (marcar "Add to PATH")
2. Abrir cmd
3. cd C:\Users\[USER]\SimulaNewsMachine
4. pip install -r requirements.txt
5. python channel_id_extractor.py     (extrair YouTube channel IDs)
6. python feed_validator.py     (testar feeds)
7. python main.py     (testar manualmente)
8. Verificar SIMULA_BRIEF_HOJE.md no Desktop
9. setup_scheduler.bat    (agendar para 05:00)


ROTINA DIÁRIA (15-20 min)

07:00 — Abrir SIMULA_BRIEF_HOJE.md
07:02 — Copiar PROMPT 1 → Claude → 4 posts IG+X → Buffer (3 min)
07:06 — Copiar PROMPT 4 → Claude → 2 posts Reddit → publicar (2 min)
07:09 — Copiar PROMPT 5 → Claude → Discord #notícias (1 min)

## 07:10 — FEITO.


SEMANAL (30 min extra):
- PROMPT 2 → Claude → YT Short script → gravar + NotebookLLM
- PROMPT 3 → Claude → YT Longo script → gravar + NotebookLLM
