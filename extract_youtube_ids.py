"""
Extract YouTube Channel IDs (UC...) from @handles.
Usage: python extract_youtube_ids.py
Output: youtube_channel_ids.csv
"""

import re
import time
import csv
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# Canais com UC já confirmado — incluídos directamente
CONFIRMED = [
    ("Jimmy Broadbent",       "UCq-ylUNa9RoTK5jr6TBOYag"),
    ("Boosted Media",         "UCH9Z2uxY1Rlij3Pez4omyeA"),
    ("Dave Cam",              "UCnwafXeJvjNzMttB1ptFPnQ"),
    ("Driver61",              "UCtbLA0YM6EpwUQhFUyPQU9Q"),
    ("Chris Haye",            "UCh4oMCJNapF8bSoSXTyxlWg"),
    ("Sim Racing Garage",     "UCT_50ZiRFWSm7oziV1OZloQ"),
    ("Super GT",              "UC-sJ8u8eu_ivfzekwkue38g"),
    ("The Simpit",            "UCqnakdO0DZ7w3ne7-EmaW7w"),
    ("GamerMuscle",           "UC69aRMKDNmaruRhBQ-_wyqw"),
    ("iRacing Official",      "UCHy30iiRnjv1uLRSo0MC2fA"),
    ("Random Callsign",       "UC1hoWeqSuf03UgeABeR2U3g"),
    ("Karl Gosling",          "UCSnP7yd5lIbrLW_nTqAc9xA"),
    ("Jardier",               "UCQyjqyKpJfD7BmJb37ABLyw"),
    ("BlackPanthaa",          "UCS5_PRRahw4GFaJ0z2TmFfA"),
]

# Canais que precisam de extracção via página
TO_EXTRACT = [
    ("Traxion.GG",             "https://www.youtube.com/@TraxionGG"),
    ("That Sim Racing Bloke",  "https://www.youtube.com/@ThatSimRacingBloke"),
    ("Ermin Hamidovic",        "https://www.youtube.com/@ErminHamidovic"),
    ("Sim Racing Corner",      "https://www.youtube.com/@SimRacingCorner"),
    ("Dan Suzuki",             "https://www.youtube.com/@DanSuzuki"),
    ("Kireth",                 "https://www.youtube.com/@Kireth"),
    ("Inside Sim Racing",      "https://www.youtube.com/@InsideSimRacing"),
    ("Tiametmarduk",           "https://www.youtube.com/@Tiametmarduk"),
    ("Aarava",                 "https://www.youtube.com/@Aarava"),
    ("AR12Gaming",             "https://www.youtube.com/@AR12Gaming"),
    ("FailRace",               "https://www.youtube.com/user/FailRace"),
    ("SLAPTrain",              "https://www.youtube.com/@SLAPTrain"),
    ("Benjamin Daly",          "https://www.youtube.com/@BenjaminDaly"),
    ("Squirrel",               "https://www.youtube.com/@SquirrelPlaysGames"),
    ("Daggerwin",              "https://www.youtube.com/@Daggerwin"),
    ("DjGoHam Gaming",         "https://www.youtube.com/@DjGoHamGaming"),
    ("Hudson's Playground",    "https://www.youtube.com/@HudsonsPlayground"),
    ("MrSealyP",               "https://www.youtube.com/@MrSealyP"),
    ("C.W. Lemoine",           "https://www.youtube.com/@CWLemoine"),
    ("ObsidianAnt",            "https://www.youtube.com/@ObsidianAnt"),
    ("320 Sim Pilot",          "https://www.youtube.com/@320SimPilot"),
    ("MajorTom",               "https://www.youtube.com/@MajorTomGaming"),
    ("eSimRacing PT",          "https://www.youtube.com/@eSimRacing"),
    ("Reiza Studios",          "https://www.youtube.com/@ReizaStudios"),
]

RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id="


def extract_channel_id(url: str) -> str | None:
    """Fetch YouTube page and extract channelId from embedded JSON."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        # YouTube embeds channelId in multiple places in the page JS
        patterns = [
            r'"channelId":"(UC[^"]{22})"',
            r'"externalChannelId":"(UC[^"]{22})"',
            r'channel_id=(UC[^&"]{22})',
        ]
        for pattern in patterns:
            match = re.search(pattern, r.text)
            if match:
                return match.group(1)
    except requests.RequestException as e:
        print(f"  ERROR fetching {url}: {e}")
    return None


def build_rss(channel_id: str) -> str:
    return f"{RSS_BASE}{channel_id}"


def main():
    results = []

    # 1. Add confirmed channels directly
    print("=== Confirmed channels ===")
    for name, cid in CONFIRMED:
        rss = build_rss(cid)
        results.append({"name": name, "channel_id": cid, "rss": rss, "status": "confirmed"})
        print(f"  ✅ {name}: {cid}")

    # 2. Extract remaining channels
    print("\n=== Extracting from pages ===")
    for name, url in TO_EXTRACT:
        print(f"  Fetching {name} ...", end=" ", flush=True)
        cid = extract_channel_id(url)
        if cid:
            rss = build_rss(cid)
            results.append({"name": name, "channel_id": cid, "rss": rss, "status": "extracted"})
            print(f"✅ {cid}")
        else:
            results.append({"name": name, "channel_id": "NOT_FOUND", "rss": "", "status": "failed"})
            print("❌ not found")
        time.sleep(1.5)  # polite rate limiting

    # 3. Write CSV
    output_file = "youtube_channel_ids.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "channel_id", "rss", "status"])
        writer.writeheader()
        writer.writerows(results)

    # 4. Summary
    confirmed = sum(1 for r in results if r["status"] in ("confirmed", "extracted"))
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\n✅ {confirmed} canais com ID | ❌ {failed} falhados")
    print(f"📄 Output: {output_file}")

    # 5. Print failed ones for manual lookup
    if failed:
        print("\nCanais que precisam de verificação manual:")
        for r in results:
            if r["status"] == "failed":
                print(f"  - {r['name']}")


if __name__ == "__main__":
    main()
