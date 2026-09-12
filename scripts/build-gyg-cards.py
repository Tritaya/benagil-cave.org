# -*- coding: utf-8 -*-
"""Build the GetYourGuide card blocks for benagil-cave.org from the offers JSON files in this
folder (both shelves: benagil-l163460 city page + benagil-sea-cave-l89246 POI page), and inject
them into the hand-written pages (index.html, operators.html, benagil-cave-worth-it.html)
between <!-- GYG:name --> markers. The town-page generator (_gen_town_pages.py) reads
gyg-cards.json.

Slots are SELECTORS (departure town x craft), not hand-picked id lists; the order on the page is
the stated rule: value (price x rating) desc, then reviews desc. Floors keep 5-review products
off the page. HERO_OVERRIDES exists for a deliberate editorial pick; print the chosen heroes.

Lanes (partner-global cmp namespace, device-named):
  bcorg     product links on cards
  bcorg-bt  the pinned availability calendar (one per page, id="availability")
  bcorg-a   the auto widget end slot
"""
import base64
import glob
import html
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
PARTNER = "1Q7ZSYC"
CMP = "bcorg"
CARD_MIN_REVIEWS = 20
HERO_MIN_REVIEWS = 100
CARDS_PER_SLOT = 6

BEN = re.compile(r"benagil", re.I)
KAYAK = re.compile(r"kayak|paddle|\bsup\b|stand[- ]up|canoe", re.I)
CAT = re.compile(r"catamaran|sailing|\bsail\b|yacht", re.I)
DOLPH = re.compile(r"dolphin", re.I)
TOWNS = {
    "benagil": re.compile(r"benagil beach|praia de benagil|from benagil|benagil:", re.I),
    "carvoeiro": re.compile(r"carvoeiro", re.I),
    "armacao": re.compile(r"arma[cç][aã]o", re.I),
    "portimao": re.compile(r"portim[aã]o|ferragudo|praia da rocha", re.I),
    "albufeira": re.compile(r"albufeira", re.I),
    "lagos": re.compile(r"\blagos\b", re.I),
    "vilamoura": re.compile(r"vilamoura|quarteira", re.I),
}
TOWN_LABEL = {"benagil": "Benagil beach", "carvoeiro": "Carvoeiro", "armacao": "Armação de Pêra", "portimao": "Portimão",
              "albufeira": "Albufeira", "lagos": "Lagos", "vilamoura": "Vilamoura"}

# editorial operator profiles on operators.html -> provider-name patterns for inline GYG links
OPLINKS = {
    "carvoeiro-caves": r"carvoeiro caves|vela brilhante", "carvoeiro-tours": r"carvoeiro tours",
    "setima-onda": r"s[eé]tima onda", "tridente": r"tridente", "benagil-eco": r"benagil eco",
    "benagil-kayak": r"benagil kayak|kayak (&|and) sup benagil", "blue-xperiences": r"blue ?xperiences", "cave-captain": r"cave ?captain",
    "sunboat": r"sunboat", "benagil-express": r"benagil express", "ocean4fun": r"ocean ?4 ?fun",
    "algarexperience": r"algarexperience", "bom-dia": r"bom dia", "seafaris": r"seafaris",
    "algarve-cave-tours": r"algarve cave tours|geoff meadows",
}

HERO_OVERRIDES = {
    # The boat page's own verdict is "if the cave is the point, leave from Carvoeiro or Armacao";
    # its calendar must not then sell a $116 Portimao cruise (t197581, the raw value winner).
    "benagil-boat-tour": 421964,
}


def f(t, k):
    v = t.get(k)
    if isinstance(v, list):
        return " ".join(json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else str(x) for x in v)
    return str(v or "")


def load():
    by = {}
    for fp in sorted(glob.glob(os.path.join(HERE, "gyg_*.json"))):
        d = json.load(io.open(fp, encoding="utf-8"))
        d = d if isinstance(d, list) else d.get("products") or d.get("offers")
        for t in d:
            by[int(t["id"])] = t
    return by


def rating(t):
    try:
        return float(t.get("formattedRating") or t.get("rating") or 0)
    except (TypeError, ValueError):
        return 0.0


