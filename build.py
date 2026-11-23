#!/usr/bin/env python3
"""Erzeugt die Kalender 'KI - Sport' (ICS) und die Übersichtsseite aus der öffentlichen ESPN-API.

Aufruf: python3 build.py [Zielordner]   (Standard: aktueller Ordner)
"""
import datetime as dt
import html
import json
import os
import sys
import urllib.request
from zoneinfo import ZoneInfo

B = "https://site.api.espn.com/apis/"
TZ = ZoneInfo("Europe/Vienna")
UTC = dt.timezone.utc
REPO_RAW = "https://raw.githubusercontent.com/hyr9fg2rrz-oss/ki-sport/main/"

# ---------------------------------------------------------------- Konfiguration
FAV_SOCCER = {  # ESPN-ID: (Name, Wettbewerbe)
    "519":  ("Rapid Wien",      ["aut.1", "uefa.champions", "uefa.europa", "uefa.europa.conf"]),
    "359":  ("Arsenal",         ["eng.1", "eng.fa", "eng.league_cup", "uefa.champions", "uefa.europa"]),
    "382":  ("Manchester City", ["eng.1", "eng.fa", "eng.league_cup", "uefa.champions", "uefa.europa"]),
    "112":  ("Lazio",           ["ita.1", "ita.coppa_italia", "ita.super_cup", "uefa.champions", "uefa.europa", "uefa.europa.conf"]),
    "104":  ("AS Roma",         ["ita.1", "ita.coppa_italia", "ita.super_cup", "uefa.champions", "uefa.europa", "uefa.europa.conf"]),
    "110":  ("Inter",           ["ita.1", "ita.coppa_italia", "ita.super_cup", "uefa.champions", "uefa.europa"]),
    "103":  ("AC Milan",        ["ita.1", "ita.coppa_italia", "ita.super_cup", "uefa.champions", "uefa.europa"]),
    "1068": ("Atlético Madrid", ["esp.1", "esp.copa_del_rey", "esp.super_cup", "uefa.champions", "uefa.europa"]),
    "86":   ("Real Madrid",     ["esp.1", "esp.copa_del_rey", "esp.super_cup", "uefa.champions", "uefa.europa"]),
    "83":   ("FC Barcelona",    ["esp.1", "esp.copa_del_rey", "esp.super_cup", "uefa.champions", "uefa.europa"]),
}
FAV_US = {"nfl": {"12": "Kansas City Chiefs", "4": "Cincinnati Bengals"},
          "college-football": {"251": "Texas Longhorns", "194": "Ohio State"}}
TOP_LEAGUES = {"eng.1": "Premier League", "ger.1": "Bundesliga", "esp.1": "LaLiga", "ita.1": "Serie A"}
TOP_N = 6            # Topspiel = beide Teams aktuell unter den Top 6
UCL_BIG_LEAGUES = ["eng.1", "ger.1", "esp.1", "ita.1", "fra.1"]  # "große Klubs" für CL-Topspiele

# Derbys & Klassiker: immer ⭐, egal wie die Tabelle steht. (Sport, Liga, Team A, Team B, Name)
DERBIES = [
    ("soccer", ["aut.1"], "519", "1382", "Wiener Derby"),
    ("soccer", ["esp.1", "esp.copa_del_rey", "esp.super_cup", "uefa.champions"], "86", "83", "El Clásico"),
    ("soccer", ["esp.1", "esp.copa_del_rey", "esp.super_cup", "uefa.champions"], "86", "1068", "Derbi madrileño"),
    ("soccer", ["ita.1", "ita.coppa_italia", "ita.super_cup"], "104", "112", "Derby della Capitale"),
    ("soccer", ["ita.1", "ita.coppa_italia", "ita.super_cup", "uefa.champions"], "110", "103", "Derby della Madonnina"),
    ("soccer", ["ita.1", "ita.coppa_italia", "ita.super_cup"], "110", "111", "Derby d'Italia"),
    ("soccer", ["eng.1", "eng.fa", "eng.league_cup"], "359", "367", "North London Derby"),
    ("soccer", ["eng.1", "eng.fa", "eng.league_cup"], "382", "360", "Manchester Derby"),
    ("soccer", ["ger.1"], "132", "124", "Der Klassiker"),
    ("college-football", ["college-football"], "194", "130", "The Game"),
]

