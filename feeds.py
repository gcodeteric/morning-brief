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
    # REMOVIDO 2026-05-11: 403 Forbidden (confirmed by Perplexity HTTP check)
    # {"url": "https://traxion.gg/feed/", "cat": "sim_racing", "p": 10, "name": "Traxion.GG", "official": False, "source_type": "media"},
    {"url": "https://overtake.gg/news/index.rss", "cat": "sim_racing", "p": 10, "name": "OverTake.gg", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://boxthislap.org/feed/", "cat": "sim_racing", "p": 10, "name": "BoxThisLap", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://bsimracing.com/feed/", "cat": "sim_racing", "p": 9, "name": "BSIMRacing", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://racesimcentral.net/feed/", "cat": "sim_racing", "p": 9, "name": "Race Sim Central", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://simracingsetup.com/feed/", "cat": "sim_racing", "p": 8, "name": "SimRacingSetup", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://simracingcockpit.gg/feed/", "cat": "sim_racing", "p": 8, "name": "SimRacingCockpit.gg", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    # {"url": "https://racinggames.gg/feed/atom/", "cat": "racing_games", "p": 8, "name": "RacingGames.gg"},

    # =========================================================================
    # TIER 1 — Sim Official Blogs (priority 7-10)
    # =========================================================================
    {"url": "https://www.iracing.com/feed/", "cat": "sim_racing", "p": 10, "name": "iRacing News", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    {"url": "https://www.assettocorsa.gg/feed/", "cat": "sim_racing", "p": 9, "name": "Kunos AC EVO", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    {"url": "https://www.studio-397.com/feed/", "cat": "sim_racing", "p": 8, "name": "Studio 397 LMU", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    # {"url": "https://www.beamng.com/blog/index.rss", "cat": "sim_racing", "p": 7, "name": "BeamNG Blog"},
    {"url": "https://forum.reizastudios.com/forums/-/index.rss", "cat": "sim_racing", "p": 7, "name": "Reiza Forum", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    {"url": "https://rennsport.gg/feed/", "cat": "sim_racing", "p": 7, "name": "Rennsport", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    # {"url": "https://www.raceroomracingexperience.com/news/feed/", "cat": "sim_racing", "p": 6, "name": "RaceRoom"},

    # =========================================================================
    # TIER 1 — Nostalgia Official (priority 7-10)
    # =========================================================================
    {"url": "https://blog.scssoft.com/feeds/posts/default?alt=rss", "cat": "nostalgia", "p": 10, "name": "SCS Software Blog", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    # REMOVIDO: GIANTS Software feed inactivo em 2026
    {"url": "https://simulatornews.com/feed/", "cat": "nostalgia", "p": 8, "name": "SimulatorNews", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    # REMOVIDO: Flightsim.to feed inactivo em 2026

    # =========================================================================
    # TIER 1 — Motorsport Real (priority 7-9)
    # =========================================================================
    {"url": "https://www.motorsport.com/rss/all/news/", "cat": "motorsport", "p": 9, "name": "Motorsport.com", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    # REMOVIDO 2026-05-11: 500 Server Error (unreliable)
    # {"url": "https://www.autosport.com/rss/feed/all", "cat": "motorsport", "p": 8, "name": "Autosport", "official": False, "source_type": "media"},
    {"url": "https://the-race.com/feed/", "cat": "motorsport", "p": 8, "name": "The Race", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://racer.com/feed/", "cat": "motorsport", "p": 7, "name": "RACER", "official": False, "source_type": "media"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 1 — Racing Games (priority 6-9)
    # =========================================================================
    {"url": "https://gtplanet.net/feed/", "cat": "racing_games", "p": 9, "name": "GTPlanet", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://dirtfish.com/feed/", "cat": "racing_games", "p": 6, "name": "DirtFish", "official": False, "source_type": "media"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 2 — Secondary (priority 4-7)
    # =========================================================================
    {"url": "https://ocracing.com/feed/", "cat": "sim_racing", "p": 6, "name": "OC Racing", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://boostedmedia.net/feed/", "cat": "hardware", "p": 7, "name": "Boosted Media", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://coachdaveacademy.com/feed/", "cat": "sim_racing", "p": 6, "name": "Coach Dave Academy", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://blog.gridfinder.com/feed/", "cat": "community", "p": 5, "name": "Grid Finder Blog", "official": False, "source_type": "community"},  # ADDED 2026-05-11
    # {"url": "https://simrace247.com/feed/", "cat": "sim_racing", "p": 6, "name": "SimRace247"},
    {"url": "https://onlineracedriver.com/feed/", "cat": "sim_racing", "p": 5, "name": "OnlineRaceDriver", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://isrtv.com/feed/", "cat": "sim_racing", "p": 5, "name": "Inside Sim Racing", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://simracing-pc.de/en/feed/", "cat": "hardware", "p": 5, "name": "SimRacing-PC", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    # {"url": "https://randomcallsign.com/blog-feed.xml", "cat": "sim_racing", "p": 6, "name": "Random Callsign"},
    {"url": "https://apexsimracing.com/blogs/sim-racing-blog.atom", "cat": "hardware", "p": 5, "name": "Apex Sim Racing", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://vco-esports.com/feed/", "cat": "esports", "p": 6, "name": "VCO Esports", "official": True, "source_type": "esports"},  # ADDED 2026-05-11
    # {"url": "https://simracing.gp/sgp-blog/feed/", "cat": "community", "p": 5, "name": "SimRacing.GP"},
    # {"url": "https://simracingdeal.com/feed/", "cat": "deals", "p": 5, "name": "SimRacingDeal"},
    # {"url": "https://www.drivingitalia.net/feed/?lang=en", "cat": "sim_racing", "p": 4, "name": "DrivingItalia"},
    # {"url": "https://vracingnews.de/feed/", "cat": "sim_racing", "p": 4, "name": "vRacingnews DE"},
    # {"url": "https://fanatec.com/eu-en/racing-hardware/blog/feed/", "cat": "hardware", "p": 7, "name": "Fanatec Blog"},
    # {"url": "https://en.mozaracing.com/blogs/news.atom", "cat": "hardware", "p": 7, "name": "MOZA Blog"},
    # REMOVIDO: FlightSim.com feed inactivo em 2026
    {"url": "https://msfsaddons.com/feed/", "cat": "nostalgia", "p": 5, "name": "MSFS Addons", "official": False, "source_type": "media"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 2 — Sim Racing Hardware Official
    # =========================================================================
    {"url": "https://simucube.com/blog/feed", "cat": "sim_racing", "p": 7, "name": "Simucube Blog", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://heusinkveld.com/feed", "cat": "sim_racing", "p": 7, "name": "Heusinkveld", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://www.cubecontrols.com/feed", "cat": "sim_racing", "p": 7, "name": "Cube Controls", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://sim-lab.eu/blogs/news.atom", "cat": "sim_racing", "p": 7, "name": "Sim-Lab", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://nextlevelracing.com/news/feed", "cat": "sim_racing", "p": 7, "name": "Next Level Racing", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://trakracer.com/blogs/racing-simulator.atom", "cat": "sim_racing", "p": 7, "name": "Trak Racer", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://mozaracing.com/blogs/news.atom", "cat": "sim_racing", "p": 7, "name": "Moza Racing", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"url": "https://blog.logitech.com/feed", "cat": "sim_racing", "p": 6, "name": "Logitech Blog", "official": True, "source_type": "hardware"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 2 — Sim Racing Simulators Official
    # =========================================================================
    {"url": "https://beamng.com/game/index.xml", "cat": "sim_racing", "p": 7, "name": "BeamNG.drive", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    {"url": "https://www.raceroom.com/en/news/feed", "cat": "sim_racing", "p": 7, "name": "RaceRoom Racing", "official": True, "source_type": "simulator"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 2 — Sim Racing Media
    # =========================================================================
    {"url": "https://simracingcockpit.com/feed", "cat": "sim_racing", "p": 6, "name": "Sim Racing Cockpit", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.gtplanet.net/feed", "cat": "sim_racing", "p": 6, "name": "GTPlanet", "official": False, "source_type": "media"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 2 — Motorsport Official Series and Media
    # =========================================================================
    {"url": "https://www.motorsport.com/rss/all/news", "cat": "motorsport", "p": 8, "name": "Motorsport.com All", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.fia.com/rss/news", "cat": "motorsport", "p": 8, "name": "FIA News", "official": True, "source_type": "series"},  # ADDED 2026-05-11
    {"url": "https://www.indycar.com/news.rss", "cat": "motorsport", "p": 8, "name": "IndyCar", "official": True, "source_type": "series"},  # ADDED 2026-05-11
    {"url": "https://www.motorsport.com/rss/f1/news", "cat": "motorsport", "p": 7, "name": "Motorsport.com F1", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.motorsport.com/rss/wrc/news", "cat": "motorsport", "p": 7, "name": "Motorsport.com WRC", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.motorsport.com/rss/motogp/news", "cat": "motorsport", "p": 7, "name": "Motorsport.com MotoGP", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.motorsport.com/rss/nascar/news", "cat": "motorsport", "p": 7, "name": "Motorsport.com NASCAR", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.motorsport.com/rss/wec/news", "cat": "motorsport", "p": 7, "name": "Motorsport.com WEC", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.motorsport.com/rss/indycar/news", "cat": "motorsport", "p": 7, "name": "Motorsport.com IndyCar", "official": False, "source_type": "media"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 2 — Community Reddit RSS
    # =========================================================================
    {"url": "https://www.reddit.com/r/simracing.rss", "cat": "sim_racing", "p": 5, "name": "Reddit r/simracing", "official": False, "source_type": "community"},  # ADDED 2026-05-11
    {"url": "https://www.reddit.com/r/iRacing.rss", "cat": "sim_racing", "p": 5, "name": "Reddit r/iRacing", "official": False, "source_type": "community"},  # ADDED 2026-05-11
    {"url": "https://www.reddit.com/r/BeamNG.rss", "cat": "sim_racing", "p": 5, "name": "Reddit r/BeamNG", "official": False, "source_type": "community"},  # ADDED 2026-05-11
    {"url": "https://www.reddit.com/r/trucksim.rss", "cat": "truck", "p": 5, "name": "Reddit r/trucksim", "official": False, "source_type": "community"},  # ADDED 2026-05-11
    {"url": "https://www.reddit.com/r/farmingsimulator.rss", "cat": "farming", "p": 5, "name": "Reddit r/farmingsimulator", "official": False, "source_type": "community"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 3 — YouTube RSS (channel_id confirmados)
    # =========================================================================
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCq-ylUNa9RoTK5jr6TBOYag", "cat": "sim_racing", "p": 8, "name": "Jimmy Broadbent", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCH9Z2uxY1Rlij3Pez4omyeA", "cat": "hardware", "p": 8, "name": "Boosted Media YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCnwafXeJvjNzMttB1ptFPnQ", "cat": "sim_racing", "p": 7, "name": "Dave Cam", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtbLA0YM6EpwUQhFUyPQU9Q", "cat": "sim_racing", "p": 7, "name": "Driver61", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCh4oMCJNapF8bSoSXTyxlWg", "cat": "sim_racing", "p": 7, "name": "Chris Haye", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCqnakdO0DZ7w3ne7-EmaW7w", "cat": "sim_racing", "p": 6, "name": "The Simpit", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC69aRMKDNmaruRhBQ-_wyqw", "cat": "sim_racing", "p": 6, "name": "GamerMuscle", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC1hoWeqSuf03UgeABeR2U3g", "cat": "sim_racing", "p": 6, "name": "Random Callsign YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC7WNZQb14M9X6whT6WMsWoQ", "cat": "racing_games", "p": 7, "name": "Tiametmarduk", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC-46hTnlyW3aCwjHs2acDzg", "cat": "racing_games", "p": 7, "name": "aarava", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC3Xu9GSp5-yVa1ck91SjRWA", "cat": "racing_games", "p": 7, "name": "SLAPTrain", "official": False, "source_type": "media"},  # ADDED 2026-05-11

    # =========================================================================
    # TIER 3 — Nostalgia YT (channel_id confirmados)
    # =========================================================================
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCSeb5KSN6BC1c0WwEjUzM_A", "cat": "nostalgia", "p": 6, "name": "Squirrel YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCQ8k8yTDLITldfWYKDs3xFg", "cat": "nostalgia", "p": 6, "name": "Daggerwin YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCOkhQewmm48tEpk9x9hwdSw", "cat": "nostalgia", "p": 6, "name": "MrSealyP YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCEodFwnfPXdkzVPJZmuzAIg", "cat": "nostalgia", "p": 6, "name": "C.W. Lemoine YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCtiq6FTXiFKQm-wqMuRijgA", "cat": "nostalgia", "p": 6, "name": "ObsidianAnt YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC6zzlBIwNS9GJZZ3rBx_WhQ", "cat": "nostalgia", "p": 6, "name": "Hudson's Playground YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCAILTiWNai7Y2zsO8ECFxcA", "cat": "nostalgia", "p": 6, "name": "320 Sim Pilot YT", "official": False, "source_type": "media"},  # ADDED 2026-05-11

    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCPUDe8-YI3gc7SQrxRL75ng", "cat": "portugal", "p": 8, "name": "eSimRacing PT", "official": False, "source_type": "community"},  # ADDED 2026-05-11
    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCTkR43EyS8y7d_uyd9rqu2A", "cat": "portugal", "p": 8, "name": "SimRacing Portugal", "official": False, "source_type": "community"},  # ADDED 2026-05-11
]

# =============================================================================
# CANAIS YOUTUBE PARA EXTRAIR (channel_id_extractor.py)
# Após extracção, ficam em data/extracted_channel_ids.json
# =============================================================================

YOUTUBE_CHANNELS_TO_EXTRACT = [
    {"handle": "https://www.youtube.com/@traxiongg", "name": "Traxion.GG YT", "cat": "sim_racing", "p": 8, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/c/SuperGT", "name": "Super GT", "cat": "sim_racing", "p": 8, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/c/SimRacingGarage", "name": "Sim Racing Garage", "cat": "hardware", "p": 8, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/c/Kireth", "name": "Kireth", "cat": "sim_racing", "p": 7, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@blackpanthaa", "name": "BlackPanthaa", "cat": "racing_games", "p": 7, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/user/AR12Gaming", "name": "AR12Gaming", "cat": "racing_games", "p": 7, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@failrace", "name": "FailRace", "cat": "racing_games", "p": 7, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@benjamindaly300", "name": "Benjamin Daly", "cat": "sim_racing", "p": 7, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/user/NorthernAlexUK", "name": "Squirrel", "cat": "nostalgia", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@Daggerwin", "name": "Daggerwin", "cat": "nostalgia", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@DjGoHamGaming", "name": "DjGoHam", "cat": "nostalgia", "p": 5, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@HudsonsPlaygroundGaming", "name": "Hudson's Playground", "cat": "nostalgia", "p": 5, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@MrSealyP", "name": "MrSealyP", "cat": "nostalgia", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@CWLemoine", "name": "C.W. Lemoine", "cat": "nostalgia", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@ObsidianAnt", "name": "ObsidianAnt", "cat": "nostalgia", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@320SimPilot", "name": "320 Sim Pilot", "cat": "nostalgia", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@MajorTom.", "name": "MajorTom", "cat": "nostalgia", "p": 5, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@ErminHamidovic", "name": "Ermin Hamidovic", "cat": "nostalgia", "p": 5, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@DanSuzuki", "name": "Dan Suzuki", "cat": "sim_racing", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@iRacingOfficial", "name": "iRacing Official YT", "cat": "sim_racing", "p": 8, "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@ThatSimRacingBloke", "name": "That Sim Racing Bloke", "cat": "sim_racing", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/user/ReizaStudios", "name": "Reiza Studios YT", "cat": "sim_racing", "p": 7, "official": True, "source_type": "simulator"},  # ADDED 2026-05-11

    # Hardware brands with no website RSS — YouTube only
    {"handle": "https://www.youtube.com/@Fanatec", "name": "Fanatec YT", "cat": "sim_racing", "p": 7, "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@Thrustmaster", "name": "Thrustmaster YT", "cat": "sim_racing", "p": 7, "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@AsatekSimSports", "name": "Asetek SimSports YT", "cat": "sim_racing", "p": 7, "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@simagic_racing", "name": "Simagic Racing YT", "cat": "sim_racing", "p": 7, "official": True, "source_type": "hardware"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@VRSdirectforcepro", "name": "VRS DirectForce Pro YT", "cat": "sim_racing", "p": 7, "official": True, "source_type": "hardware"},  # ADDED 2026-05-11

    # Sim racing media with no website RSS
    {"handle": "https://www.youtube.com/@OverTakegg", "name": "OverTake.gg YT", "cat": "sim_racing", "p": 7, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@InsideSimRacing", "name": "Inside Sim Racing YT", "cat": "sim_racing", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@simracingpaddock", "name": "Sim Racing Paddock YT", "cat": "sim_racing", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@MoreSideways", "name": "More Sideways YT", "cat": "sim_racing", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@SimHQ", "name": "SimHQ YT", "cat": "sim_racing", "p": 6, "official": False, "source_type": "media"},  # ADDED 2026-05-11

    # Official sim developers with YouTube as primary channel
    {"handle": "https://www.youtube.com/@AssettoCorsaOfficial", "name": "Assetto Corsa Official YT", "cat": "sim_racing", "p": 8, "official": True, "source_type": "simulator"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@RaceRoomRacing", "name": "RaceRoom Racing YT", "cat": "sim_racing", "p": 7, "official": True, "source_type": "simulator"},  # ADDED 2026-05-11

    # Official motorsport series (no RSS — YouTube only)
    {"handle": "https://www.youtube.com/@Formula1", "name": "Formula 1 YT", "cat": "motorsport", "p": 8, "official": True, "source_type": "series"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@FIAWorldEnduranceChampionship", "name": "FIA WEC YT", "cat": "motorsport", "p": 8, "official": True, "source_type": "series"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@WRC", "name": "WRC YT", "cat": "motorsport", "p": 8, "official": True, "source_type": "series"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@MotoGP", "name": "MotoGP YT", "cat": "motorsport", "p": 8, "official": True, "source_type": "series"},  # ADDED 2026-05-11
    {"handle": "https://www.youtube.com/@NASCARHighlights", "name": "NASCAR Highlights YT", "cat": "motorsport", "p": 8, "official": True, "source_type": "series"},  # ADDED 2026-05-11
]


def get_all_feeds():
    """Retorna todos os feeds: estáticos + dinâmicos (do extracted_channel_ids.json)."""
    all_feeds = list(FEEDS)

    # Carregar feeds dinâmicos extraídos pelo channel_id_extractor.py
    extracted_file = Path(__file__).resolve().parent / "data" / "extracted_channel_ids.json"
    if extracted_file.exists():
        try:
            youtube_meta = {entry["handle"]: entry for entry in YOUTUBE_CHANNELS_TO_EXTRACT}  # ADDED 2026-05-11
            with open(extracted_file, "r", encoding="utf-8") as f:
                extracted = json.load(f)
            for entry in extracted:
                if entry.get("channel_id"):
                    seed_meta = youtube_meta.get(entry.get("handle"), {})  # ADDED 2026-05-11
                    all_feeds.append({
                        "url": f"https://www.youtube.com/feeds/videos.xml?channel_id={entry['channel_id']}",
                        "cat": entry.get("cat", "sim_racing"),
                        "p": entry.get("p", 5),
                        "name": entry.get("name", "YouTube Channel"),
                        "official": entry.get("official", seed_meta.get("official", False)),  # ADDED 2026-05-11
                        "source_type": entry.get("source_type", seed_meta.get("source_type", "media")),  # ADDED 2026-05-11
                    })
        except Exception:
            pass  # Se falhar, continuar sem os feeds dinâmicos

    return all_feeds
