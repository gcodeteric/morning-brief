"""SimulaNewsMachine — Lista completa de RSS feeds."""

import json
from pathlib import Path

# =============================================================================
# FEEDS ESTÁTICOS — todos os feeds confirmados
# =============================================================================

FEEDS = [
    # =========================================================================
    # TIER 1 — Sim Racing News (priority 8-10)
    # =========================================================================
    {"url": "https://traxion.gg/feed/", "cat": "sim_racing", "p": 10, "name": "Traxion.GG"},
    {"url": "https://overtake.gg/news/index.rss", "cat": "sim_racing", "p": 10, "name": "OverTake.gg"},
    {"url": "https://boxthislap.org/feed/", "cat": "sim_racing", "p": 10, "name": "BoxThisLap"},
    {"url": "https://bsimracing.com/feed/", "cat": "sim_racing", "p": 9, "name": "BSIMRacing"},
    {"url": "https://racesimcentral.net/feed/", "cat": "sim_racing", "p": 9, "name": "Race Sim Central"},
    {"url": "https://simracingsetup.com/feed/", "cat": "sim_racing", "p": 8, "name": "SimRacingSetup"},
    {"url": "https://simracingcockpit.gg/feed/", "cat": "sim_racing", "p": 8, "name": "SimRacingCockpit.gg"},
    {"url": "https://racinggames.gg/feed/atom/", "cat": "racing_games", "p": 8, "name": "RacingGames.gg"},

    # =========================================================================
    # TIER 1 — Sim Official Blogs (priority 7-10)
    # =========================================================================
    {"url": "https://www.iracing.com/feed/", "cat": "sim_racing", "p": 10, "name": "iRacing News"},
    {"url": "https://www.assettocorsa.gg/feed/", "cat": "sim_racing", "p": 9, "name": "Kunos AC EVO"},
    {"url": "https://www.studio-397.com/feed/", "cat": "sim_racing", "p": 8, "name": "Studio 397 LMU"},
    {"url": "https://www.beamng.com/blog/index.rss", "cat": "sim_racing", "p": 7, "name": "BeamNG Blog"},
    {"url": "https://forum.reizastudios.com/forums/-/index.rss", "cat": "sim_racing", "p": 7, "name": "Reiza Forum"},
    {"url": "https://rennsport.gg/feed/", "cat": "sim_racing", "p": 7, "name": "Rennsport"},
    {"url": "https://www.raceroomracingexperience.com/news/feed/", "cat": "sim_racing", "p": 6, "name": "RaceRoom"},

    # =========================================================================
    # TIER 1 — Nostalgia Official (priority 7-10)
    # =========================================================================
    {"url": "https://blog.scssoft.com/feeds/posts/default?alt=rss", "cat": "nostalgia", "p": 10, "name": "SCS Software Blog"},
    # REMOVIDO: GIANTS Software feed inactivo em 2026
    {"url": "https://simulatornews.com/feed/", "cat": "nostalgia", "p": 8, "name": "SimulatorNews"},
    # REMOVIDO: Flightsim.to feed inactivo em 2026

    # =========================================================================
    # TIER 1 — Motorsport Real (priority 7-9)
    # =========================================================================
    {"url": "https://www.motorsport.com/rss/all/news/", "cat": "motorsport", "p": 9, "name": "Motorsport.com"},
    {"url": "https://www.autosport.com/rss/feed/all", "cat": "motorsport", "p": 8, "name": "Autosport"},
    {"url": "https://the-race.com/feed/", "cat": "motorsport", "p": 8, "name": "The Race"},
    {"url": "https://racer.com/feed/", "cat": "motorsport", "p": 7, "name": "RACER"},

    # =========================================================================
    # TIER 1 — Racing Games (priority 6-9)
    # =========================================================================
    {"url": "https://gtplanet.net/feed/", "cat": "racing_games", "p": 9, "name": "GTPlanet"},
    {"url": "https://dirtfish.com/feed/", "cat": "racing_games", "p": 6, "name": "DirtFish"},

    # =========================================================================
    # TIER 2 — Secondary (priority 4-7)
    # =========================================================================
    {"url": "https://ocracing.com/feed/", "cat": "sim_racing", "p": 6, "name": "OC Racing"},
    {"url": "https://boostedmedia.net/feed/", "cat": "hardware", "p": 7, "name": "Boosted Media"},
    {"url": "https://coachdaveacademy.com/feed/", "cat": "sim_racing", "p": 6, "name": "Coach Dave Academy"},
    {"url": "https://blog.gridfinder.com/feed/", "cat": "community", "p": 5, "name": "Grid Finder Blog"},
    # {"url": "https://simrace247.com/feed/", "cat": "sim_racing", "p": 6, "name": "SimRace247"},
    {"url": "https://onlineracedriver.com/feed/", "cat": "sim_racing", "p": 5, "name": "OnlineRaceDriver"},
    {"url": "https://isrtv.com/feed/", "cat": "sim_racing", "p": 5, "name": "Inside Sim Racing"},
    {"url": "https://simracing-pc.de/en/feed/", "cat": "hardware", "p": 5, "name": "SimRacing-PC"},
    # {"url": "https://randomcallsign.com/blog-feed.xml", "cat": "sim_racing", "p": 6, "name": "Random Callsign"},
    {"url": "https://apexsimracing.com/blogs/sim-racing-blog.atom", "cat": "hardware", "p": 5, "name": "Apex Sim Racing"},
    {"url": "https://vco-esports.com/feed/", "cat": "esports", "p": 6, "name": "VCO Esports"},
    {"url": "https://simracing.gp/sgp-blog/feed/", "cat": "community", "p": 5, "name": "SimRacing.GP"},
    # {"url": "https://simracingdeal.com/feed/", "cat": "deals", "p": 5, "name": "SimRacingDeal"},
    {"url": "https://www.drivingitalia.net/feed/?lang=en", "cat": "sim_racing", "p": 4, "name": "DrivingItalia"},
    # {"url": "https://vracingnews.de/feed/", "cat": "sim_racing", "p": 4, "name": "vRacingnews DE"},
    {"url": "https://fanatec.com/eu-en/racing-hardware/blog/feed/", "cat": "hardware", "p": 7, "name": "Fanatec Blog"},
    {"url": "https://en.mozaracing.com/blogs/news.atom", "cat": "hardware", "p": 7, "name": "MOZA Blog"},
    # REMOVIDO: FlightSim.com feed inactivo em 2026
    {"url": "https://msfsaddons.com/feed/", "cat": "nostalgia", "p": 5, "name": "MSFS Addons"},

    # =========================================================================
    # TIER 3 — YouTube RSS (channel_id confirmados)
    # =========================================================================
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCq-ylUNa9RoTK5jr6TBOYag", "cat": "sim_racing", "p": 8, "name": "Jimmy Broadbent"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCH9Z2uxY1Rlij3Pez4omyeA", "cat": "hardware", "p": 8, "name": "Boosted Media YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCnwafXeJvjNzMttB1ptFPnQ", "cat": "sim_racing", "p": 7, "name": "Dave Cam"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtbLA0YM6EpwUQhFUyPQU9Q", "cat": "sim_racing", "p": 7, "name": "Driver61"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCh4oMCJNapF8bSoSXTyxlWg", "cat": "sim_racing", "p": 7, "name": "Chris Haye"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCqnakdO0DZ7w3ne7-EmaW7w", "cat": "sim_racing", "p": 6, "name": "The Simpit"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC69aRMKDNmaruRhBQ-_wyqw", "cat": "sim_racing", "p": 6, "name": "GamerMuscle"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC1hoWeqSuf03UgeABeR2U3g", "cat": "sim_racing", "p": 6, "name": "Random Callsign YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC7WNZQb14M9X6whT6WMsWoQ", "cat": "racing_games", "p": 7, "name": "Tiametmarduk"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC-46hTnlyW3aCwjHs2acDzg", "cat": "racing_games", "p": 7, "name": "aarava"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC3Xu9GSp5-yVa1ck91SjRWA", "cat": "racing_games", "p": 7, "name": "SLAPTrain"},

    # =========================================================================
    # TIER 3 — Nostalgia YT (channel_id confirmados)
    # =========================================================================
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCSeb5KSN6BC1c0WwEjUzM_A", "cat": "nostalgia", "p": 6, "name": "Squirrel YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCQ8k8yTDLITldfWYKDs3xFg", "cat": "nostalgia", "p": 6, "name": "Daggerwin YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCOkhQewmm48tEpk9x9hwdSw", "cat": "nostalgia", "p": 6, "name": "MrSealyP YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCEodFwnfPXdkzVPJZmuzAIg", "cat": "nostalgia", "p": 6, "name": "C.W. Lemoine YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtiq6FTXiFKQm-wqMuRijgA", "cat": "nostalgia", "p": 6, "name": "ObsidianAnt YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC6zzlBIwNS9GJZZ3rBx_WhQ", "cat": "nostalgia", "p": 6, "name": "Hudson's Playground YT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCAILTiWNai7Y2zsO8ECFxcA", "cat": "nostalgia", "p": 6, "name": "320 Sim Pilot YT"},

    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCPUDe8-YI3gc7SQrxRL75ng", "cat": "portugal", "p": 8, "name": "eSimRacing PT"},
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCTkR43EyS8y7d_uyd9rqu2A", "cat": "portugal", "p": 8, "name": "SimRacing Portugal"},
]