def reviews(t):
    return int(t.get("reviewCount") or 0)


def price_num(t):
    return float(t.get("startingPrice") or 0)


def price(t):
    p = t.get("formattedStartingPrice")
    if p:
        return p
    return "$%d" % round(price_num(t)) if price_num(t) else ""


def value(t):
    return price_num(t) * rating(t)


def clean_title(t):
    s = t.get("title") or ""
    s = re.sub(r"\s*[-–]\s*20\d\d\s*\(Verified Reviews\)\s*$", "", s)
    s = re.sub(r"\s*[-–]\s*From \$\d+\s*$", "", s)
    return s.strip()


def craft(t):
    title = f(t, "title")
    if KAYAK.search(title):
        return "kayak"
    if CAT.search(title + " " + f(t, "abstract")):
        return "cat"
    return "boat"


FAR_ORIGIN = re.compile(r"lisbon|lisboa|sevill|faro\b|olh[aã]o|tavira|quarteira|vilamoura|sintra|porto\b", re.I)
NOT_CAVE_TRIP = re.compile(r"\bhik|walk|trek|e-?bike|bike|jeep|safari|buggy|quad|tuk|segway|charter|yacht|4x4|castle|silves|monchique|winery|vineyard|city tour", re.I)


def title_prefix_town(t):
    """'From Portimão: ...' / 'Albufeira: ...' names the DEPARTURE. Itinerary stops do not."""
    m = re.match(r"^\s*(?:from\s+)?([^:]{3,40}):", f(t, "title"), re.I)
    if not m:
        return None
    pre = m.group(1)
    for k, p in TOWNS.items():
        if p.search(pre):
            return k
    return "far" if FAR_ORIGIN.search(pre) else None


def towns(t):
    pre = title_prefix_town(t)
    if pre == "far":
        return []
    if pre:
        return [pre]
    # pickup / meeting text next; itinerary only its pickup/start entries
    pk = " ".join(f(t, k) for k in ("meetingPoint", "meetingPointAddress", "meetingPoints"))
    it = t.get("itinerary") or []
    if isinstance(it, list):
        for step in it:
            if isinstance(step, dict) and re.search(r"pickup|starting|meeting|departure", str(step.get("name", "")), re.I):
                pk += " " + str(step.get("description", ""))
    if FAR_ORIGIN.search(pk) and not any(p.search(pk) for p in TOWNS.values()):
        return []
    tw = [k for k, p in TOWNS.items() if p.search(pk)]
    if not tw:
        loc = f(t, "location").lower()
        if FAR_ORIGIN.search(loc):
            return []
        tw = [k for k, p in TOWNS.items() if p.search(loc)]
    return tw


def far_origin(t):
    """A day trip FROM Lisbon/Faro/Seville etc. is not a Benagil departure, whatever it stops at."""
    return title_prefix_town(t) == "far" or bool(FAR_ORIGIN.search(f(t, "title")))


def cave_trip(t):
    """Boat or paddle products only: no walks, bikes, jeeps, private charters priced per group."""
    return not NOT_CAVE_TRIP.search(f(t, "title"))


def base_true(t):
    return bool(BEN.search(" ".join(f(t, k) for k in ("title", "abstract", "description", "highlights", "itinerary")))) \
        and not far_origin(t) and cave_trip(t)


def what(t):
    c = craft(t)
    tw = towns(t)
    parts = []
    parts.append({"kayak": "Guided kayak/SUP into the cave", "cat": "Catamaran, views the cave from the entrance", "boat": "Boat, enters the cave sea permitting"}[c])
    if tw:
        parts.append("from " + " / ".join(TOWN_LABEL[x] for x in tw[:2]))
    if DOLPH.search(f(t, "title")):
        parts.append("+ dolphins")
    return ", ".join(parts[:2]) + (" " + parts[2] if len(parts) > 2 else "")


def bare_url(t):
    return (t.get("url") or "").split("?")[0]


def aff_url(t):
    return "%s?partner_id=%s&utm_medium=online_publisher&cmp=%s" % (bare_url(t), PARTNER, CMP)


def b64(u):
    return base64.b64encode(u.encode("utf-8")).decode("ascii")


