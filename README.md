# KI - Sport

Sport-Kalender (iCal) mit allen Spielen meiner Teams, Topspielen und Playoffs. Alle Zeiten sind in Wiener Zeit.

- **Teams:** Rapid Wien, Arsenal, Man City, Lazio, Roma, Inter, Milan, Atlético, Real Madrid, Barcelona, Chiefs, Bengals, Texas Longhorns, Ohio State
- **⭐ Topspiele:** Premier League, Bundesliga, LaLiga, Serie A (Top 6 gegen Top 6), NFL (beide Teams mit mindestens 60 % Siegen, dazu Primetime-Spiele), NCAA (Top 25 gegen Top 25)
- **🏆 Playoffs:** NFL und College Football Playoff
- **📺 TV:** Sender für AT, DE, UK und USA. USA kommt bei NFL und NCAA spielgenau von ESPN, der Rest folgt der Rechtelage 2026/27 (ohne Gewähr).

Die Datei `ki-sport.ics` wird jeden Montag automatisch per GitHub Actions neu erzeugt (`.github/workflows/update.yml`). Manuell starten: Actions → „Kalender aktualisieren“ → Run workflow.

Lokal erzeugen: `python3 build.py ki-sport.ics` (Python 3.9 oder neuer, keine Abhängigkeiten). Datenquelle: öffentliche ESPN-API.
