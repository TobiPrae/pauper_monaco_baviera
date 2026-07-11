# League Analytics Page

Diese Dokumentation beschreibt die Logik und Darstellungen der Streamlit-Seite `League Analytics` im Projekt.

## Zweck

Die Seite dient dazu, alle relevanten Match- und Deckdaten für ausgewählte Ligen zusammenzuführen und visuell aufzubereiten.

## Hauptbestandteile

### Seitenreihenfolge

Die Seite verwendet keine globale Ligaauswahl mehr. Für die Career Timeline gibt es einen eigenen lokalen Ligafilter in der Sektion.

1. Deck vs Deck Analytics
2. Career Timeline
3. Head-to-Head Analytics
4. Hall of Fame

### 1. Deck vs Deck Analytics

Die Sektion `Deck vs Deck Analytics` verwendet dasselbe matchbasierte Monaco-Dataset wie Head-to-Head (unabhängig vom Timeline-Filter) und berücksichtigt nur abgeschlossene Matches der Typen `Round`, `SemiFinal`, `Final`, `MatchFor3rd`.

- Matrix mit Deck (Zeilen) vs Deck (Spalten) im Format `Wins-Losses-Draws` aus Sicht der Zeile.
- Sortierung der Decks nach übergreifender Winrate.
- Farb-Codierung pro Zelle basiert auf `(wins-losses)/(wins+losses)`.
- Summary-Karten: `Most Played Matchup`, `Highest Winrate Matchup`, `Worst Matchup`, `Most Balanced Matchup`, `Largest Sample Size`.
- Expander mit Match-Details inklusive `Winner` und klickbarem `Video Link`.
- Zusätzliche Tabelle `Deck Matchup Rankings`.

### 2. Career Timeline

Die Timeline zeigt pro Spieler die chronologische Karriere über alle ausgewählten Saisons.

- Es werden nur Spieler aus Ligen berücksichtigt, deren Name `monaco` enthält.
- Ein lokaler `st.multiselect` in der Timeline-Sektion steuert, welche Monaco-Ligen einfließen.
- Spieler werden nach ihrer Winrate sortiert (höchste Winrate zuerst).

Visualisierung:

- Jeder Spieler erhält eine horizontale Linie mit kleinen farbigen Kästchen.
- Farbe der Kästchen:
  - Grün für einen Sieg
  - Gelb für ein Unentschieden
  - Rot für eine Niederlage
- Älteste Spiele erscheinen links, neueste rechts.
- Zwischen verschiedenen Saisons bzw. Liga-IDs erscheint eine dünne vertikale Trennlinie.
- Playoff-Matches (`SemiFinal`, `Final`, `MatchFor3rd`) werden in der richtigen Liga nach den regulären Runden einsortiert, aber innerhalb des Liga-Blocks angezeigt.

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

### 3. Head-to-Head Analytics

Die neue Head-to-Head-Analytics-Sektion zeigt die historische Bilanz zwischen Spielern in einer Matrix.

- Zeilen und Spalten listet Spieler alphabetisch.
- Die Diagonale bleibt leer.
- Jede Zelle zeigt das Format `Wins-Losses-Draws` aus Sicht des Zeilenspielers.
- Die Hintergrundfarbe verwendet einen kontinuierlichen Skalenverlauf von rot (negative Bilanz) über grau (ausgeglichen) zu grün (positive Bilanz).
- Über einen Filter lassen sich `All Matches`, `Regular Season` und `Playoffs Only` auswählen.
- Ein Expander darunter zeigt die Details aller historischen Matches für den ausgewählten Spieler-gegen-Spieler-Vergleich.

### 4. Hall of Fame

Die Hall of Fame listet die Liga-Champions der Monaco-Ligen in einer separaten Tabelle.

Jeder Eintrag enthält:

- `League`: Liga-Name
- `Player`: Gewinner der Liga
- `Deck`: Das zugewiesene Deck des Gewinners

Weitere Regeln:

- Die Hall of Fame ist unabhängig vom Career-Timeline-Filter.
- Berücksichtigt werden nur Ligen mit `league_name` enthält `monaco`.
- Zusätzlich werden nur abgeschlossene Ligen mit `playoffs_closed == True` berücksichtigt, mit einer Ausnahme für Liga `nr == 1`.
- Die Tabelle ist nach Datum sortiert, neueste abgeschlossene Saisons oben.

## Implementierungsdetails

- `client.list_leagues()`, `client.list_rounds()`, `client.list_league_players()`, `client.list_matches()` und `client.list_users()` werden verwendet, um Daten aus dem Datastore zu laden.
- `compute_match_summary(match)` aus `models.py` berechnet Match-Ergebnisse und Spielwerte.
- Matchdaten werden zur Timeline aus der dort gewählten lokalen Ligaauswahl generiert.
- `build_deck_matchup_matrix(matches)` kapselt die Berechnung für Deck-vs-Deck-Matrix, Summary, Details und Meta-Statistiken (`@st.cache_data`).
- Die Head-to-Head-Sektion verwendet ein eigenes, vom Timeline-Filter entkoppeltes Match-Set und enthält einen zusätzlichen Match-Filter für `All Matches`, `Regular Season` und `Playoffs Only`.
- Für Head-to-Head werden nur Ligen berücksichtigt, deren Name `monaco` enthält.
- Die Hall of Fame verwendet ein eigenes Monaco-Liga-Set, unabhängig von der Timeline-Auswahl.
- Die Deckzuordnung verwendet die Mitgliedschaften (`LeaguePlayer`) der Liga, um jedem Spieler sein aktuelles Deck für diese Liga zuzuordnen.

## Hinweise

- Die Seite zeigt in der Career Timeline nur Matches an, deren `round_id` zu den im Timeline-Filter ausgewählten Liga-Rounds gehört.
- Wenn ein Deck nicht gefunden wird, wird `No Deck` verwendet.
- Saisons werden über den `league.nr` und den `league.league_name` identifiziert.
- Die Timeline sortiert Matches nach `round.start_date`, `season_number`, `round_number`, Match-Typ und `match_id`.
- Playoff-Matches wie `SemiFinal`, `Final` und `MatchFor3rd` werden nach den regulären Runden in derselben Liga eingeordnet.