def img_hash(t):
    for u in t.get("images") or []:
        m = re.search(r"/tour_img/([^/]+?\.(?:jpe?g|png))$", u, re.I)
        if m:
            return m.group(1)
    return None


def thumb(t):
    h = img_hash(t)
    return "https://cdn.getyourguide.com/img/tour/%s/134.jpg" % h if h else ""


def og_image(t):
    h = img_hash(t)
    return "https://cdn.getyourguide.com/img/tour/%s/148.jpg" % h if h else ""


def badge(t):
    for b in t.get("badges") or []:
        b = str(b)
        if b.startswith("#1 selling") or b in ("Top rated", "Top pick", "Likely to sell out", "Certified by GetYourGuide", "Official ticket"):
            return b
    return t.get("bookedRecentlyText") or ""


def card(t, rank):
    e = lambda s: html.escape(str(s), quote=True)
    c = craft(t)
    meta = ['<span class="ec-rating">%.1f&#9733; (%s)</span>' % (rating(t), format(reviews(t), ","))]
    if price(t):
        meta.append('<span class="ec-price">from %s</span>' % e(price(t)))
    meta.append('<span class="ec-reach ec-reach-%s">%s</span>' % (c, {"kayak": "Kayak / SUP", "cat": "Catamaran", "boat": "Boat"}[c]))
    if is_private(t):
        meta.append('<span class="ec-reach ec-reach-cat">Private, priced per boat</span>')
    b = badge(t)
    if not b and reviews(t) >= 2000:
        b = "Most booked"
    if b:
        meta.append('<span class="ec-hot">%s</span>' % e(b))
    if t.get("freeCancellation"):
        meta.append('<span class="ec-fc">Free cancellation</span>')
    return (
        '      <li class="ec-tour-item">\n'
        '        <a class="vlink ec-tour" data-vurl="%s" role="link" rel="sponsored nofollow noopener" tabindex="0" aria-label="%s on GetYourGuide">\n'
        '          <span class="ec-rank">%d</span>\n'
        '          <img class="ec-thumb" src="%s" alt="" loading="lazy" width="92" height="92">\n'
        '          <span class="ec-body">\n'
        '            <span class="ec-title">%s</span>\n'
        '            <span class="ec-what">%s</span>\n'
        '            <span class="ec-meta">%s</span>\n'
        '          </span>\n'
        '          <span class="ec-cta">Check availability &#8594;</span>\n'
        '        </a>\n'
        '      </li>'
    ) % (b64(aff_url(t)), e(clean_title(t)), rank, e(thumb(t)), e(clean_title(t)), e(what(t)), "\n              ".join(meta))


SUP = re.compile(r"\bsup\b|paddle ?board|stand[- ]up", re.I)
SPEED = re.compile(r"speed ?boat|\brib\b|fast boat|semi-rigid|zodiac", re.I)


def is_sup(t):
    return bool(SUP.search(f(t, "title")))


def is_private(t):
    """The title alone is not enough: t195731 is titled 'Benagil Cave & Marinha Beach Boat Tour'
    and its GYG slug is 'algarve-coast-private-boat-tour' at $447 per hull (audit, 2026-09-12)."""
    hay = " ".join((f(t, "title"), f(t, "url"), f(t, "abstract")))
    return bool(re.search(r"\bprivate\b|\bprivado\b|per boat|per group|whole boat|exclusive use", hay, re.I))


def ranked(pool, sel, min_reviews):
    """Per-person tours first (value desc, reviews desc), then private boats priced per group -
    a EUR 400 private hull with 20 reviews must not lead a list of EUR 40 seats with 1,000."""
    ids = [i for i, t in pool.items() if sel(t) and reviews(t) >= min_reviews and price_num(t) > 0]
    ids.sort(key=lambda i: (is_private(pool[i]), -value(pool[i]), -reviews(pool[i])))
    return ids


