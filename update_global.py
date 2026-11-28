#!/usr/bin/env python3
"""Collect the international side of the Kerala gold price into global.json.

  gold    international gold price, US dollars per troy ounce, one value per day
  usdinr  rupees per US dollar, one value per day
  news    recent gold-market headlines (title, source, link, time)
  themes  how many headlines mention each driver (Fed, dollar, ...) and a
          rising / falling / neutral word count

Every series has more than one source. If a source fails, the next is tried.
If all fail, the old data stays. global.json also records what worked
(`diag`, `sources`) so a failure is easy to see. Run at most every few hours
unless called with --force. Standard library only.
"""
import csv
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

OUT = "global.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; KeralaGoldRateBot/1.0)", "Accept": "*/*"}
KEEP_DAYS = 400
REFRESH_MINUTES = 150
TZ = timezone.utc


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def d_str(dt):
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------- price series
def from_stooq(symbol, start, end):
    url = ("https://stooq.com/q/d/l/?s=%s&i=d&d1=%s&d2=%s"
           % (symbol, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")))
    text = get(url)
    if "Close" not in text[:200]:
        raise ValueError("unexpected reply: " + text[:60].replace("\n", " "))
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            out[row["Date"]] = float(row["Close"])
        except (KeyError, ValueError, TypeError):
            continue
    return out


def from_yahoo(symbol):
    last = None
    for host in ("query1", "query2"):
        try:
            url = "https://%s.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d" % (
                host, urllib.parse.quote(symbol))
            res = json.loads(get(url))["chart"]["result"][0]
            stamps, closes = res["timestamp"], res["indicators"]["quote"][0]["close"]
            out = {}
            for t, c in zip(stamps, closes):
                if c is not None:
                    out[d_str(datetime.fromtimestamp(t, TZ))] = float(c)
            return out
        except Exception as exc:
            last = exc
    raise last


def from_frankfurter(start, end):
    last = None
    for url in ("https://api.frankfurter.dev/v1/%s..%s?base=USD&symbols=INR",
                "https://api.frankfurter.app/%s..%s?from=USD&to=INR"):
        try:
            data = json.loads(get(url % (d_str(start), d_str(end))))
            return {k: float(v["INR"]) for k, v in data["rates"].items() if "INR" in v}
        except Exception as exc:
            last = exc
    raise last


def from_goldapi_spot():
    data = json.loads(get("https://api.gold-api.com/price/XAU"))
    return {d_str(datetime.now(TZ)): float(data["price"])}


GOLD_RANGE = (500, 20000)   # sane US$ per ounce
FX_RANGE = (40, 200)        # sane rupees per US$


def clean(series, lo_hi):
    lo, hi = lo_hi
    return {k: round(v, 2) for k, v in series.items() if lo <= v <= hi}


def collect(name, tries, lo_hi, min_rows, diag):
    """Run the sources in order; return (series, source name) of the first good one."""
    for label, fn in tries:
        try:
            s = clean(fn(), lo_hi)
            if len(s) < min_rows:
                raise ValueError("only %d rows" % len(s))
            diag.append("%s: %s ok (%d days, latest %s)" % (name, label, len(s), max(s)))
            return s, label
        except Exception as exc:
            diag.append("%s: %s failed (%s)" % (name, label, str(exc)[:90]))
    return None, None


def merge(old, new, max_jump):
    """New values replace old ones for the same day. A new latest value that jumps
    too far from the previous latest one is ignored."""
    out = dict(old)
    if old and new:
        prev = old[max(old)]
        latest = new[max(new)]
        if abs(latest / prev - 1) > max_jump and max(new) > max(old):
            new = {k: v for k, v in new.items() if k != max(new)}
    out.update(new)
    cut = d_str(datetime.now(TZ) - timedelta(days=KEEP_DAYS))
    return dict(sorted((k, v) for k, v in out.items() if k >= cut))


# ------------------------------------------------------------ Gulf shop rates
# Local currency per US dollar (pegged, except the Kuwaiti dinar, which is approximate).
GULF = [("AE", "dubai", 3.6725), ("SA", "saudi-arabia", 3.75), ("QA", "qatar", 3.64),
        ("KW", "kuwait", 0.307), ("OM", "oman", 0.3845), ("BH", "bahrain", 0.376)]


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)


def pick_karat(text, karat, expect):
    """First number after '<karat>K' that is within 4% of the expected local price."""
    for m in re.finditer(r"\b%dK\b" % karat, text):
        for n in re.findall(r"\d[\d,]*\.?\d*", text[m.end(): m.end() + 220]):
            try:
                v = float(n.replace(",", ""))
            except ValueError:
                continue
            if abs(v / expect - 1) <= 0.04:
                return v
    return None


def fetch_gulf(gold_usd, diag):
    """Published 24K/22K shop rates for the Gulf countries (GoodReturns), checked against
    the world price so a misread number is never used. Returns None if nothing was read."""
    out = {}
    for code, slug, peg in GULF:
        est24 = gold_usd / 31.1035 * peg
        try:
            text = strip_tags(get("https://www.goodreturns.in/gold-rates/%s.html" % slug))
        except Exception as exc:
            diag.append("gulf %s failed (%s)" % (code, str(exc)[:60]))
            continue
        r = {}
        for k in (24, 22):
            v = pick_karat(text, k, est24 * k / 24)
            if v:
                r[str(k)] = v
        if r:
            out[code] = r
    diag.append("gulf: %d of %d countries read" % (len(out), len(GULF)))
    return out or None


# ----------------------------------------------------------------------- news
THEMES = [
    ("Fed and interest rates", r"\bfed\b|federal reserve|fomc|powell|rate cut|rate hike|interest rate|treasury yield|bond yield|\byields?\b"),
    ("US dollar", r"\bdollar\b|\bdxy\b|greenback"),
    ("Rupee", r"\brupee\b|\binr\b"),
    ("Inflation and jobs data", r"inflation|\bcpi\b|\bpce\b|payroll|jobs report|unemployment|\bgdp\b"),
    ("Geopolitics and safe haven", r"geopolit|\bwar\b|conflict|ceasefire|tension|sanction|safe[- ]haven|middle east|ukraine|israel|iran|gaza"),
    ("Trade and tariffs", r"tariff|trade war|trade deal"),
    ("Central bank buying", r"central bank|\bpboc\b|reserves"),
    ("ETF and demand", r"\betf\b|demand|jewellery|jewelry|import|duty"),
]
UP_WORDS = r"\b(rise|rises|rising|rose|jump|jumps|surge|surges|climb|climbs|gain|gains|rally|rallies|record|higher|soar|soars|up)\b"
DOWN_WORDS = r"\b(fall|falls|falling|fell|drop|drops|slip|slips|slide|slides|tumble|tumbles|decline|declines|lose|loses|dip|dips|slump|slumps|retreat|retreats|lower|down|plunge|plunges|cheaper)\b"
RELEVANT = re.compile(r"gold|bullion|rupee|dollar|\bfed\b|federal reserve", re.I)

QUERIES = ["gold price", "gold price Fed dollar", "rupee dollar gold India"]


def fetch_news(diag):
    items, seen = [], set()
    ok = 0
    for q in QUERIES:
        try:
            url = ("https://news.google.com/rss/search?q=%s&hl=en-IN&gl=IN&ceid=IN:en"
                   % urllib.parse.quote(q + " when:7d"))
            root = ET.fromstring(get(url))
            ok += 1
        except Exception as exc:
            diag.append("news '%s' failed (%s)" % (q, str(exc)[:70]))
            continue
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            src = (it.findtext("source") or "").strip()
            try:
                when = parsedate_to_datetime(it.findtext("pubDate")).astimezone(TZ)
            except Exception:
                continue
            if src and title.endswith(" - " + src):
                title = title[: -len(" - " + src)].strip()
            if not title or not link.startswith("http") or not RELEVANT.search(title):
                continue
            key = re.sub(r"[^a-z0-9]", "", title.lower())[:60]
            if key in seen:
                continue
            seen.add(key)
            items.append({"t": title[:170], "s": src[:40], "u": link,
                          "d": when.strftime("%Y-%m-%dT%H:%MZ")})
    items.sort(key=lambda x: x["d"], reverse=True)
    items = items[:12]
    diag.append("news: %d of %d searches ok, %d headlines" % (ok, len(QUERIES), len(items)))
    return items if ok else None


def themes(items):
    counts = {}
    up = down = flat = 0
    for it in items:
        t = it["t"].lower()
        for name, pat in THEMES:
            if re.search(pat, t):
                counts[name] = counts.get(name, 0) + 1
        u, d = bool(re.search(UP_WORDS, t)), bool(re.search(DOWN_WORDS, t))
        if u and not d:
            up += 1
        elif d and not u:
            down += 1
        else:
            flat += 1
    top = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    return {"n": len(items), "counts": top, "up": up, "down": down, "flat": flat}


# ----------------------------------------------------------------------- main
def load_old():
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    force = "--force" in sys.argv
    old = load_old()
    now = datetime.now(TZ)
    if not force and old.get("checked"):
        try:
            age = now - datetime.fromisoformat(old["checked"])
            if age < timedelta(minutes=REFRESH_MINUTES):
                print("Checked %d minutes ago; nothing to do." % (age.total_seconds() // 60))
                return
        except ValueError:
            pass

    start, end = now - timedelta(days=KEEP_DAYS), now
    diag, sources = [], dict(old.get("sources") or {})

    gold, gsrc = collect("gold", [
        ("Stooq", lambda: from_stooq("xauusd", start, end)),
        ("Yahoo XAUUSD", lambda: from_yahoo("XAUUSD=X")),
        ("Yahoo gold futures", lambda: from_yahoo("GC=F")),
        ("gold-api spot", from_goldapi_spot),
    ], GOLD_RANGE, 1, diag)
    fx, fsrc = collect("usdinr", [
        ("ECB via Frankfurter", lambda: from_frankfurter(start, end)),
        ("Stooq", lambda: from_stooq("usdinr", start, end)),
        ("Yahoo", lambda: from_yahoo("INR=X")),
    ], FX_RANGE, 1, diag)
    news = fetch_news(diag)
    gulf = None
    if gold:
        try:
            gulf = fetch_gulf(gold[max(gold)], diag)
        except Exception as exc:
            diag.append("gulf failed (%s)" % str(exc)[:60])

    new = dict(old)
    if gold:
        new["gold"] = merge(old.get("gold") or {}, gold, 0.15)
        sources["gold"] = gsrc
    if fx:
        new["usdinr"] = merge(old.get("usdinr") or {}, fx, 0.04)
        sources["usdinr"] = fsrc
    if news is not None:
        new["news"] = news
        new["themes"] = themes(news)
        sources["news"] = "Google News"
    if gulf:
        new["gulf"] = {"date": d_str(now), "src": "GoodReturns", "r": gulf}
    new["sources"] = sources
    new["diag"] = diag
    for line in diag:
        print(line)

    same = all(json.dumps(new.get(k), sort_keys=True) == json.dumps(old.get(k), sort_keys=True)
               for k in ("gold", "usdinr", "news", "themes", "gulf", "sources", "diag"))
    new["checked"] = now.isoformat(timespec="minutes")
    if same and old.get("checked"):
        # nothing new: remember the check time only when the diagnostics changed anyway
        print("No change in international data.")
        return
    new["updated"] = now.isoformat(timespec="minutes")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=0)
        f.write("\n")
    print("Saved %s" % OUT)


if __name__ == "__main__":
    main()
