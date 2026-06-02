# Scouting Hub v0.5

Aplicación Streamlit para crear una base propia de scouting: países, competiciones, equipos, jugadores, partidos, observaciones, scoring de prioridad, control de duplicados y backup.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Desplegar en Streamlit Cloud

- Sube todos los archivos a la raíz del repositorio.
- Main file path: `streamlit_app.py`
- Mantén la carpeta `data/` si quieres arrancar con el dataset inicial.

## Datos

Incluye CSV iniciales en `data/` para no arrancar de cero: países, competiciones, equipos, jugadores semilla y partidos de ejemplo. Exporta siempre desde la pestaña Backup antes de cerrar la app en la nube.