def cards_html(pool, ids, exclude=None, limit=CARDS_PER_SLOT):
    """Value order, but the slot's MOST-BOOKED product always gets a card (the honest budget pick the
    doctrine asks for): a $14 RIB with 13,888 reviews must not vanish behind six $50 seats."""
    ids = [i for i in ids if i != exclude]
    shown = ids[:limit]
    if ids:
        top = max(ids, key=lambda i: reviews(pool[i]))
        if top not in shown and len(shown) >= 1:
            shown = shown[:-1] + [top] if len(shown) >= limit else shown + [top]
    return '<ol class="ec-tours">\n' + "\n".join(card(pool[i], n + 1) for n, i in enumerate(shown)) + "\n    </ol>", shown


def widget_availability(tid):
    return ('<div class="avail-widget" id="availability">\n'
            '      <div data-gyg-widget="availability" data-gyg-tour-id="%d" data-gyg-partner-id="%s" data-gyg-cmp="%s-bt" data-gyg-locale-code="en-US" data-gyg-currency="USD"></div>\n'
            '    </div>' % (tid, PARTNER, CMP))


def widget_auto():
    return '<div data-gyg-widget="auto" data-gyg-partner-id="%s" data-gyg-cmp="%s-a" data-gyg-locale-code="en-US" data-gyg-currency="USD"></div>' % (PARTNER, CMP)


DISCLAIMER = ('<p class="t-note ec-note">Prices are GetYourGuide "from" prices in US dollars, per person unless the card says "priced per boat" (private boats are listed after the per-person tours), ratings and review counts as captured 12 September 2026; '
              'they move with season and availability &#8212; the live widget and the booking page are the reference. Sea permitting: swell over about 1.5 m closes the cave. '
              'Booking through these links may earn us a commission at no extra cost to you; it never changes the order or the verdicts.</p>')


def inject(path, marker, block, inline=False):
    h = io.open(path, encoding="utf-8").read()
    pat = re.compile(r"(<!-- GYG:%s -->)(.*?)(<!-- /GYG:%s -->)" % (re.escape(marker), re.escape(marker)), re.S)
    if not pat.search(h):
        raise SystemExit("marker GYG:%s missing in %s" % (marker, os.path.basename(path)))
    pad = "" if inline else "\n    "
    h = pat.sub(lambda m: m.group(1) + pad + block + pad + m.group(3), h, count=1)
    io.open(path, "w", encoding="utf-8").write(h)


def hero_lead(pool, tid):
    t = pool[tid]
    e = lambda s: html.escape(str(s), quote=True)
    return ('<strong>%s</strong> &mdash; %.1f&#9733; from %s reviews, from %s, %s. %s' % (
        e(clean_title(t)), rating(t), format(reviews(t), ","), e(price(t)),
        "free cancellation" if t.get("freeCancellation") else "see cancellation terms",
        e((t.get("abstract") or "")[:220])))


