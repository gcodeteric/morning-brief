"""
SimulaNewsMachine — Extractor de Channel IDs do YouTube via yt-dlp.

Corre uma vez: python channel_id_extractor.py
Requer: pip install yt-dlp (adicionar ao requirements.txt)
Guarda resultados em data/extracted_channel_ids.json
"""

import json
import sys
import time
from pathlib import Path

from feeds import YOUTUBE_CHANNELS_TO_EXTRACT

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "extracted_channel_ids.json"


def extract_channel_id_yt_dlp(url):
    """Extrai channel_id usando yt-dlp (sem fazer download, só metadata)."""
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlist_items": "1",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # yt-dlp devolve channel_id directamente
            channel_id = info.get("channel_id") or info.get("uploader_id")
            if channel_id and channel_id.startswith("UC"):
                return channel_id
            # Fallback: tentar no primeiro entry se for playlist
            entries = info.get("entries", [])
            first = next(iter(entries), None)
            if first:
                cid = first.get("channel_id") or first.get("uploader_id")
                if cid and cid.startswith("UC"):
                    return cid
        return None
    except Exception as e:
        print(f"   ERRO yt-dlp: {e}")
        return None


def main():
    # Verificar se yt-dlp está instalado
    try:
        import yt_dlp
    except ImportError:
        print("ERRO: yt-dlp não está instalado.")
        print("Instalar com: pip install yt-dlp")
        return 1

    print("=" * 60)
    print("SimulaNewsMachine — YouTube Channel ID Extractor (yt-dlp)")
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

        channel_id = extract_channel_id_yt_dlp(url)

        if channel_id:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            print(f"   OK → {channel_id}")
            ok_count += 1
            results.append({
                "name": name,
                "handle": url,
                "channel_id": channel_id,
                "cat": channel.get("cat", "sim_racing"),
                "p": channel.get("p", 5),
                "rss_url": rss_url,
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

        if i < len(YOUTUBE_CHANNELS_TO_EXTRACT):
            time.sleep(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"RESULTADO: {ok_count} OK | {fail_count} FALHOU")
    print(f"Guardado em: {OUTPUT_FILE}")
    print("=" * 60)

    if fail_count > 0:
        print()
        print("Canais que falharam:")
        for r in results:
            if r["status"] == "FALHOU":
                print(f"  - {r['name']}: {r['handle']}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
