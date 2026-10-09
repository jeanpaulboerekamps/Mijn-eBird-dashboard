# My Birding Life – versie 4

Nieuwe onderdelen:

- Wereldwijde heatmap met **unieke soorten per rastercel**, instelbare resolutie.
- Cirkelkaart met vogelordes en Passeriformes uitgesplitst naar families. Voor correcte wereldtotalen en percentages is een wereldwijde taxonomische checklist nodig.

## Installatie in bestaande GitHub-repository

Vervang `app.py` en `requirements.txt`, voeg `extra_sections.py` toe, en laat `data/ebird.zip` staan. Streamlit Community Cloud herstart automatisch.

## Taxonomie

Voeg optioneel `data/taxonomy.csv` toe met kolommen `scientific name`, `order`, `family`, en optioneel `category` (met `species` voor volledige soorten). Gebruik een complete wereldwijde soortenlijst uit één consistente taxonomie, bij voorkeur eBird/Clements. Zonder deze referentie toont de app de heatmap wel, maar geen misleidende cirkelpercentages.

De geüploade eBird-data is publiek als de repository publiek is.