def main():
    pool = {i: t for i, t in load().items() if base_true(t)}
    is_kayak = lambda t: craft(t) == "kayak"
    near = lambda t: craft(t) != "kayak" and any(x in towns(t) for x in ("carvoeiro", "armacao", "benagil"))
    catd = lambda t: craft(t) != "kayak" and (craft(t) == "cat" or DOLPH.search(f(t, "title")) or any(x in towns(t) for x in ("portimao", "albufeira", "lagos", "vilamoura")))
    town_sel = lambda tw: (lambda t: tw in towns(t))   # any craft that departs there

    def town_slot(tw, fallback):
        """A town's own departures; if the page would be thin (<4 cards after the hero), fill with
        the nearest launches so no town page ships an empty list (cards say where each leaves from)."""
        ids = ranked(pool, town_sel(tw), CARD_MIN_REVIEWS)
        if len(ids) < 5:
            ids += [i for i in fallback if i not in ids]
        return ids

    near_ids = ranked(pool, near, CARD_MIN_REVIEWS)
    catd_ids = ranked(pool, catd, CARD_MIN_REVIEWS)
    # mode slots for the two spoke pages (/benagil-boat-tour, /benagil-cave-kayak)
    is_speed = lambda t: craft(t) == "boat" and (SPEED.search(f(t, "title") + " " + f(t, "includes") + " " + f(t, "description")[:300]) is not None)
    is_kayak_only = lambda t: craft(t) == "kayak" and not is_sup(t)
    SLOTS = {
        "boat-near": near_ids,
        "kayak": ranked(pool, is_kayak, CARD_MIN_REVIEWS),
        "cat-dolphin": catd_ids,
        "speedboat": ranked(pool, is_speed, CARD_MIN_REVIEWS),
        "boat-any": ranked(pool, lambda t: craft(t) == "boat", CARD_MIN_REVIEWS),
        "catamaran": ranked(pool, lambda t: craft(t) == "cat", CARD_MIN_REVIEWS),
        "kayak-only": ranked(pool, is_kayak_only, CARD_MIN_REVIEWS),
        "sup": ranked(pool, lambda t: craft(t) == "kayak" and is_sup(t), 5),
        "benagil-cave-tour-from-carvoeiro": town_slot("carvoeiro", near_ids),
        "benagil-cave-tour-from-armacao-de-pera": town_slot("armacao", near_ids),
        "benagil-cave-tour-from-portimao": town_slot("portimao", catd_ids),
        "benagil-cave-tour-from-albufeira": town_slot("albufeira", catd_ids),
        "benagil-cave-tour-from-lagos": town_slot("lagos", catd_ids),
    }

    def pick_hero(slug, ids):
        """Hero = the calendar: a per-person BOAT with a real review base (the town pages are written
        around boats; a kayak hero on the Carvoeiro page contradicted its own copy - audit 2026-09-12),
        then any per-person tour, never a private hull."""
        if slug in HERO_OVERRIDES:
            return HERO_OVERRIDES[slug]
        for want_boat in (True, False):
            for i in ids:
                t = pool[i]
                if reviews(t) >= HERO_MIN_REVIEWS and not is_private(t) and (craft(t) != "kayak" or not want_boat):
                    return i
        for i in ids:
            if not is_private(pool[i]):
                return i
        return ids[0]

    HEROES = {
        "index": pick_hero("index", SLOTS["boat-near"]),
        "operators": pick_hero("operators", SLOTS["boat-near"]),
        "benagil-cave-worth-it": pick_hero("benagil-cave-worth-it", SLOTS["boat-near"]),
    }
    for slug in ("benagil-cave-tour-from-carvoeiro", "benagil-cave-tour-from-armacao-de-pera", "benagil-cave-tour-from-portimao",
                 "benagil-cave-tour-from-albufeira", "benagil-cave-tour-from-lagos"):
        HEROES[slug] = pick_hero(slug, SLOTS[slug])
    # spoke pages: the boat page's calendar is the best per-person boat (any town); the kayak
    # page's calendar is a KAYAK (never a SUP - that is its own mode on the same page)
    HEROES["benagil-boat-tour"] = pick_hero("benagil-boat-tour", SLOTS["boat-any"])
    HEROES["benagil-cave-kayak"] = pick_hero("benagil-cave-kayak", SLOTS["kayak-only"])

    out = {"partner": PARTNER, "cmp": CMP, "stamp": "12 September 2026", "heroes": HEROES, "slots": {}, "og": {}, "hero_meta": {},
           "disclaimer": DISCLAIMER, "widget_auto": widget_auto()}
    for slug, tid in HEROES.items():
        t = pool[tid]
        out["og"][slug] = og_image(t)
        out["hero_meta"][slug] = {"id": tid, "title": clean_title(t), "price": price(t), "rating": rating(t), "reviews": reviews(t),
                                  "aff": aff_url(t), "widget": widget_availability(tid), "lead": hero_lead(pool, tid)}
    TOWN_OF_SLUG = {"benagil-cave-tour-from-carvoeiro": "carvoeiro", "benagil-cave-tour-from-armacao-de-pera": "armacao",
                    "benagil-cave-tour-from-portimao": "portimao", "benagil-cave-tour-from-albufeira": "albufeira",
                    "benagil-cave-tour-from-lagos": "lagos"}
    for slot, ids in SLOTS.items():
        out["slots"][slot] = {"ids": ids, "html_by_page": {}, "count_by_page": {}, "native_by_page": {}}
        for slug, hero in HEROES.items():
            h, used = cards_html(pool, ids, exclude=hero)
            out["slots"][slot]["html_by_page"][slug] = h
            out["slots"][slot]["count_by_page"][slug] = len(used)
            tw = TOWN_OF_SLUG.get(slot)
            out["slots"][slot]["native_by_page"][slug] = sum(1 for i in used if tw and tw in towns(pool[i]))
    json.dump(out, io.open(os.path.join(HERE, "gyg-cards.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    def og_meta(slug):
        return ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">' % out["og"][slug])

    # hand-written pages
    idx = os.path.join(SITE, "index.html")
    inject(idx, "home-og", og_meta("index"), inline=True)
    inject(idx, "home-boat", cards_html(pool, SLOTS["boat-near"], exclude=HEROES["index"], limit=5)[0])
    inject(idx, "home-kayak", cards_html(pool, SLOTS["kayak"], limit=3)[0])
    inject(idx, "home-cat", cards_html(pool, SLOTS["cat-dolphin"], exclude=HEROES["index"], limit=4)[0])
    inject(idx, "home-availability", widget_availability(HEROES["index"]))
    inject(idx, "home-availability-lead", out["hero_meta"]["index"]["lead"], inline=True)
    inject(idx, "home-auto", widget_auto())
    inject(idx, "home-note", DISCLAIMER)

    ops = os.path.join(SITE, "operators.html")
    inject(ops, "ops-og", og_meta("operators"), inline=True)
    inject(ops, "ops-near", cards_html(pool, SLOTS["boat-near"], exclude=HEROES["operators"])[0])
    inject(ops, "ops-kayak", cards_html(pool, SLOTS["kayak"])[0])
    inject(ops, "ops-cat", cards_html(pool, SLOTS["cat-dolphin"], exclude=HEROES["operators"])[0])
    inject(ops, "ops-availability", widget_availability(HEROES["operators"]))
    inject(ops, "ops-availability-lead", out["hero_meta"]["operators"]["lead"], inline=True)
    inject(ops, "ops-auto", widget_auto())
    inject(ops, "ops-note", DISCLAIMER)
    # inline "on GetYourGuide" links inside the editorial profiles (empty when the operator has no listing)
    for key, pat in OPLINKS.items():
        # never the page's own hero (it has the pinned calendar) - one ask per product per page
        hits = [i for i, t in pool.items() if re.search(pat, t.get("provider") or "", re.I) and i != HEROES["operators"]]
        hits.sort(key=lambda i: (-reviews(pool[i]), -value(pool[i])))
        if hits:
            t = pool[hits[0]]
            link = (' Also bookable <a class="vlink op-book" data-vurl="%s" role="link" rel="sponsored nofollow noopener" tabindex="0">on GetYourGuide (%s, %.1f&#9733;, %s reviews) &#8594;</a>'
                    % (b64(aff_url(t)), html.escape(price(t)), rating(t), format(reviews(t), ",")))
        else:
            link = ""
        inject(ops, "oplink-" + key, link, inline=True)

    worth = os.path.join(SITE, "benagil-cave-worth-it.html")
    inject(worth, "worth-og", og_meta("benagil-cave-worth-it"), inline=True)
    inject(worth, "worth-availability", widget_availability(HEROES["benagil-cave-worth-it"]))
    inject(worth, "worth-availability-lead", out["hero_meta"]["benagil-cave-worth-it"]["lead"], inline=True)
    inject(worth, "worth-auto", widget_auto())

    # report
    print("pool (base-true, both shelves):", len(pool))
    for slug, tid in HEROES.items():
        t = pool[tid]
        print("HERO %-40s t%-8d %-6s %.1f/%-5d %s | %s" % (slug, tid, price(t), rating(t), reviews(t), clean_title(t)[:60], ",".join(towns(t))))
    used = sorted({i for ids in SLOTS.values() for i in ids[:CARDS_PER_SLOT + 1]} | set(HEROES.values()))
    print("distinct tours placed (approx):", len(used))
    for slot, ids in SLOTS.items():
        print("  slot %-40s n=%d top: %s" % (slot, len(ids), ids[:6]))
    print("wrote gyg-cards.json; injected index/operators/worth-it")


if __name__ == "__main__":
    main()
