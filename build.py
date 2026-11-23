#!/usr/bin/env python3
"""Erzeugt den Kalender 'KI - Sport' (ICS) aus der öffentlichen ESPN-API."""
import json, sys, urllib.request, datetime as dt
from zoneinfo import ZoneInfo

B = "https://site.api.espn.com/apis/"
TZ = ZoneInfo("Europe/Vienna")
UTC = dt.timezone.utc

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
TOP_N = 6  # Topspiel = beide Teams aktuell unter den Top 6 der Tabelle

# TV-Rechte außerhalb der USA (Saison 2026/27, ohne Gewähr). USA kommt spielgenau von ESPN.
TV = {
    "eng.1": {"UK": "Sky Sports / TNT Sports", "DE": "Sky", "AT": "Sky", "USA": "NBC / Peacock / USA Network"},
    "ger.1": {"UK": "Sky Sports", "DE": None, "AT": "Sky", "USA": "ESPN+"},  # DE nach Anstoß-Slot, s. tv_ger()
    "esp.1": {"UK": "Premier Sports", "DE": "DAZN", "AT": "DAZN", "USA": "ESPN+ / ESPN"},
    "ita.1": {"UK": "TNT Sports", "DE": "DAZN", "AT": "DAZN", "USA": "Paramount+ / CBS"},
    "aut.1": {"AT": "Sky (ausgew. Spiele ORF)"},
    "uefa.champions": {"UK": "TNT Sports / Prime Video (Di-Topspiel)", "DE": "DAZN / Prime Video (Di-Topspiel)", "AT": "Sky", "USA": "Paramount+ / CBS"},
    "uefa.europa": {"UK": "TNT Sports", "DE": "RTL+", "AT": "Sky", "USA": "Paramount+"},
    "uefa.europa.conf": {"UK": "TNT Sports", "DE": "RTL+", "AT": "Sky", "USA": "Paramount+"},
    "eng.fa": {"UK": "BBC / TNT Sports", "USA": "ESPN+"},
    "eng.league_cup": {"UK": "Sky Sports", "USA": "Paramount+"},
    "nfl": {"UK": "Sky Sports NFL / DAZN Game Pass", "DE": "RTL / Nitro / RTL+ / Sky", "AT": "Sky / DAZN Game Pass"},
}

def tv_ger(local):
    wd, h = local.weekday(), local.hour
    if wd == 6: return "DAZN"
    if wd == 5 and h == 15: return "Sky (Einzelspiele) / DAZN (Konferenz)"
    return "Sky"