# TV-Rechte (Saison 2026/27, ohne Gewähr). USA bei NFL/NCAA kommt spielgenau von ESPN.
TV = {
    "eng.1": {"UK": "Sky Sports / TNT Sports", "DE": "Sky", "AT": "Sky", "USA": "NBC / Peacock / USA Network"},
    "ger.1": {"UK": "Sky Sports", "DE": None, "AT": "Sky", "USA": "ESPN+"},
    "esp.1": {"UK": "Premier Sports", "DE": "DAZN", "AT": "DAZN", "USA": "ESPN+ / ESPN"},
    "ita.1": {"UK": "TNT Sports", "DE": "DAZN", "AT": "DAZN", "USA": "Paramount+ / CBS"},
    "aut.1": {"AT": "Sky (ausgew. Spiele ORF)"},
    "uefa.champions": {"UK": "TNT Sports / Prime Video (Di-Topspiel)", "DE": "DAZN / Prime Video (Di-Topspiel)",
                       "AT": "Sky", "USA": "Paramount+ / CBS"},
    "uefa.europa": {"UK": "TNT Sports", "DE": "RTL+", "AT": "Sky", "USA": "Paramount+"},
    "uefa.europa.conf": {"UK": "TNT Sports", "DE": "RTL+", "AT": "Sky", "USA": "Paramount+"},
    "eng.fa": {"UK": "BBC / TNT Sports", "USA": "ESPN+"},
    "eng.league_cup": {"UK": "Sky Sports", "USA": "Paramount+"},
    "nfl": {"UK": "Sky Sports NFL / DAZN Game Pass", "DE": "RTL / Nitro / RTL+ / Sky", "AT": "Sky / DAZN Game Pass"},
}

CALENDARS = {  # Datei: (Name, Filter)
    "ki-sport.ics":    ("KI - Sport", lambda ev: True),
    "meine-teams.ics": ("KI - Sport · Meine Teams", lambda ev: ev["group"] == "teams"),
    "topspiele.ics":   ("KI - Sport · Topspiele", lambda ev: ev["group"] == "top"),
    "playoffs.ics":    ("KI - Sport · Playoffs", lambda ev: ev["group"] == "playoff"),
}
ALARM_MIN = 30


# ---------------------------------------------------------------- Hilfsfunktionen
def get(path):
    try:
        with urllib.request.urlopen(B + path, timeout=30) as r:
            return json.load(r)
    except Exception as e:  # einzelne fehlende Wettbewerbe sind normal (400/404)
        print("WARN", path, e, file=sys.stderr)
        return {}


def soccer_schedule(lg, tid):
    for q in ("", "?fixture=true"):
        yield from get(f"site/v2/sports/soccer/{lg}/teams/{tid}/schedule{q}").get("events", [])


def standings_ids(lg, n):
    st = get(f"v2/sports/soccer/{lg}/standings")
    try:
        entries = st["children"][0]["standings"]["entries"]
    except Exception:
        return []
    rank = lambda x: next((s["value"] for s in x["stats"] if s["name"] == "rank"), 99)
    return [x["team"]["id"] for x in sorted(entries, key=rank)[:n]]


def team_ids(e):
    return {x["team"]["id"] for x in e["competitions"][0].get("competitors", [])}


def tv_ger(local):
    wd, h = local.weekday(), local.hour
    if wd == 6:
        return "DAZN"
    if wd == 5 and h == 15:
        return "Sky (Einzelspiele) / DAZN (Konferenz)"
    return "Sky"


def name(x, short=False):
    if not x:
        return "TBD"
    t = x["team"]
    n = (t.get("shortDisplayName") if short else None) or t.get("displayName") or t.get("name") or "TBD"
    r = (x.get("curatedRank") or {}).get("current")
    return f"#{r} {n}" if r and r <= 25 else n


def score(x):
    s = x.get("score") if x else None
    return s.get("displayValue") if isinstance(s, dict) else s


def record(x):
    for r in (x or {}).get("records", []) or []:
        if r.get("type") == "total":
            try:
                w, l, *_ = map(int, r["summary"].split("-"))
                return w, l
            except Exception:
                pass
    return None


def thanksgiving(y):
    d = dt.date(y, 11, 1)
    return d + dt.timedelta(days=(3 - d.weekday()) % 7 + 21)


