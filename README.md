# My Birding Life – versie 5

- Heatmap direct boven de lifers, kleuren van lichtoranje tot donkerrood.
- Automatische koppeling aan de officiële eBird/Clements Checklist v2025 (Cornell).
- Cirkelkaart: vogelordes en Passeriformes-families, met wereldtotaal, gezien en percentage.

## GitHub update
Vervang `app.py` en `extra_sections.py` in je repository. `requirements.txt` en `data/ebird.zip` kunnen blijven staan.

De app downloadt de Clements CSV bij de eerste start (internet vereist). Als Cornell tijdelijk niet bereikbaar is, kun je de officiële CSV downloaden van https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2025/2025-citation-checklist-downloads/ en opslaan als `data/taxonomy.csv`.

**Taxonomische kanttekening:** historische waarnemingsnamen worden exact gekoppeld aan de huidige checklist; oude synoniemen/splits kunnen daardoor als niet-gekoppeld worden gerapporteerd. De app toont het aantal niet-gekoppelde namen.