# =============================================================================
# CANAIS YOUTUBE PARA EXTRAIR (channel_id_extractor.py)
# Após extracção, ficam em data/extracted_channel_ids.json
# =============================================================================

YOUTUBE_CHANNELS_TO_EXTRACT = [
    {"handle": "https://www.youtube.com/@traxiongg", "name": "Traxion.GG YT", "cat": "sim_racing", "p": 8},
    {"handle": "https://www.youtube.com/c/SuperGT", "name": "Super GT", "cat": "sim_racing", "p": 8},
    {"handle": "https://www.youtube.com/c/SimRacingGarage", "name": "Sim Racing Garage", "cat": "hardware", "p": 8},
    {"handle": "https://www.youtube.com/c/Kireth", "name": "Kireth", "cat": "sim_racing", "p": 7},
    {"handle": "https://www.youtube.com/@blackpanthaa", "name": "BlackPanthaa", "cat": "racing_games", "p": 7},
    {"handle": "https://www.youtube.com/user/AR12Gaming", "name": "AR12Gaming", "cat": "racing_games", "p": 7},
    {"handle": "https://www.youtube.com/@failrace", "name": "FailRace", "cat": "racing_games", "p": 7},
    {"handle": "https://www.youtube.com/@benjamindaly300", "name": "Benjamin Daly", "cat": "sim_racing", "p": 7},
    {"handle": "https://www.youtube.com/user/NorthernAlexUK", "name": "Squirrel", "cat": "nostalgia", "p": 6},
    {"handle": "https://www.youtube.com/@Daggerwin", "name": "Daggerwin", "cat": "nostalgia", "p": 6},
    {"handle": "https://www.youtube.com/@DjGoHamGaming", "name": "DjGoHam", "cat": "nostalgia", "p": 5},
    {"handle": "https://www.youtube.com/@HudsonsPlaygroundGaming", "name": "Hudson's Playground", "cat": "nostalgia", "p": 5},
    {"handle": "https://www.youtube.com/@MrSealyP", "name": "MrSealyP", "cat": "nostalgia", "p": 6},
    {"handle": "https://www.youtube.com/@CWLemoine", "name": "C.W. Lemoine", "cat": "nostalgia", "p": 6},
    {"handle": "https://www.youtube.com/@ObsidianAnt", "name": "ObsidianAnt", "cat": "nostalgia", "p": 6},
    {"handle": "https://www.youtube.com/@320SimPilot", "name": "320 Sim Pilot", "cat": "nostalgia", "p": 6},
    {"handle": "https://www.youtube.com/@MajorTom.", "name": "MajorTom", "cat": "nostalgia", "p": 5},
    {"handle": "https://www.youtube.com/@ErminHamidovic", "name": "Ermin Hamidovic", "cat": "nostalgia", "p": 5},
    {"handle": "https://www.youtube.com/@DanSuzuki", "name": "Dan Suzuki", "cat": "sim_racing", "p": 6},
    {"handle": "https://www.youtube.com/@iRacingOfficial", "name": "iRacing Official YT", "cat": "sim_racing", "p": 8},
    {"handle": "https://www.youtube.com/@ThatSimRacingBloke", "name": "That Sim Racing Bloke", "cat": "sim_racing", "p": 6},
    {"handle": "https://www.youtube.com/user/ReizaStudios", "name": "Reiza Studios YT", "cat": "sim_racing", "p": 7},
]


def get_all_feeds():
    """Retorna todos os feeds: estáticos + dinâmicos (do extracted_channel_ids.json)."""
    all_feeds = list(FEEDS)

    # Carregar feeds dinâmicos extraídos pelo channel_id_extractor.py
    extracted_file = Path(__file__).resolve().parent / "data" / "extracted_channel_ids.json"
    if extracted_file.exists():
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                extracted = json.load(f)
            for entry in extracted:
                if entry.get("channel_id"):
                    all_feeds.append({
                        "url": f"https://www.youtube.com/feeds/videos.xml?channel_id={entry['channel_id']}",
                        "cat": entry.get("cat", "sim_racing"),
                        "p": entry.get("p", 5),
                        "name": entry.get("name", "YouTube Channel"),
                    })
        except Exception:
            pass  # Se falhar, continuar sem os feeds dinâmicos

    return all_feeds