def get(path):
    try:
        with urllib.request.urlopen(B + path, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        print("WARN", path, e, file=sys.stderr)
        return {}

events = {}

def add(e, tag, comp, top=False, playoff=False, label=None):
    c = e["competitions"][0]
    ev = events.get(e["id"])
    if ev:
        ev["tags"].add(tag); ev["top"] |= top; ev["playoff"] |= playoff
        return
    comps = c.get("competitors", [])
    side = {x.get("homeAway"): x for x in comps}
    st = c["status"]["type"]
    notes = [n.get("headline") for n in c.get("notes", []) if n.get("headline")]
    us_tv = sorted({n for b in c.get("broadcasts", []) for n in b.get("names", [])})
    venue = c.get("venue", {})
    events[e["id"]] = dict(
        date=e["date"], comp=comp, label=label, tags={tag}, top=top, playoff=playoff,
        home=side.get("home"), away=side.get("away"), status=st, notes=notes, us_tv=us_tv,
        time_valid=c.get("timeValid", True) and st.get("name") != "STATUS_TBD",
        loc=", ".join(filter(None, [venue.get("fullName"), venue.get("address", {}).get("city")])),
        week=e.get("week", {}).get("number"))

def name(x):
    if not x: return "TBD"
    n = x["team"].get("displayName") or x["team"].get("name") or "TBD"
    r = (x.get("curatedRank") or {}).get("current")
    return f"#{r} {n}" if r and r <= 25 else n

def score(x):
    s = x.get("score") if x else None
    return s.get("displayValue") if isinstance(s, dict) else s

def record(x):
    for r in (x or {}).get("records", []) or []:
        if r.get("type") == "total":
            try:
                w, l, *t = map(int, r["summary"].split("-"))
                return w, l
            except Exception: pass
    return None

# ---------- Fußball: Lieblingsteams ----------
for tid, (team, leagues) in FAV_SOCCER.items():
    for lg in leagues:
        for q in ("", "?fixture=true"):
            d = get(f"site/v2/sports/soccer/{lg}/teams/{tid}/schedule{q}")
            for e in d.get("events", []):
                add(e, team, lg, label=(e.get("league") or {}).get("name"))

# ---------- Fußball: Topspiele (Top 6 gegen Top 6) ----------
for lg, lname in TOP_LEAGUES.items():
    st = get(f"v2/sports/soccer/{lg}/standings")
    try:
        entries = sorted(st["children"][0]["standings"]["entries"],
                         key=lambda x: next((s["value"] for s in x["stats"] if s["name"] == "rank"), 99))
    except Exception:
        continue
    top = {x["team"]["id"] for x in entries[:TOP_N]}
    for tid in top:
        for q in ("", "?fixture=true"):
            for e in get(f"site/v2/sports/soccer/{lg}/teams/{tid}/schedule{q}").get("events", []):
                ids = {x["team"]["id"] for x in e["competitions"][0]["competitors"]}
                if ids <= top:
                    add(e, f"Topspiel {lname}", lg, top=True, label=(e.get("league") or {}).get("name"))

# ---------- NFL ----------
def thanksgiving(y):
    d = dt.date(y, 11, 1)
    return d + dt.timedelta(days=(3 - d.weekday()) % 7 + 21)

for wk in range(1, 19):
    for e in get(f"site/v2/sports/football/nfl/scoreboard?seasontype=2&week={wk}").get("events", []):
        c = e["competitions"][0]
        ids = {x["team"]["id"]: x for x in c["competitors"]}
        for tid, team in FAV_US["nfl"].items():
            if tid in ids: add(e, team, "nfl", label="NFL")
        recs = [record(x) for x in ids.values()]
        good = all(r and (r[0] + r[1]) >= 3 and r[0] / (r[0] + r[1]) >= 0.6 for r in recs)
        kick = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        us_day = (kick - dt.timedelta(hours=5)).date()
        prime = kick.hour < 6 or us_day in (thanksgiving(us_day.year), dt.date(us_day.year, 12, 25))
        if good or prime:
            add(e, "NFL-Topspiel" if good else "NFL Primetime", "nfl", top=True, label="NFL")
for wk in range(1, 6):
    for e in get(f"site/v2/sports/football/nfl/scoreboard?seasontype=3&week={wk}").get("events", []):
        if "pro bowl" not in e.get("name", "").lower():
            add(e, "NFL Playoffs", "nfl", playoff=True, label="NFL Playoffs")

# ---------- College Football ----------
for wk in range(1, 17):
    for e in get(f"site/v2/sports/football/college-football/scoreboard?seasontype=2&week={wk}&groups=80&limit=400").get("events", []):
        c = e["competitions"][0]
        ids = {x["team"]["id"]: x for x in c["competitors"]}
        for tid, team in FAV_US["college-football"].items():
            if tid in ids: add(e, team, "ncaaf", label="NCAA Football")
        ranks = [(x.get("curatedRank") or {}).get("current", 99) for x in ids.values()]
        champ = any("championship" in (n.get("headline") or "").lower() for n in c.get("notes", []))
        if all(r <= 25 for r in ranks) or (champ and any(r <= 25 for r in ranks)):
            add(e, "NCAA-Topspiel", "ncaaf", top=True, label="NCAA Football")
for e in get("site/v2/sports/football/college-football/scoreboard?seasontype=3&groups=80&limit=400").get("events", []):
    notes = " ".join(n.get("headline", "") for n in e["competitions"][0].get("notes", []))
    if "College Football Playoff" in notes:
        add(e, "College Football Playoff", "ncaaf", playoff=True, label="NCAA Football Playoff")

print(len(events), "Events", file=sys.stderr)

# ---------- ICS schreiben ----------
def esc(s): return s.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace("\n", r"\n")

def fold(line):
    b, out = line.encode(), []
    while len(b) > 75:
        cut = 75 if not out else 74
        while (b[cut] & 0xC0) == 0x80: cut -= 1
        out.append(b[:cut].decode()); b = b[cut:]
    out.append(b.decode())
    return "\r\n ".join(out)

VTZ = """BEGIN:VTIMEZONE
TZID:Europe/Vienna
X-LIC-LOCATION:Europe/Vienna
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE""".split("\n")

now = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//KI Sport//DE", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
     "X-WR-CALNAME:KI - Sport", "NAME:KI - Sport", "X-WR-TIMEZONE:Europe/Vienna",
     "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D", *VTZ]

