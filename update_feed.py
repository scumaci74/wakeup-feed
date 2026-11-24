#!/usr/bin/env python3
"""Feed RSS personale non ufficiale di Wake Up (Repubblica).

Sorgente: JSON pubblico della rubrica. Nessuna credenziale o sessione richiesta.
Conserva gli episodi gia' pubblicati; evita modifiche se non ci sono novita'.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
import sys
import xml.etree.ElementTree as ET

import requests

SOURCE_PAGE = (
    "https://www.repubblica.it/rubriche/wake-up/2026/11/23/rubrica/"
    "wake_up_-_la_rassegna_che_sveglia_gli_italiani-425738372/"
)
JSON_URL = SOURCE_PAGE.replace("/rubriche/", "/json/rubriche/", 1)
FEED_PATH = Path("feed.xml")
TITLE = "Wake Up - La rassegna che sveglia gli italiani"
AUTHOR = "Antonio Fraschilla"
CHANNEL_COVER = (
    "https://www.repstatic.it/video/photo/2026/11/23/1359831/"
    "1359831-thumb-spotify-800-wakeup_2311_podcast.jpg"
)
ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES)

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Referer": SOURCE_PAGE,
})


def parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc)
        except (ValueError, TypeError, IndexError):
            raise ValueError(f"Data puntata non valida: {value!r}")


def fetch_episodes() -> list[dict]:
    results: dict[str, dict] = {}
    url = JSON_URL
    seen_urls: set[str] = set()

    # Limite difensivo: il feed conserva gli episodi delle esecuzioni precedenti.
    for _ in range(5):
        if url in seen_urls:
            break
        seen_urls.add(url)
        response = session.get(url, timeout=30)
        print(f"Sorgente HTTP {response.status_code}: {url}", flush=True)
        response.raise_for_status()
        payload = response.json()
        batch = payload.get("data")
        if not isinstance(batch, list):
            raise RuntimeError("Il JSON non contiene un elenco 'data' valido")
        for ep in batch:
            if not isinstance(ep, dict):
                continue
            guid = str(ep.get("original_id") or "").strip()
            audio = str(ep.get("audio_url") or "").strip()
            name = str(ep.get("title") or "").strip()
            date = str(ep.get("pub_date") or "").strip()
            if not (guid and audio and name and date):
                continue
            if urlsplit(audio).hostname != "media.gedidigital.it":
                continue
            parse_date(date)  # Se il formato cambia, il workflow segnala l'errore.
            results[guid] = {
                "guid": guid,
                "title": name,
                "description": name,
                "date": date,
                "audio": audio,
                "duration": str(ep.get("duration") or ""),
                "image": str(ep.get("image") or CHANNEL_COVER),
            }
        next_url = payload.get("next")
        url = next_url.get("href") if isinstance(next_url, dict) else None
        if not url:
            break
    if not results:
        raise RuntimeError("Nessun episodio valido nella sorgente: feed non modificato")
    return list(results.values())


def existing_episodes() -> dict[str, dict]:
    if not FEED_PATH.exists():
        return {}
    try:
        root = ET.parse(FEED_PATH).getroot()
    except ET.ParseError as exc:
        raise RuntimeError("Il feed esistente non e' XML valido: nessuna sovrascrittura") from exc
    saved = {}
    for item in root.findall("./channel/item"):
        guid = item.findtext("guid")
        enclosure = item.find("enclosure")
        if not guid or enclosure is None or not enclosure.get("url"):
            continue
        art = item.find(f"{{{ITUNES}}}image")
        saved[guid] = {
            "guid": guid,
            "title": item.findtext("title", ""),
            "description": item.findtext("description", ""),
            "date": item.findtext("pubDate", ""),
            "audio": enclosure.get("url"),
            "duration": item.findtext(f"{{{ITUNES}}}duration", ""),
            "image": art.get("href", CHANNEL_COVER) if art is not None else CHANNEL_COVER,
        }
    return saved


def child(parent: ET.Element, name: str, value: str) -> None:
    ET.SubElement(parent, name).text = value


def render_feed(episodes: dict[str, dict]) -> bytes:
    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    child(channel, "title", TITLE)
    child(channel, "link", SOURCE_PAGE)
    child(channel, "description", "Feed RSS personale non ufficiale di Wake Up di Repubblica.")
    child(channel, "language", "it-IT")
    child(channel, "copyright", "Contenuti GEDI / la Repubblica")
    child(channel, "lastBuildDate", format_datetime(datetime.now(timezone.utc)))
    child(channel, f"{{{ITUNES}}}author", AUTHOR)
    child(channel, f"{{{ITUNES}}}explicit", "false")
    child(channel, f"{{{ITUNES}}}type", "episodic")
    ET.SubElement(channel, f"{{{ITUNES}}}category", {"text": "News"})
    ET.SubElement(channel, f"{{{ITUNES}}}image", {"href": CHANNEL_COVER})
    image = ET.SubElement(channel, "image")
    child(image, "url", CHANNEL_COVER)
    child(image, "title", TITLE)
    child(image, "link", SOURCE_PAGE)

    for ep in sorted(episodes.values(), key=lambda e: parse_date(e["date"]), reverse=True)[:200]:
        item = ET.SubElement(channel, "item")
        child(item, "title", ep["title"])
        child(item, "description", ep["description"])
        child(item, "pubDate", format_datetime(parse_date(ep["date"])))
        guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
        guid.text = ep["guid"]
        child(item, f"{{{ITUNES}}}author", AUTHOR)
        if ep["duration"]:
            child(item, f"{{{ITUNES}}}duration", ep["duration"])
        ET.SubElement(item, f"{{{ITUNES}}}image", {"href": ep["image"]})
        ET.SubElement(item, "enclosure", {"url": ep["audio"], "type": "audio/mpeg"})
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> None:
    previous = existing_episodes()
    current = fetch_episodes()
    new = [e for e in current if e["guid"] not in previous]
    if not new and FEED_PATH.exists():
        print(f"Nessuna nuova puntata ({len(current)} trovate). Feed invariato.")
        return
    previous.update({e["guid"]: e for e in current})
    FEED_PATH.write_bytes(render_feed(previous))
    print(f"Feed aggiornato: {len(new)} nuove puntate, {len(previous)} conservate")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        sys.exit(1)
