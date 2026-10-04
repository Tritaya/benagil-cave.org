# -*- coding: utf-8 -*-
"""Build the GetYourGuide card blocks for benagil-cave.org from the offers JSON files in this
folder (both shelves: benagil-l163460 city page + benagil-sea-cave-l89246 POI page), and inject
them into the hand-written pages (index.html, operators.html, benagil-cave-worth-it.html)
between <!-- GYG:name --> markers. The town-page generator (_gen_town_pages.py) reads
gyg-cards.json.

Slots are SELECTORS (departure town x craft), not hand-picked id lists; the order on the page is
the stated rule: value (price x rating) desc, then reviews desc. Floors keep 5-review products
off the page. HERO_OVERRIDES exists for a deliberate editorial pick; print the chosen heroes.

Lanes (partner-global cmp namespace, hostname prefix, device-named; since 2026-09-14):
  benagil-cave-btc  product links on cards
  benagil-cave-bti  inline "on GetYourGuide" links inside operator profiles
  benagil-cave-bt   the pinned availability calendar (one per page, id="availability")
  benagil-cave-a    the auto widget end slot
  benagil-cave      the loader's default only (data-gyg-partner-cmp)
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
CMP = "benagil-cave"   # hostname without TLD, like the rest of the partner account (was "bcorg" until 2026-09-14)
# lanes name the DEVICE (_CTA-KIT.md): <site>-btc product cards, <site>-bti inline "on GetYourGuide" links in
# operator profiles, <site>-bt the pinned availability widget, <site>-a the auto widget, bare <site> = loader fallback
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
    # the three hub pages argue for the Carvoeiro small boat in their copy; a new near launch with a
    # higher basket must not swap the calendar under that copy (t732531 did, 2026-09-13)
    "index": 421964,
    "operators": 421964,
    "benagil-cave-worth-it": 421964,
    # the kayak page is written around the max-6 5.0/547 paddle; t732531 (a kayak tour whose title
    # omits the word) out-baskets it by $5 and must not take the calendar
    "benagil-cave-kayak": 670049,
    # Faro: the page's verdict is "most Faro day trips never go on the water; this one does" - the
    # calendar is the boat (t874501, boards at Armacao de Pera), never the 3,302-review clifftop day
    # t304398 ("This is not a boat tour"), which is a choice card instead (2026-10-04)
    "benagil-cave-tour-from-faro": 874501,
    # Lisbon: the most-reviewed day trip that includes the cave boat (sea and availability permitting)
    "benagil-cave-tour-from-lisbon": 847548,
}
# site-hosted hero (img/<file>.webp, stamped "benagil-cave.org") is the og:image when it exists;
# the GYG 148 image of the pinned tour is the fallback
SITE_HERO = {"index": "benagil-cave.webp", "operators": "benagil-cave-tour-operators.webp", "benagil-cave-worth-it": "is-benagil-cave-worth-it.webp",
             "benagil-boat-tour": "benagil-boat-tour.webp", "benagil-cave-kayak": "benagil-cave-kayak-tour.webp"}


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


# "cruise port" is a pickup point, not a boat: it made t650425 / t616467 read "boat included" (2026-10-04)
BOATWORD = re.compile(r"boat|cruise(?!\s*(?:port|ship terminal))|kayak|catamaran|\bsail|\bsup\b|paddle", re.I)


def boat_access(t):
    """Far-origin day trips only (Faro, Lisbon): does the price include getting onto the water?
    'included' / 'optional' (sold as an extra, or the ticket excluded) / 'none' (a clifftop day).
    Most Faro day trips say "This is not a boat tour" (2026-10-04) - their cards must not read
    "Boat, enters the cave". Not applied to local departures, whose excludes often list kayaks."""
    if not far_origin(t):
        return None
    inc = " | ".join(str(x) for x in t.get("includes") or [])
    exc = " | ".join(str(x) for x in t.get("excludes") or [])
    gtk = f(t, "goodToKnow")
    desc = f(t, "description")
    if re.search(r"not a boat tour|land-based tour|without entering it by boat", gtk + " " + desc, re.I):
        return "none"
    # judge each include line on its own: t1060580 includes "1-hour guided kayak tour" AND
    # "(optional) cliff jumping" - the optional is the jump, not the kayak
    boat_lines = [str(x) for x in t.get("includes") or [] if BOATWORD.search(str(x)) and not re.search(r"optional|additional fee|extra cost", str(x), re.I)]
    # t654398: "Benagil Cave boat tour (if group option selected)" - included on one option only (audit 2026-10-04)
    if boat_lines and all(re.search(r"\bif\b[^)]{0,40}option", x, re.I) for x in boat_lines):
        return "partial"
    if boat_lines:
        return "included"
    if BOATWORD.search(inc + " " + exc + " " + gtk) and re.search(r"optional|additional fee|extra cost", inc + " " + exc + " " + gtk, re.I):
        return "optional"
    # t625908: the boat is a fixed itinerary stop but "Boat tour ticket" is excluded - not optional, a
    # separate ticket (and its listing refuses refunds if the sea cancels the boat) (audit 2026-10-04)
    if BOATWORD.search(exc) and re.search(r"(embark|board)[^.]{0,60}boat|boat (tour|ride|trip) (to|into|inside)", desc, re.I):
        return "ticket"
    if BOATWORD.search(exc):
        return "none"
    return None


def craft(t):
    title = f(t, "title")
    if boat_access(t) in ("none", "optional", "ticket"):
        return "land"
    if KAYAK.search(title):
        return "kayak"
    if CAT.search(title) or re.search(r"catamaran", f(t, "description")[:400], re.I):   # "sail along the coast" in a small boat's blurb is not a catamaran
        return "cat"
    # a title can omit the craft: t732531 "Benagil: Caves & Wild Beaches Tour w/ Local Guide, 4K Photos"
    # is a paddle ("Paddle to secluded secret sea caves") and shipped as a small boat and a page hero
    body = f(t, "highlights") + " " + f(t, "description")[:600] + " " + f(t, "includes")
    if len(KAYAK.findall(body)) > len(re.findall(r"\bboat|\brib\b|speedboat|vessel|skipper", body, re.I)):
        return "kayak"
    return "boat"


FAR_ORIGIN = re.compile(r"lisbon|lisboa|sevill|faro\b|olh[aã]o|tavira|quarteira|vilamoura|sintra|porto\b", re.I)
NOT_CAVE_TRIP = re.compile(r"\bhik|walk|trek|e-?bike|bike|jeep|safari|buggy|quad|tuk|segway|charter|yacht|4x4|castle|silves|monchique|winery|vineyard|city tour", re.I)


def title_prefix_town(t):
    """'From Portimão: ...' / 'Albufeira: ...' names the DEPARTURE. Itinerary stops do not."""
    m = re.match(r"^\s*(?:from\s+)?([^:]{3,40}):", f(t, "title"), re.I)
    if not m:
        return None
    pre = m.group(1) + ":"   # keep the colon: the "benagil" pattern is anchored on "benagil:" so it never fires on "Benagil Caves tour" body text
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
    # the meeting fields are often empty while the abstract opens with "Meet at the Portimão pier"
    # (t396968, 13,888 reviews, shipped with no town - audit 2026-09-13): read only meet/depart clauses
    ab = re.sub(r"<[^>]+>", " ", f(t, "description") or f(t, "abstract"))[:500]   # the v10 JSON keeps the text in "description"; "abstract" is None
    clause_town = None
    for m in re.finditer(r"(?:meet|depart|leav|start|begin|board)[^.]{0,80}", ab, re.I):
        # the FIRST town named after the verb is the departure; later names in the same sentence are
        # destinations ("leaving Albufeira marina towards Benagil and Carvoeiro")
        hits = [(p.search(m.group(0)).start(), k) for k, p in TOWNS.items() if p.search(m.group(0))]
        if hits:
            clause_town = min(hits)[1]
            break
    it = t.get("itinerary") or []
    if isinstance(it, list):
        for step in it:
            if isinstance(step, dict) and re.search(r"pickup|starting|meeting|departure", str(step.get("name", "")), re.I):
                pk += " " + str(step.get("description", ""))
    if FAR_ORIGIN.search(pk) and not any(p.search(pk) for p in TOWNS.values()):
        return []
    tw = [k for k, p in TOWNS.items() if p.search(pk)]
    if not tw and clause_town:
        tw = [clause_town]
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
    ba = boat_access(t)
    if ba is not None:   # a day trip by road from Faro or Lisbon: say what happens at the cave
        return {"none": "Day trip by road; views the cave from the clifftop, no boat",
                "optional": "Day trip by road; the cave boat is optional, at extra cost",
                "ticket": "Day trip by road; a boat stop on the itinerary, but the boat ticket costs extra",
                "partial": "Day trip by road; boat included on the small-group option only",
                "included": "Day trip by road + %s to the cave, sea permitting" % ("guided kayak" if c == "kayak" else "boat")}[ba]
    tw = towns(t)
    parts = []
    if is_private(t) and not far_origin(t):
        # a hull hired for your group: "yacht" matches the catamaran pattern, and the listings do not
        # say whether a charter goes in or holds at the arch (2026-10-04). Capacity from GYG's own unit.
        cap = re.search(r"up to (\d+)", t.get("priceCategory") or "")
        return ("Private charter for up to %s" % cap.group(1) if cap else "Private charter for your group") + \
               (", from " + " / ".join(TOWN_LABEL[x] for x in tw[:2]) if tw else "")
    parts.append({"kayak": "Guided kayak/SUP into the cave", "cat": "Catamaran, views the cave from the entrance", "boat": "Boat, enters the cave sea permitting"}[c])
    if tw:
        parts.append("from " + " / ".join(TOWN_LABEL[x] for x in tw[:2]))
    if DOLPH.search(f(t, "title")):
        parts.append("+ dolphins")
    return ", ".join(parts[:2]) + (" " + parts[2] if len(parts) > 2 else "")


def bare_url(t):
    return (t.get("url") or "").split("?")[0]


def aff_url(t, device="btc"):
    return "%s?partner_id=%s&utm_medium=online_publisher&cmp=%s-%s" % (bare_url(t), PARTNER, CMP, device)


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
        # GetYourGuide's own "Top pick" badge reads as OUR pick next to a pinned calendar; dropped (audit 2026-09-13)
        if b.startswith("#1 selling") or b in ("Top rated", "Likely to sell out", "Certified by GetYourGuide", "Official ticket"):
            return b
    return t.get("bookedRecentlyText") or ""


def card(t, rank):
    e = lambda s: html.escape(str(s), quote=True)
    c = craft(t)
    meta = ['<span class="ec-rating">%.1f&#9733; (%s)</span>' % (rating(t), format(reviews(t), ","))]
    if price(t):
        meta.append('<span class="ec-price">from %s</span>' % e(price(t)))
    if not (is_private(t) and not far_origin(t)):   # a charter's chip is "Private, priced per boat" alone
        meta.append('<span class="ec-reach ec-reach-%s">%s</span>' % ("boat" if c == "land" else c, {"kayak": "Kayak / SUP", "cat": "Catamaran", "boat": "Boat", "land": {"none": "Clifftop, no boat", "ticket": "Boat ticket extra", "partial": "Boat on one option"}.get(boat_access(t), "Boat optional")}[c]))
    if is_private(t):
        meta.append('<span class="ec-reach ec-reach-cat">Private, priced per boat</span>')
    # 2,000+ reviews is the more useful chip than any platform badge ("Certified by GetYourGuide"
    # was hiding "Most booked" on the 13,888-review RIB)
    # literal, not "Most booked": with the most-booked rows a page carried four "Most booked" chips (audit 2026-10-04)
    b = "2,000+ reviews" if reviews(t) >= 2000 else badge(t)
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
    # GYG's own price unit decides first: "per group up to 10" is a hull, "per person" is a seat.
    # The keyword rule flagged t847548 ($181 per person, Lisbon day trip) as private because its
    # text offers a "private hotel pickup" option (2026-10-04).
    pc = (t.get("priceCategory") or "").lower()
    if pc:
        return "group" in pc
    hay = " ".join((f(t, "title"), f(t, "url"), f(t, "description")[:600]))
    # ... and the word alone is not enough either: t390616's slug says "private-guided-boat-tour"
    # at $37 with 434 reviews, which is a per-person seat (audit, 2026-09-13). A hull costs hundreds.
    return bool(re.search(r"\bprivate\b|\bprivado\b|per boat|per group|whole boat|exclusive use", hay, re.I)) and price_num(t) >= 150


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
    # ... and so does the CHEAPEST per-person seat, so a "from $23" in the prose always has a card
    # behind it (the kayak page said $23 over a list whose cheapest card was $34 - audit 2026-09-13)
    musts = []
    if ids:
        musts.append(max(ids, key=lambda i: reviews(pool[i])))
        pp = [i for i in ids if not is_private(pool[i])]
        if pp:
            musts.append(min(pp, key=lambda i: price_num(pool[i])))
    for m in musts:
        if m not in shown:
            if len(shown) >= limit:
                shown.remove([i for i in shown if i not in musts][-1])
            shown.append(m)
    return '<ol class="ec-tours">\n' + "\n".join(card(pool[i], n + 1) for n, i in enumerate(shown)) + "\n    </ol>", shown


def widget_availability(tid):
    return ('<div class="avail-widget" id="availability">\n'
            '      <div data-gyg-widget="availability" data-gyg-tour-id="%d" data-gyg-partner-id="%s" data-gyg-cmp="%s-bt" data-gyg-locale-code="en-US" data-gyg-currency="USD"></div>\n'
            '    </div>' % (tid, PARTNER, CMP))


def widget_auto():
    return '<div data-gyg-widget="auto" data-gyg-partner-id="%s" data-gyg-cmp="%s-a" data-gyg-locale-code="en-US" data-gyg-currency="USD"></div>' % (PARTNER, CMP)


DISCLAIMER = ('<p class="t-note ec-note">Prices are GetYourGuide "from" prices in US dollars, per person unless the card says "priced per boat", ratings and review counts as captured 12 September 2026; '
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


FAR_TOWNS = {   # day trips BY ROAD from cities with no Benagil launch (2026-10-04, inbox-20261004-002)
    "benagil-cave-tour-from-faro": re.compile(r"\bfaro\b", re.I),
    "benagil-cave-tour-from-lisbon": re.compile(r"lisbon|lisboa", re.I),
}
FAR_NOT = re.compile(r"\bhik|e-?bike|\bbike|jeep|buggy|quad|segway|yacht|charter", re.I)
MOSTBOOKED_MIN = 500   # "most booked" must mean it: a row of 30-review products would be a second list, not a signal
MOSTBOOKED_N = 3


def main():
    everything = load()
    pool = {i: t for i, t in everything.items() if base_true(t)}
    # far pool: Benagil day trips from Faro / Lisbon (never base-true: they are not Benagil departures)
    far_pool = {i: t for i, t in everything.items()
                if i not in pool and BEN.search(f(t, "title") + " " + f(t, "description")) and far_origin(t)
                and not FAR_NOT.search(f(t, "title")) and not is_private(t)}
    # private hulls and yachts that LEAVE from the coast (base-true filters charters out of the main lists)
    priv_pool = {i: t for i, t in everything.items()
                 if i not in pool and BEN.search(f(t, "title") + " " + f(t, "description")) and not far_origin(t)
                 and is_private(t) and craft(t) != "kayak"}
    pool_all = dict(pool)
    pool_all.update(far_pool)
    pool_all.update(priv_pool)
    is_kayak = lambda t: craft(t) == "kayak"
    is_speed = lambda t: craft(t) == "boat" and (SPEED.search(f(t, "title") + " " + f(t, "includes") + " " + f(t, "description")[:300]) is not None)
    near = lambda t: craft(t) != "kayak" and any(x in towns(t) for x in ("carvoeiro", "armacao", "benagil"))
    # catamarans and dolphin combos by what they ARE, not by where they leave from: the old town rule
    # filed the Portimão speedboat t397931 under "catamarans" (audit 2026-09-13)
    catd = lambda t: craft(t) != "kayak" and not is_speed(t) and (craft(t) == "cat" or DOLPH.search(f(t, "title")) is not None)
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
    is_kayak_only = lambda t: craft(t) == "kayak" and not is_sup(t)
    SLOTS = {
        "boat-near": near_ids,
        "kayak": ranked(pool, is_kayak, CARD_MIN_REVIEWS),
        "cat-dolphin": catd_ids,
        # the home/operators group is headed "Catamarans, speedboats & dolphins": catamarans, dolphin
        # combos AND the speedboats, so the $14 RIB has a card wherever a chart says "from $14"
        "cat-speed": ranked(pool, lambda t: catd(t) or is_speed(t), CARD_MIN_REVIEWS),
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
    for slug, pat in FAR_TOWNS.items():
        SLOTS[slug] = ranked(far_pool, lambda t, p=pat: p.search(f(t, "title")) is not None, CARD_MIN_REVIEWS)
    # private boats/yachts from the coast, plus any private hull already in the main pool
    SLOTS["private"] = ranked(pool_all, lambda t: is_private(t) and not far_origin(t) and craft(t) != "kayak", CARD_MIN_REVIEWS)

    def pick_hero(slug, ids):
        """Hero = the calendar: a per-person BOAT with a real review base (the town pages are written
        around boats; a kayak hero on the Carvoeiro page contradicted its own copy - audit 2026-09-12),
        then any per-person tour, never a private hull."""
        if slug in HERO_OVERRIDES:
            return HERO_OVERRIDES[slug]
        for want_boat in (True, False):
            for i in ids:
                t = pool_all[i]
                if reviews(t) >= HERO_MIN_REVIEWS and not is_private(t) and craft(t) != "land" and (craft(t) != "kayak" or not want_boat):
                    return i
        for i in ids:
            if not is_private(pool_all[i]):
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
    for slug in FAR_TOWNS:
        HEROES[slug] = pick_hero(slug, SLOTS[slug])

    out = {"partner": PARTNER, "cmp": CMP, "stamp": "12 September 2026", "heroes": HEROES, "slots": {}, "og": {}, "hero_meta": {},
           "disclaimer": DISCLAIMER, "widget_auto": widget_auto(), "mostbooked": {}, "private_row": {}}
    for slug, tid in HEROES.items():
        t = pool_all[tid]
        site_file = SITE_HERO.get(slug, slug + ".webp")
        out["og"][slug] = ("https://benagil-cave.org/img/" + site_file) if os.path.exists(os.path.join(HERE, "..", "img", site_file)) else og_image(t)
        out["hero_meta"][slug] = {"id": tid, "title": clean_title(t), "price": price(t), "rating": rating(t), "reviews": reviews(t),
                                  "aff": aff_url(t), "widget": widget_availability(tid), "lead": hero_lead(pool_all, tid)}
    TOWN_OF_SLUG = {"benagil-cave-tour-from-carvoeiro": "carvoeiro", "benagil-cave-tour-from-armacao-de-pera": "armacao",
                    "benagil-cave-tour-from-portimao": "portimao", "benagil-cave-tour-from-albufeira": "albufeira",
                    "benagil-cave-tour-from-lagos": "lagos"}
    for slot, ids in SLOTS.items():
        out["slots"][slot] = {"ids": ids, "html_by_page": {}, "count_by_page": {}, "native_by_page": {}}
        for slug, hero in HEROES.items():
            h, used = cards_html(pool_all, ids, exclude=hero)
            out["slots"][slot]["html_by_page"][slug] = h
            out["slots"][slot]["count_by_page"][slug] = len(used)
            tw = TOWN_OF_SLUG.get(slot)
            out["slots"][slot]["native_by_page"][slug] = sum(1 for i in used if tw and tw in towns(pool_all[i]))

    # "Most booked" rows (user decision 2026-10-04, inbox-20261004-002 card sweep): the card lists stay
    # value-ordered and capped; underneath, the page's own departures with the most reviews that the
    # cap left out - so the $14 Portimao RIB with 8,920 reviews is on the Portimao page.
    def mostbooked(slug, own_ids, list_slot):
        _, used = cards_html(pool_all, SLOTS[list_slot], exclude=HEROES[slug])
        cand = [i for i in own_ids if i not in used and i != HEROES[slug] and not is_private(pool_all[i])
                and reviews(pool_all[i]) >= MOSTBOOKED_MIN]
        cand.sort(key=lambda i: -reviews(pool_all[i]))
        cand = cand[:MOSTBOOKED_N]
        if not cand:
            return "", []
        return '<ol class="ec-tours">\n' + "\n".join(card(pool_all[i], n + 1) for n, i in enumerate(cand)) + "\n    </ol>", cand
    for slug, tw in TOWN_OF_SLUG.items():
        h, ids = mostbooked(slug, ranked(pool, town_sel(tw), CARD_MIN_REVIEWS), slug)
        out["mostbooked"][slug] = {"html": h, "ids": ids}
    # what the far pages actually SHOW (pinned + cards), so their prose counts cannot drift from the
    # list: the Lisbon page said "3 of 8" over seven trips (audit 2026-10-04)
    out["far_stats"] = {}
    for slug in FAR_TOWNS:
        _, used = cards_html(pool_all, SLOTS[slug], exclude=HEROES[slug])
        shown = [HEROES[slug]] + used
        st = {"shown": len(shown)}
        for i in shown:
            k = boat_access(pool_all[i]) or "none"
            st[k] = st.get(k, 0) + 1
        st["min_price_none"] = min((price_num(pool_all[i]) for i in shown if boat_access(pool_all[i]) == "none"), default=0)
        st["min_price"] = min(price_num(pool_all[i]) for i in shown)
        out["far_stats"][slug] = st
    h, ids = mostbooked("benagil-cave-kayak", SLOTS["kayak"], "kayak-only")
    out["mostbooked"]["benagil-cave-kayak"] = {"html": h, "ids": ids}
    # private charters row for the boat page: never a product the page already shows
    boat_used = {HEROES["benagil-boat-tour"]}
    for s in ("speedboat", "boat-near", "cat-dolphin"):   # the groups the boat page renders
        boat_used.update(cards_html(pool_all, SLOTS[s], exclude=HEROES["benagil-boat-tour"])[1])
    priv = [i for i in SLOTS["private"] if i not in boat_used]
    h, used = cards_html(pool_all, priv, limit=3) if priv else ("", [])
    out["private_row"]["benagil-boat-tour"] = {"html": h, "ids": used}
    json.dump(out, io.open(os.path.join(HERE, "gyg-cards.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    def og_meta(slug):
        return ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">' % out["og"][slug])

    # hand-written pages
    idx = os.path.join(SITE, "index.html")
    inject(idx, "home-og", og_meta("index"), inline=True)
    inject(idx, "home-boat", cards_html(pool, SLOTS["boat-near"], exclude=HEROES["index"], limit=5)[0])
    inject(idx, "home-kayak", cards_html(pool, SLOTS["kayak"], limit=3)[0])
    inject(idx, "home-cat", cards_html(pool, SLOTS["cat-speed"], exclude=HEROES["index"], limit=4)[0])
    inject(idx, "home-availability", widget_availability(HEROES["index"]))
    inject(idx, "home-availability-lead", out["hero_meta"]["index"]["lead"], inline=True)
    inject(idx, "home-auto", widget_auto())
    inject(idx, "home-note", DISCLAIMER)

    ops = os.path.join(SITE, "operators.html")
    inject(ops, "ops-og", og_meta("operators"), inline=True)
    inject(ops, "ops-near", cards_html(pool, SLOTS["boat-near"], exclude=HEROES["operators"])[0])
    inject(ops, "ops-kayak", cards_html(pool, SLOTS["kayak"])[0])
    inject(ops, "ops-cat", cards_html(pool, SLOTS["cat-speed"], exclude=HEROES["operators"])[0])
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
                    % (b64(aff_url(t, "bti")), html.escape(price(t)), rating(t), format(reviews(t), ",")))
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
        t = pool_all[tid]
        print("HERO %-40s t%-8d %-6s %.1f/%-5d %s | %s" % (slug, tid, price(t), rating(t), reviews(t), clean_title(t)[:60], ",".join(towns(t))))
    used = sorted({i for ids in SLOTS.values() for i in ids[:CARDS_PER_SLOT + 1]} | set(HEROES.values()))
    print("distinct tours placed (approx):", len(used))
    for slot, ids in SLOTS.items():
        print("  slot %-40s n=%d top: %s" % (slot, len(ids), ids[:6]))
    print("wrote gyg-cards.json; injected index/operators/worth-it")


if __name__ == "__main__":
    main()
