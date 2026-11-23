# KI - Sport

Sport-Kalender (iCal) mit meinen Teams, Topspielen, Derbys und Playoffs. Alle Zeiten sind in Wiener Zeit. Dazu gibt es eine Übersichtsseite mit den nächsten 14 Tagen.

## Kalender-Abos

| Kalender | Adresse |
|---|---|
| **KI - Sport** (alles) | `https://raw.githubusercontent.com/hyr9fg2rrz-oss/ki-sport/main/ki-sport.ics` |
| Meine Teams | `https://raw.githubusercontent.com/hyr9fg2rrz-oss/ki-sport/main/meine-teams.ics` |
| Topspiele | `https://raw.githubusercontent.com/hyr9fg2rrz-oss/ki-sport/main/topspiele.ics` |
| Playoffs | `https://raw.githubusercontent.com/hyr9fg2rrz-oss/ki-sport/main/playoffs.ics` |

Entweder „alles“ oder die drei Einzelkalender abonnieren. Jedes Spiel steht in genau einem Einzelkalender.

## Inhalt

- **Meine Teams:** Rapid Wien, Arsenal, Man City, Lazio, Roma, Inter, Milan, Atlético, Real Madrid, Barcelona, Chiefs, Bengals, Texas Longhorns, Ohio State. Alle Wettbewerbe, mit ⏰ Erinnerung 30 Minuten vor Anpfiff.
- **⭐ Topspiele:** Premier League, Bundesliga, LaLiga und Serie A (Top 6 gegen Top 6); Champions League (große Klubs gegeneinander); NFL (beide Teams mit mindestens 60 % Siegen, dazu Primetime-Spiele); NCAA (Top 25 gegen Top 25).
- **⭐ Derbys:** Wiener Derby, El Clásico, Derbi madrileño, Derby della Capitale, Derby della Madonnina, Derby d'Italia, North London Derby, Manchester Derby, Der Klassiker, The Game.
- **🏆 Playoffs:** NFL und College Football Playoff, mit ⏰ Erinnerung.
- **🌙 Nachtspiele:** Anstoß zwischen 0 und 6 Uhr Wiener Zeit.
- **📺 TV:** Sender für AT, DE, UK und USA. USA kommt bei NFL und NCAA spielgenau von ESPN, der Rest folgt der Rechtelage 2026/27 (ohne Gewähr).

## Automatik

GitHub Actions erzeugt alles **täglich** neu (`.github/workflows/update.yml`). Manuell starten: Actions → „Kalender aktualisieren“ → Run workflow.

Lokal erzeugen: `python3 build.py .` (Python 3.9 oder neuer, keine Abhängigkeiten). Teams, Derbys und TV-Sender stehen oben in `build.py`. Datenquelle: öffentliche ESPN-API.