# ---------------------------------------------------------------- Spiele sammeln
events = {}


def add(e, comp, tag=None, fav=None, top=False, playoff=False, derby=None, label=None):
    ev = events.get(e["id"])
    if not ev:
        c = e["competitions"][0]
        side = {x.get("homeAway"): x for x in c.get("competitors", [])}
        st = c["status"]["type"]
        venue = c.get("venue", {})
        ev = events[e["id"]] = dict(
            date=e["date"], comp=comp, label=label or (e.get("league") or {}).get("name") or comp,
            tags=set(), favs=set(), top=False, playoff=False, derby=None,
            home=side.get("home"), away=side.get("away"), status=st,
            notes=[n.get("headline") for n in c.get("notes", []) if n.get("headline")],
            us_tv=sorted({n for b in c.get("broadcasts", []) for n in b.get("names", [])}),
            time_valid=c.get("timeValid", True) and st.get("name") != "STATUS_TBD",
            loc=", ".join(filter(None, [venue.get("fullName"), venue.get("address", {}).get("city")])),
            week=(e.get("week") or {}).get("number"))
    if tag: ev["tags"].add(tag)
    if fav: ev["favs"].add(fav); ev["tags"].add(fav)
    ev["top"] |= top
    ev["playoff"] |= playoff
    if derby: ev["derby"] = derby; ev["tags"].add(derby)


# Fußball: Lieblingsteams
for tid, (team, leagues) in FAV_SOCCER.items():
    for lg in leagues:
        for e in soccer_schedule(lg, tid):
            add(e, lg, fav=team)

# Fußball: Topspiele der großen Ligen (Top 6 gegen Top 6)
big_clubs = set()
for lg in UCL_BIG_LEAGUES:
    top = set(standings_ids(lg, TOP_N))
    big_clubs |= top
    if lg not in TOP_LEAGUES:
        continue
    for tid in top:
        for e in soccer_schedule(lg, tid):
            if team_ids(e) <= top:
                add(e, lg, tag=f"Topspiel {TOP_LEAGUES[lg]}", top=True)
big_clubs |= set(FAV_SOCCER) - {"519"}  # deine großen Klubs zählen immer

# Champions League: große Klubs gegeneinander
for tid in sorted(big_clubs):
    for e in soccer_schedule("uefa.champions", tid):
        if len(team_ids(e)) == 2 and team_ids(e) <= big_clubs:
            add(e, "uefa.champions", tag="Topspiel Champions League", top=True)

# Derbys & Klassiker
for sport, leagues, a, b, dname in DERBIES:
    for lg in leagues:
        if sport == "soccer":
            evs = soccer_schedule(lg, a)
        else:
            evs = []
            for stp in ("2", "3"):
                evs += get(f"site/v2/sports/football/{lg}/teams/{a}/schedule?seasontype={stp}").get("events", [])
        for e in evs:
            if {a, b} <= team_ids(e):
                add(e, "ncaaf" if sport != "soccer" else lg, top=True, derby=dname,
                    label="NCAA Football" if sport != "soccer" else None)

# NFL
for wk in range(1, 19):
    for e in get(f"site/v2/sports/football/nfl/scoreboard?seasontype=2&week={wk}").get("events", []):
        c = e["competitions"][0]
        ids = {x["team"]["id"]: x for x in c["competitors"]}
        for tid, team in FAV_US["nfl"].items():
            if tid in ids:
                add(e, "nfl", fav=team, label="NFL")
        recs = [record(x) for x in ids.values()]
        good = all(r and sum(r) >= 3 and r[0] / sum(r) >= 0.6 for r in recs)
        kick = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        us_day = (kick - dt.timedelta(hours=5)).date()
        prime = kick.hour < 6 or us_day in (thanksgiving(us_day.year), dt.date(us_day.year, 12, 25))
        if good or prime:
            add(e, "nfl", tag="NFL-Topspiel" if good else "NFL Primetime", top=True, label="NFL")
for wk in range(1, 6):
    for e in get(f"site/v2/sports/football/nfl/scoreboard?seasontype=3&week={wk}").get("events", []):
        if "pro bowl" not in e.get("name", "").lower():
            add(e, "nfl", tag="NFL Playoffs", playoff=True, label="NFL Playoffs")
            for tid, team in FAV_US["nfl"].items():
                if tid in team_ids(e):
                    add(e, "nfl", fav=team)

