# Data Analyzer Page

Diese Dokumentation beschreibt die Logik und Darstellungen der Streamlit-Seite `Data Analyzer` im Projekt.

## Zweck

Die Seite dient dazu, alle relevanten Match- und Deckdaten für ausgewählte Ligen zusammenzuführen und visuell aufzubereiten.

## Hauptbestandteile

### 1. Ligaauswahl

- `st.multiselect` erlaubt die Auswahl einer oder mehrerer Ligen.
- Nur Daten der ausgewählten Ligen werden in den nachfolgenden Tabellen und Visualisierungen verwendet.

### 2. Match-Daten-Tabelle

Die Haupttabelle listet alle Matches der ausgewählten Ligen auf. Jede Zeile enthält:

- League Name
- League Number
- League ID
- Round Number
- Round Start
- Round End
- Match ID
- Match Type
- Player A
- Deck A
- Player B
- Deck B
- Starting Player
- Match Result
- Score A
- Score B
- Points A
- Points B
- Total Games
- Video Link

Die Tabelle wird nach Liga-Nummer, Rundennummer und Match-ID sortiert.

### 3. Meta Stats

Die Sektion `Meta Stats` wertet die ausgewählten Ligen auf Deck-Ebene aus.

Berechnete Kennzahlen pro Deck:

- `Wins`: Anzahl gewonnener Matches des Decks
- `Draws`: Anzahl unentschiedener Matches des Decks
- `Leagues`: Anzahl unterschiedlicher Ligen, in denen das Deck auftaucht
- `Win Rate`: Gewinnrate über alle eingegebenen Matches (Anzahl gewonnener Matches / Anzahl teilgenommener Matches)
- `Winrate (incl Draw)`: Gewinnrate inklusive Unentschieden, wobei ein Draw als 50% Sieg gewertet wird

Sortierung:

- Primär nach `Winrate (incl Draw)` absteigend
- Sekundär nach `Win Rate` absteigend
- Tertiär nach Wins absteigend

Die Berechnungen umfassen alle Matchtypen der ausgewählten Ligen, also sowohl reguläre Runden als auch Playoff-Matches. Nur abgeschlossene Matches mit mindestens einem gewerteten Spiel werden berücksichtigt.

### 4. Career Timeline

Die Timeline zeigt pro Spieler die chronologische Karriere über alle ausgewählten Saisons.

Visualisierung:

- Jeder Spieler erhält eine horizontale Linie mit kleinen farbigen Kästchen.
- Farbe der Kästchen:
  - Grün für einen Sieg
  - Gelb für ein Unentschieden
  - Rot für eine Niederlage
- Älteste Spiele erscheinen links, neueste rechts.
- Zwischen verschiedenen Saisons erscheint eine dünne vertikale Trennlinie.
- Playoff-Matches (`SemiFinal`, `Final`, `MatchFor3rd`) werden in der richtigen Liga nach den regulären Runden einsortiert.

Tooltip-Informationen pro Match:

- Gegner
- Saison
- Runde
- Eigenes Deck
- Gegnerdeck
- Ergebnis (z. B. `2:0`, `2:1`, `1:2`)

### Zusammenfassung pro Spieler

Über der Timeline wird pro Spieler angezeigt:

- Match Win Rate
- Aktuelle Serie (z. B. `W-W-L-W`)
- Längste Siegesserie
- Gesamtbilanz (Wins-Draws-Losses)

### 5. Hall of Fame

Die Hall of Fame listet die Liga-Champions in einer separaten Tabelle.

Jeder Eintrag enthält:

- `League`: Liga-Name
- `Player`: Gewinner der Liga
- `Deck`: Das zugewiesene Deck des Gewinners

Die Hall of Fame ist nicht vom Ligafilter betroffen.

Weitere Regeln:

- Es werden nur Ligen mit `Monaco` im Namen erfasst.
- Die aktuell laufende Liga wird nicht aufgenommen.
- Die Tabelle ist nach Datum sortiert, neueste abgeschlossene Saisons oben.

Über der Timeline wird pro Spieler angezeigt:

- Match Win Rate
- Aktuelle Serie (z. B. `W-W-L-W`)
- Längste Siegesserie
- Gesamtbilanz (Wins-Draws-Losses)

## Implementierungsdetails

- `client.list_leagues()`, `client.list_rounds()`, `client.list_league_players()`, `client.list_matches()` und `client.list_users()` werden verwendet, um Daten aus dem Datastore zu laden.
- `compute_match_summary(match)` aus `models.py` berechnet Match-Ergebnisse und Spielwerte.
- Matchdaten werden zur Tabelle und zur Timeline aus derselben gefilterten Auswahl generiert, um Konsistenz sicherzustellen.
- Die Deckzuordnung verwendet die Mitgliedschaften (`LeaguePlayer`) der Liga, um jedem Spieler sein aktuelles Deck für diese Liga zuzuordnen.

## Hinweise

- Die Seite zeigt aktuell nur Matches an, deren `round_id` zu einem ausgewählten Liga-Round gehört.
- Wenn ein Deck nicht gefunden wird, wird `No Deck` verwendet.
- Saisons werden über den `league.nr` und den `league.league_name` identifiziert.
- Die Timeline sortiert Matches nach `round.start_date`, `season_number`, `round_number`, Match-Typ und `match_id`.
- Playoff-Matches wie `SemiFinal`, `Final` und `MatchFor3rd` werden nach den regulären Runden in derselben Liga eingeordnet.
