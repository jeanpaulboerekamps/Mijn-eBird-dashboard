# My Birding Life — Streamlit

## Online zetten

1. Maak een nieuwe GitHub-repository en upload `app.py` en `requirements.txt` (geen persoonlijke eBird-data).
2. Ga naar https://share.streamlit.io, log in met GitHub en kies **Create app**.
3. Selecteer je repository, branch `main` en bestand `app.py`.
4. Open de nieuwe app-URL op je iPad en upload je eBird ZIP-export via de zijbalk.

Je kunt de app ook lokaal draaien met `pip install -r requirements.txt` en `streamlit run app.py`.

**Privacy:** De CSV bevat mogelijk precieze locaties en persoonlijke informatie. Zet deze niet in een openbare repository. De upload blijft in de sessie van de Streamlit-app; de Streamlit-host verwerkt de gegevens tijdens die sessie.

**Beperkingen:** De kaarten zijn interactief via zoomen, hover en landfilters in de zijbalk. Direct klikken op een land als selectiefilter is nog niet geïmplementeerd. Foto's openen via bronlinks en worden nog niet als thumbnails in de app geladen. De continentindeling is op basis van landen, niet van individuele coördinaten.