# College Football
for wk in range(1, 17):
    for e in get(f"site/v2/sports/football/college-football/scoreboard?seasontype=2&week={wk}&groups=80&limit=400").get("events", []):
        c = e["competitions"][0]
        ids = {x["team"]["id"]: x for x in c["competitors"]}
        for tid, team in FAV_US["college-football"].items():
            if tid in ids:
                add(e, "ncaaf", fav=team, label="NCAA Football")
        ranks = [(x.get("curatedRank") or {}).get("current", 99) for x in ids.values()]
        champ = any("championship" in (n.get("headline") or "").lower() for n in c.get("notes", []))
        if all(r <= 25 for r in ranks) or (champ and any(r <= 25 for r in ranks)):
            add(e, "ncaaf", tag="NCAA-Topspiel", top=True, label="NCAA Football")
for e in get("site/v2/sports/football/college-football/scoreboard?seasontype=3&groups=80&limit=400").get("events", []):
    notes = " ".join(n.get("headline", "") for n in e["competitions"][0].get("notes", []))
    if "College Football Playoff" in notes:
        add(e, "ncaaf", tag="College Football Playoff", playoff=True, label="NCAA Football Playoff")
        for tid, team in FAV_US["college-football"].items():
            if tid in team_ids(e):
                add(e, "ncaaf", fav=team)

print(len(events), "Events", file=sys.stderr)


# ---------------------------------------------------------------- Aufbereiten
def prepare(eid, ev):
    utc = dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
    kick = utc.astimezone(TZ)
    us = ev["comp"] in ("nfl", "ncaaf")
    h, a = ev["home"], ev["away"]
    match = f"{name(a)} @ {name(h)}" if us else f"{name(h)} – {name(a)}"
    if ev["playoff"] and ev["notes"] and "TBD" in match:
        match = ev["notes"][0]
    result = None
    if ev["status"].get("completed") and score(h) is not None:
        result = f"{score(a)}:{score(h)}" if us else f"{score(h)}:{score(a)}"

    night = ev["time_valid"] and 0 <= kick.hour < 6
    ev["group"] = "teams" if ev["favs"] else ("playoff" if ev["playoff"] else "top")
    icons = ["🏈" if us else "⚽"]
    if ev["playoff"]: icons.append("🏆")
    elif ev["top"] or ev["derby"]: icons.append("⭐")
    if night: icons.append("🌙")
    title = match + (f" ({result})" if result else "")
    if ev["derby"]: title = f"{ev['derby']}: {title}"

    tv = {land: TV.get(ev["comp"], {}).get(land) for land in ("AT", "DE", "UK", "USA")}
    if ev["us_tv"]: tv["USA"] = ", ".join(ev["us_tv"])
    if ev["comp"] == "ger.1": tv["DE"] = tv_ger(kick)
    if ev["comp"] == "nfl" and ev["playoff"]: tv["DE"] = "RTL / RTL+"

    return dict(id=eid, utc=utc, kick=kick, us=us, summary=" ".join(icons + [title]), match=match,
                result=result, night=night, tv=tv, alarm=bool(ev["favs"] or ev["playoff"]),
                icons=icons, **ev)


games = sorted((prepare(k, v) for k, v in events.items()), key=lambda g: g["utc"])


# ---------------------------------------------------------------- ICS schreiben
def esc(s):
    return s.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace("\n", r"\n")


