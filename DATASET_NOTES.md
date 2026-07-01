# Notas de dataset v0.7

Esta versión prioriza que puedas construir una base grande sin duplicados:

- La carpeta `data/` trae estructura inicial de países, competiciones, equipos y jugadores semilla.
- La app incluye un importador de partidos desde Football-Data.co.uk para las competiciones disponibles en abierto.
- Para jugadores completos de todas las plantillas, usa `template_players.csv` o la descarga desde la página Importador masivo.

## Cobertura automática de partidos incluida en el importador

- Premier League, Championship, League One
- LaLiga, LaLiga Hypermotion
- Serie A, Serie B
- Bundesliga, 2. Bundesliga
- Ligue 1, Ligue 2

## Terceras divisiones no cubiertas automáticamente por esa fuente

- Primera Federación completa por grupos
- Serie C por grupos
- 3. Liga si la fuente elegida no la cubre
- Championnat National si la fuente elegida no la cubre

Para esas competiciones usa el CSV universal de partidos.