for eid, ev in sorted(events.items(), key=lambda kv: kv[1]["date"]):
    kick = dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(TZ)
    us = ev["comp"] in ("nfl", "ncaaf")
    icon = "🏆" if ev["playoff"] else ("⭐" if ev["top"] and not (ev["tags"] - {t for t in ev["tags"] if "Top" in t or "Prime" in t}) else "")
    sport = "🏈" if us else "⚽"
    h, a = ev["home"], ev["away"]
    title = f"{name(a)} @ {name(h)}" if us else f"{name(h)} – {name(a)}"
    if ev["status"].get("completed") and score(h) is not None:
        title += f" ({score(a)}:{score(h)})" if us else f" ({score(h)}:{score(a)})"
    if ev["playoff"] and ev["notes"] and "TBD" in title:
        title = ev["notes"][0]
    summary = " ".join(filter(None, [sport, icon, title]))

    tv = {"USA": ", ".join(ev["us_tv"]) or None}
    m = TV.get(ev["comp"], {})
    for land in ("UK", "DE", "AT"):
        tv[land] = m.get(land)
    tv["USA"] = tv["USA"] or m.get("USA")
    if ev["comp"] == "ger.1": tv["DE"] = tv_ger(kick)
    if ev["comp"] == "nfl" and ev["playoff"]: tv["DE"] = "RTL / RTL+"

    desc = [f"{ev['label'] or ev['comp']}"]
    desc += ev["notes"]
    if ev["week"] and us: desc.append(f"Woche {ev['week']}")
    desc.append("Kalender-Grund: " + ", ".join(sorted(ev["tags"])))
    desc.append("")
    desc.append("📺 TV")
    for land, flag in (("AT", "🇦🇹"), ("DE", "🇩🇪"), ("UK", "🇬🇧"), ("USA", "🇺🇸")):
        desc.append(f"{flag} {land}: {tv[land] or '–'}")
    desc.append("")
    desc.append(f"Status: {ev['status'].get('description', '')}")
    if not ev["time_valid"]: desc.append("Anstoßzeit noch offen")
    desc.append("TV außerhalb USA nach Rechtelage 2026/27, ohne Gewähr.")

    L += ["BEGIN:VEVENT", f"UID:espn-{eid}@ki-sport", f"DTSTAMP:{now}"]
    if ev["time_valid"]:
        end = kick + dt.timedelta(hours=3.5 if us else 2)
        L += [f"DTSTART;TZID=Europe/Vienna:{kick:%Y%m%dT%H%M%S}", f"DTEND;TZID=Europe/Vienna:{end:%Y%m%dT%H%M%S}"]
    else:
        day = dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(dt.timezone(dt.timedelta(hours=-5))).date()
        L += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + dt.timedelta(days=1):%Y%m%d}"]
    L += [f"SUMMARY:{esc(summary)}", f"DESCRIPTION:{esc(chr(10).join(desc))}",
          f"CATEGORIES:{esc(','.join(sorted(ev['tags'])))}"]
    if ev["loc"]: L.append(f"LOCATION:{esc(ev['loc'])}")
    L.append("END:VEVENT")
L.append("END:VCALENDAR")

out = sys.argv[1] if len(sys.argv) > 1 else "ki-sport.ics"
with open(out, "w", newline="") as f:
    f.write("\r\n".join(fold(l) for l in L) + "\r\n")