def fold(line):
    b, out = line.encode(), []
    while len(b) > 75:
        cut = 75 if not out else 74
        while (b[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(b[:cut].decode())
        b = b[cut:]
    out.append(b.decode())
    return "\r\n ".join(out)


VTZ = ["BEGIN:VTIMEZONE", "TZID:Europe/Vienna", "X-LIC-LOCATION:Europe/Vienna",
       "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "TZNAME:CEST",
       "DTSTART:19700329T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
       "BEGIN:STANDARD", "TZOFFSETFROM:+0200", "TZOFFSETTO:+0100", "TZNAME:CET",
       "DTSTART:19701025T030000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
       "END:VTIMEZONE"]


def vevent(g, now):
    desc = [g["label"], *g["notes"]]
    if g["week"] and g["us"]: desc.append(f"Woche {g['week']}")
    desc.append("Im Kalender wegen: " + ", ".join(sorted(g["tags"])))
    if g["night"]: desc.append("🌙 Nachtspiel (Wiener Zeit)")
    desc += ["", "📺 TV"]
    for land, flag in (("AT", "🇦🇹"), ("DE", "🇩🇪"), ("UK", "🇬🇧"), ("USA", "🇺🇸")):
        desc.append(f"{flag} {land}: {g['tv'][land] or '–'}")
    desc += ["", f"Status: {g['status'].get('description', '')}"]
    if not g["time_valid"]: desc.append("Anstoßzeit noch offen")
    desc.append("TV außerhalb USA nach Rechtelage 2026/27, ohne Gewähr.")

    L = ["BEGIN:VEVENT", f"UID:espn-{g['id']}@ki-sport", f"DTSTAMP:{now}"]
    if g["time_valid"]:
        end = g["kick"] + dt.timedelta(hours=3.5 if g["us"] else 2)
        L += [f"DTSTART;TZID=Europe/Vienna:{g['kick']:%Y%m%dT%H%M%S}",
              f"DTEND;TZID=Europe/Vienna:{end:%Y%m%dT%H%M%S}"]
    else:
        day = g["utc"].astimezone(dt.timezone(dt.timedelta(hours=-5))).date()
        L += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + dt.timedelta(days=1):%Y%m%d}",
              "TRANSP:TRANSPARENT"]
    L += [f"SUMMARY:{esc(g['summary'])}", f"DESCRIPTION:{esc(chr(10).join(desc))}",
          f"CATEGORIES:{esc(','.join(sorted(g['tags'])))}"]
    if g["loc"]: L.append(f"LOCATION:{esc(g['loc'])}")
    if g["alarm"] and g["time_valid"] and not g["status"].get("completed"):
        L += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(g['summary'])}",
              f"TRIGGER:-PT{ALARM_MIN}M", "END:VALARM"]
    L.append("END:VEVENT")
    return L


outdir = sys.argv[1] if len(sys.argv) > 1 else "."
now = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
for fname, (calname, keep) in CALENDARS.items():
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//KI Sport//DE", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         f"X-WR-CALNAME:{calname}", f"NAME:{calname}", "X-WR-TIMEZONE:Europe/Vienna",
         "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H", *VTZ]
    n = 0
    for g in games:
        if keep(g):
            L += vevent(g, now)
            n += 1
    L.append("END:VCALENDAR")
    with open(os.path.join(outdir, fname), "w", newline="", encoding="utf-8") as f:
        f.write("\r\n".join(fold(l) for l in L) + "\r\n")
    print(f"{fname}: {n} Spiele", file=sys.stderr)


# ---------------------------------------------------------------- Übersichtsseite
today = dt.datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
window = [g for g in games if today <= g["kick"] < today + dt.timedelta(days=14)]
page_data = [dict(
    day=g["kick"].strftime("%Y-%m-%d"), time=g["kick"].strftime("%H:%M") if g["time_valid"] else None,
    sport="football" if g["us"] else "soccer", group=g["group"], match=g["match"], result=g["result"],
    label=g["label"], derby=g["derby"], night=g["night"], playoff=g["playoff"],
    star=bool(g["top"] or g["derby"]) and not g["playoff"], why=sorted(g["tags"]), tv=g["tv"],
) for g in window]

subs = "".join(
    f'<li><a href="webcal://{REPO_RAW.split("://")[1]}{f}">{html.escape(n)}</a>'
    f'<button type="button" data-copy="{REPO_RAW}{f}">Link kopieren</button></li>'
    for f, (n, _) in CALENDARS.items())

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_template.html"), encoding="utf-8") as f:
    page = f.read()
page = (page.replace("/*DATA*/[]", json.dumps(page_data, ensure_ascii=False).replace("</", "<\\/"))
            .replace("<!--SUBS-->", subs)
            .replace("<!--UPDATED-->", dt.datetime.now(TZ).strftime("%d.%m.%Y, %H:%M")))
os.makedirs(os.path.join(outdir, "docs"), exist_ok=True)
with open(os.path.join(outdir, "docs", "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
print(f"docs/index.html: {len(page_data)} Spiele (14 Tage)", file=sys.stderr)
