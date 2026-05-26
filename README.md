# pauper_monaco_baviera

**To decide:**
- App hosting 
    - Streamlit 
        + Free
        - Github repo must be public
    - Cloud Run
        + Github repo can be private
        + Easier to "professionalize" (e.g. using an official domain name like paupergeddon-monaco.info)
        + Bigger learning effect (usage of docker on GCP)
        + More flexibility about performance and scalability
        - Might cost some euros per month
- Data store
    - GCP datastore
        + Free
        + NoSQL flexible schema
        + Easy to use
    - Other GCP services
    - Other services
- AI agent
    - Claude
    - Gemini
    - Others?

**To do:**
- Set up GitHub
- Decide architecture
- Write promt for agent

**Features: Must**
- Administration
    - Log In erforderlich
- Liga
    - Übersicht
        - Tabelle (Anzeige Spieltag, slide switch zwischen Spieltagen)
        - Tunierbaum (In Playoffs)
    - Anlegen
        - Spieler hinzufügen
        - Planen 
            - Wie viele Wochen (Start-/Endzeit)
            - Automatisches Scheduling/Turnierbegegnungen Planen
    - Spiele dokumentieren
- Spielermanagement
    - Übersicht
    - Bearbeiten
    - Hinzufügen
- Turnierbaum 



**Features: Nice to have**
- Eigene Spielerprofile 

**Prompt:**
- We want to build a web app to track and organize our Magic the Gathering Tournament
- We want to use:
    - Streamlit hosted on https://share.streamlit.io/
    - GCP Datastore for Storage
    - We want also to be able to test it locally
- Tournament Rules:
    - One match consists of multiple games in a best of 3 mode
    - So we can have the following outcomes:
        - 2:1 (Win Player A)
        - 1:0 (Win Player A)
        - 2:0 (Win Player A)
        - 0:0 (Draw)
        - 1:1 (Draw)
        - 0:1 (Win Player B)
        - 1:2 (Win Player B)
        - 0:2 (Win Player B)
    - A Match Win is awarded 3 points
    - A Draw is awarded 1 point to each player
    - A Loss is awarded 0 points
    - We will have a swiss system where each players plays once against each other player
    - After the swiss round we want to make a top n cut (n should be modifiable) for the playoffs where we would play in a tournament tree instead of a table format
- We want to have at least the following features:
    - Password protection for entering the web
    - Multipage Structure with the following pages:
        1. Player Management
            - Add Players
            - Edit Players (including Delete)
            - Show Player Overview
        2. League
            - Table with following Columns
                - Player
                - Points
                - Points + (Game Wins / Total Games Played)
                - Match Wins
                - Match Losses
                - Match Draws
                - Total Matches Played
                - Game Wins
                - Game Losses
                - Total Games Played
                - Game Win Rate (Game Wins / Total Games Played)
            - The table should be sortable by Column (default 'Points + (Game Wins / Total Games Played)')
        3. Record Game 
            - Player A (dropdown select)
            - Player B (dropdown select)
            - Starting Player (dropdown select)
            - Winner Game 1-3 (Player A, Player B, None)
            - Automatically Calculate Match Winner, Loser or Draw
            - Check box: Went in time
        4. Edit Game 
- Last step: Ask us questions about your understanding.
