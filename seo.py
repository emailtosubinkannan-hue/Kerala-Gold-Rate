#!/usr/bin/env python3
"""Keep the search-engine parts of the site in step with data.json.

It rewrites, inside index.html, the blocks between these markers:
  <!--SEO:start--> ... <!--SEO:end-->    title, description, canonical, share tags, structured data
  <!--LEAD:start--> ... <!--LEAD:end-->  the one-sentence rate summary (visible text for crawlers)
  <!--FAQ:start--> ... <!--FAQ:end-->    the questions and answers
and it writes sitemap.xml and robots.txt.

The site address comes from the CNAME file if there is one (custom domain),
otherwise it is the GitHub Pages address. Run `python3 seo.py` after adding or
changing CNAME. update_rates.py calls refresh() after every new rate.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
GITHUB_URL = "https://emailtosubinkannan-hue.github.io/Kerala-Gold-Rate/"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

FAQ = [
    ("How many grams are in one pavan of gold?",
     "One pavan is 8 grams. To get the price of one pavan, multiply the per-gram rate by 8."),
    ("What is the difference between 22K and 24K gold?",
     "24K gold is almost pure (99.9%) and is mostly sold as coins and bars. 22K gold is about 91.6% gold mixed with other metals such as copper or silver, which makes it strong enough for jewellery. Kerala jewellers price ornaments at the 22K rate."),
    ("Why is the price at the jeweller higher than the gold rate?",
     "The gold rate is the price of the gold only. The jeweller adds making charges (a percentage that depends on the design), 3% GST on the gold value plus making charges, and a small hallmarking fee. Use the jewellery price calculator on this page to estimate the final bill."),
    ("Why does the gold rate change?",
     "Kerala rates follow international gold prices and the dollar-rupee exchange rate, and are also affected by import duty and local demand. The day’s rate is usually announced in the morning and can be revised later the same day when markets move sharply."),
    ("Is the gold rate the same in every Kerala jeweller?",
     "Most jewellers in Kerala follow the daily rate announced by the state’s gold traders’ association, so the gold rate is usually the same across the state. Making charges and discounts differ from shop to shop."),
    ("Is it a good time to buy gold today?",
     "See the purchasing guide, market analysis and buying strategy on this page. They use the last year of 22K prices to show the trend, momentum, support and resistance, and suggest whether to buy now, buy in parts or wait. It is a rule-based guide, not financial advice."),
    ("Where do these rates come from?",
     "The rates are collected automatically from public Kerala gold-rate websites several times a day, and the charts are built from the daily rates saved on this page."),
]


def base_url():
    try:
        with open(os.path.join(ROOT, "CNAME"), encoding="utf-8") as f:
            d = f.read().strip()
        if d:
            return f"https://{d}/"
    except FileNotFoundError:
        pass
    return GITHUB_URL


def inr(n):
    """Indian digit grouping: 1,23,456"""
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def latest_rate(today):
    for k in ("e", "a", "m"):
        if today.get(k):
            return today[k]
    return None


def label(date):
    y, m, d = date.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def esc(s):
    return html.escape(s, quote=True)


def head_block(base, rate, date, updated):
    g, p = inr(rate), inr(rate * 8)
    title = f"Kerala Gold Rate Today: 22K ₹{g}/g, ₹{p}/Pavan"
    desc = (f"Kerala gold rate today ({label(date)}): 22K ₹{g}/gram, ₹{p}/pavan. "
            "Daily, monthly and yearly charts, buy-or-wait signal, price calculator. English and Malayalam.")
    img_alt = "Kerala Gold Rate Today: 22K gold price per gram and pavan, charts and buying guide"
    faq_ld = [{"@type": "Question", "name": q,
               "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": base + "#website", "url": base, "name": "Kerala Gold Rate",
         "description": "Today's 22K gold rate in Kerala per gram and per pavan, with charts and a buying guide.",
         "inLanguage": ["en-IN", "ml-IN"]},
        {"@type": "WebPage", "@id": base + "#webpage", "url": base, "name": title, "description": desc,
         "isPartOf": {"@id": base + "#website"}, "inLanguage": "en-IN", "dateModified": updated,
         "primaryImageOfPage": {"@type": "ImageObject", "url": base + "og-image.png", "width": 1200, "height": 630},
         "about": {"@type": "Thing", "name": "Gold price in Kerala"}},
        {"@type": "FAQPage", "@id": base + "#faq", "isPartOf": {"@id": base + "#webpage"}, "mainEntity": faq_ld},
    ]}
    ld_json = json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    lines = [
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{base}">',
        '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Kerala Gold Rate">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{base}">',
        f'<meta property="og:image" content="{base}og-image.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(img_alt)}">',
        '<meta property="og:locale" content="en_IN">',
        '<meta property="og:locale:alternate" content="ml_IN">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{base}og-image.png">',
        f'<meta name="twitter:image:alt" content="{esc(img_alt)}">',
        '<link rel="icon" href="favicon.svg" type="image/svg+xml">',
        '<link rel="icon" href="icon-192.png" sizes="192x192" type="image/png">',
        '<link rel="apple-touch-icon" href="apple-touch-icon.png">',
        '<link rel="manifest" href="manifest.webmanifest">',
        f'<script type="application/ld+json">{ld_json}</script>',
    ]
    return "\n".join(lines)


def lead_text(rate, date):
    return (f"Kerala gold rate today ({label(date)}): 22K gold is ₹{inr(rate)} per gram "
            f"and ₹{inr(rate * 8)} per pavan (8 g).")


def faq_block():
    out = []
    for i, (q, a) in enumerate(FAQ, 1):
        out.append(f'<details><summary data-i18n-html="faq{i}_q">{html.escape(q, quote=False)}</summary>'
                   f'<div class="gd" data-i18n-html="faq{i}_a">{html.escape(a, quote=False)}</div></details>')
    return "\n".join(out)


def swap(text, name, new):
    pat = re.compile(r"(<!--" + name + r":start-->)(.*?)(<!--" + name + r":end-->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"marker {name} not found in index.html")
    return pat.sub(lambda m: m.group(1) + "\n" + new + "\n" + m.group(3), text, count=1)


def write_if_changed(path, content):
    old = None
    try:
        with open(path, encoding="utf-8") as f:
            old = f.read()
    except FileNotFoundError:
        pass
    if old == content:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def refresh(data=None):
    if data is None:
        with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
            data = json.load(f)
    today = data["today"]
    rate = latest_rate(today)
    if not rate:
        return False
    base = base_url()
    date = today["date"]
    updated = data.get("updated") or date
    path = os.path.join(ROOT, "index.html")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = swap(text, "SEO", head_block(base, rate, date, updated))
    text = swap(text, "LEAD", f'<p class="lead" id="lead">{esc(lead_text(rate, date))}</p>')
    text = swap(text, "FAQ", faq_block())
    changed = write_if_changed(path, text)
    changed |= write_if_changed(os.path.join(ROOT, "sitemap.xml"),
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url>\n    <loc>{base}</loc>\n    <lastmod>{date}</lastmod>\n"
        "    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n</urlset>\n")
    changed |= write_if_changed(os.path.join(ROOT, "robots.txt"),
        f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n")
    return changed


if __name__ == "__main__":
    print("updated" if refresh() else "already up to date")
