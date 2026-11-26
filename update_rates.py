#!/usr/bin/env python3
"""Fetch today's Kerala 22K gold rate (per gram) and store it in data.json.

Runs on a schedule in GitHub Actions. If no source can be read, or the value
looks wrong, the script exits with an error and leaves data.json untouched.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
DATA_FILE = "data.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; KeralaGoldRateBot/1.0)"}


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)


def num(s):
    return int(s.replace(",", ""))


def parse_keralagold_org(html):
    # 1) structured data block on the page
    m = re.search(r"Gold Rate in Kerala[^}]*?\"price\"\s*:\s*(\d{4,6})", html, re.S)
    if m:
        return int(m.group(1))
    # 2) visible text
    text = strip_tags(html)
    for pat in (r"22K Gold / 1 Gram\s*₹\s*([\d,]+)", r"22K / Gram\s*₹\s*([\d,]+)"):
        m = re.search(pat, text)
        if m:
            return num(m.group(1))
    return None


def parse_keralagoldrates_com(html):
    text = strip_tags(html)
    m = re.search(r"₹\s*([\d,]+)\s*/\s*gram", text)
    return num(m.group(1)) if m else None


SOURCES = [
    ("https://keralagold.org/", parse_keralagold_org),
    ("https://keralagoldrates.com/", parse_keralagoldrates_com),
]


def fetch_rate(previous):
    for url, parser in SOURCES:
        try:
            req = urllib.request.Request(url, headers=UA)
            html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            rate = parser(html)
        except Exception as exc:  # network or parse problem: try next source
            print(f"{url}: failed ({exc})")
            continue
        if rate is None:
            print(f"{url}: could not find the rate on the page")
            continue
        if not (3000 <= rate <= 100000):
            print(f"{url}: rate {rate} is outside the sane range, ignored")
            continue
        if previous and abs(rate - previous) / previous > 0.15:
            print(f"{url}: rate {rate} jumped more than 15% from {previous}, ignored")
            continue
        print(f"{url}: 22K = {rate}/g")
        return rate
    return None


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    days = data["days"]
    previous = days[max(days)] if days else None
    rate = fetch_rate(previous)
    if rate is None:
        print("No valid rate found. data.json left unchanged.")
        sys.exit(1)

    now = datetime.now(IST)
    today = now.strftime("%Y-%m-%d")
    slot = "m" if now.hour < 12 else "a" if now.hour < 17 else "e"

    if data["today"].get("date") != today:
        data["today"] = {"date": today, "m": None, "a": None, "e": None}
    data["today"][slot] = rate
    days[today] = rate
    data["days"] = dict(sorted(days.items()))
    data["updated"] = now.isoformat(timespec="minutes")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"Saved {today} ({slot}): {rate}")


if __name__ == "__main__":
    main()
