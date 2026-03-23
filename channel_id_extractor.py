"""
SimulaNewsMachine — Extractor de Channel IDs do YouTube.

Corre uma vez: python channel_id_extractor.py
Visita cada URL de canal YouTube e extrai o channelId via regex do HTML.
Guarda resultados em data/extracted_channel_ids.json
"""

import json
import re
import time
import sys
from pathlib import Path

import requests

from feeds import YOUTUBE_CHANNELS_TO_EXTRACT

DATA_DIR = Path.home() / "SimulaNewsMachine" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "extracted_channel_ids.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Padrões regex para encontrar channel ID no HTML do YouTube
CHANNEL_ID_PATTERNS = [
    r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"',
    r'"externalId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"',
    r'channel_id=(UC[a-zA-Z0-9_-]{22})',
    r'/channel/(UC[a-zA-Z0-9_-]{22})',
    r'"browse_id"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"',
]


def extract_channel_id(url):
    """Tenta extrair o channel ID de uma página YouTube."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text

        for pattern in CHANNEL_ID_PATTERNS:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        return None
    except Exception as e:
        print(f"   ERRO ao aceder: {e}")
        return None


def main():
    print("=" * 60)
    print("SimulaNewsMachine — YouTube Channel ID Extractor")
    print("=" * 60)
    print()

    results = []
    ok_count = 0
    fail_count = 0

    for i, channel in enumerate(YOUTUBE_CHANNELS_TO_EXTRACT, 1):
        name = channel["name"]
        url = channel["handle"]
        print(f"[{i}/{len(YOUTUBE_CHANNELS_TO_EXTRACT)}] {name}")
        print(f"   URL: {url}")

        channel_id = extract_channel_id(url)

        if channel_id:
            print(f"   OK → {channel_id}")
            ok_count += 1
            results.append({
                "name": name,
                "handle": url,
                "channel_id": channel_id,
                "cat": channel.get("cat", "sim_racing"),
                "p": channel.get("p", 5),
                "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
                "status": "OK",
            })
        else:
            print(f"   FALHOU — channel_id não encontrado")
            fail_count += 1
            results.append({
                "name": name,
                "handle": url,
                "channel_id": None,
                "cat": channel.get("cat", "sim_racing"),
                "p": channel.get("p", 5),
                "rss_url": None,
                "status": "FALHOU",
            })

        # Sleep entre requests para não ser bloqueado
        if i < len(YOUTUBE_CHANNELS_TO_EXTRACT):
            time.sleep(2)

    # Guardar resultados
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"RESULTADO: {ok_count} OK | {fail_count} FALHOU")
    print(f"Guardado em: {OUTPUT_FILE}")
    print("=" * 60)

    if fail_count > 0:
        print()
        print("Canais que falharam (verificar manualmente):")
        for r in results:
            if r["status"] == "FALHOU":
                print(f"  - {r['name']}: {r['handle']}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
