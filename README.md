# Scouting Hub v0.3

Aplicación Streamlit para crear una base propia de scouting con flujo jerárquico:

- Países
- Competiciones / ligas
- Equipos / selecciones
- Plantillas
- Jugadores
- Partidos
- Observaciones

## Novedades v0.3

- Flujo guiado desde lo grande a lo pequeño: país → liga/competición → equipo → jugador.
- Modo club y modo selección.
- Detección básica de duplicados por normalización de texto: ignora mayúsculas, tildes y espacios dobles.
- Posibilidad de añadir países, competiciones, equipos y jugadores desde el propio flujo.
- Carga masiva de plantilla mediante texto pegado línea a línea.
- Página específica para fusionar jugadores duplicados.
- Exportación completa a Excel y ZIP.
- Importación desde ZIP de backup o Excel exportado.
- Fichas de jugador y observaciones acumuladas.

## Cómo ejecutarla en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cómo subirla a Streamlit Cloud

1. Sube `app.py`, `requirements.txt`, `README.md` y la carpeta `.streamlit/` a un repositorio de GitHub.
2. Crea una app nueva en Streamlit Community Cloud.
3. Selecciona `app.py` como archivo principal.
4. Usa siempre la página `Backup / Importar / Exportar` para guardar una copia de tus datos.

## Nota importante

En Streamlit Cloud, los CSV locales pueden perderse en reinicios o redeploys. La app está pensada para trabajar con backups: exportar al acabar e importar al volver.
