import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


STATE = "sent_stories.json"
MAX = 200
TIMEOUT = 15
UA = "Mozilla/5.0"  # Plain UA: the full Chrome string trips ESPN's bot detection (202 + empty body).

SOURCES = {
    "radiotavisupleba_news": "https://www.radiotavisupleba.ge/api/zivpol-vomx-tpemqyi",
    "radiotavisupleba_politics": "https://www.radiotavisupleba.ge/api/zpvpil-vomx-tpe_qyp",
    "radiotavisupleba_society": "https://www.radiotavisupleba.ge/api/zuvprl-vomx-tpegqyq",
    "radiotavisupleba_economics": "https://www.radiotavisupleba.ge/api/zyvp_l-vomx-tpetqyy",
    "radiotavisupleba_culture": "https://www.radiotavisupleba.ge/api/zotptl-vomx-tpepoyt",
    "setanta_georgia_fb": "https://rss.app/feeds/HT20mdZJHvzD3s6H.xml",
    "fightnight_georgia_fb": "https://rss.app/feeds/8AviEtMq1cVxu8SC.xml",
    "espn_mma": "https://www.espn.com/espn/rss/mma/news",
}


def fetch(url: str) -> ET.Element:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return ET.fromstring(r.read())


def parse(root: ET.Element) -> list[dict]:
    out = []
    for it in root.iter("item"):
        title = it.findtext("title", default="").strip()
        link = it.findtext("link", default="").strip()
        if link:
            out.append({"title": title, "link": link})
    return out


def load() -> dict:
    if not os.path.exists(STATE):
        return {}
    with open(STATE, encoding="utf-8") as f:
        return json.load(f)


def save(state: dict) -> None:
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def send(token: str, chat: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        r.read()


def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("CHAT_ID")
    if not token or not chat:
        raise SystemExit("TELEGRAM_TOKEN and CHAT_ID environment variables are required")

    state = load()
    changed = False

    # The same article often appears in several category feeds
    # Track links across all sources so it is only ever notified once.
    seen = {link for links in state.values() for link in links}

    for name, url in SOURCES.items():
        if not url:
            continue

        fresh = name not in state
        known = set(state.get(name, []))

        try:
            root = fetch(url)
        except (urllib.error.URLError, ET.ParseError) as e:
            print(f"[{name}] fetch/parse failed: {e}")
            continue

        items = parse(root)

        if fresh:
            # First time we've seen this source: seed state instead of blasting every historical item as a "new" notification.
            print(f"[{name}] new source, seeding {len(items)} items without notifying")
        else:
            new = [it for it in items if it["link"] not in seen]
            for it in reversed(new):  # oldest-first for chronological order
                text = f"{it['title']}\n{it['link']}"
                try:
                    send(token, chat, text)
                except urllib.error.URLError as e:
                    print(f"[{name}] telegram send failed: {e}")
                    continue
                print(f"[{name}] sent: {it['title']}")
                time.sleep(1)  # stay well under Telegram's per-chat rate limit

        cur = [it["link"] for it in items]
        old = [l for l in known if l not in set(cur)]
        state[name] = (cur + old)[:MAX]
        seen.update(cur)
        changed = True

    if changed:
        save(state)


if __name__ == "__main__":
    main()
