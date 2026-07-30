# Scouting Hub v0.8

Aplicación Streamlit para construir una base propia de scouting desde cero.

## Qué cambia en esta versión

- Dataset completamente vacío: todos los CSV contienen solo cabeceras.
- Proyecto modular (`scouting_hub/`) en lugar de un único archivo monolítico.
- Navegación agrupada por trabajo diario, análisis y administración.
- Ranking por rol con criterios específicos.
- Radar comparativo en SVG puro: no necesita matplotlib ni Plotly.
- Percentiles, comparador y distribución por rol.
- Búsqueda de jugadores similares por perfil.
- Constructor de alineaciones y shortlists contextuales.
- Motor de confianza basado en muestra, minutos, fiabilidad, diversidad, completitud y consistencia.
- Ajuste del score hacia 50 cuando hay poca evidencia.
- Compatibilidad básica con backups de versiones anteriores.
- Escrituras atómicas de CSV y snapshot automático antes de restaurar o borrar.

## Despliegue en Streamlit Community Cloud

1. Descomprime el ZIP.
2. Sube todo el contenido a la raíz del repositorio.
3. Selecciona `streamlit_app.py` como archivo principal.
4. Asegúrate de subir las carpetas `scouting_hub/`, `data/`, `templates/` y `.streamlit/`.

## Ejecución local

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## Primer uso

1. Entra en **Alta rápida**.
2. Crea país, competición y equipo.
3. Añade la plantilla o el primer jugador.
4. Crea un partido.
5. Registra una observación rápida.
6. Cuando el perfil lo merezca, completa una evaluación específica de rol.
7. Revisa **Rankings** y **Laboratorio de roles**.
8. Descarga un backup ZIP.

## Persistencia

Los CSV locales de Streamlit Community Cloud no deben considerarse almacenamiento permanente. Descarga backups con frecuencia. La app crea snapshots locales antes de restaurar o reiniciar, pero esos snapshots también dependen del almacenamiento del despliegue.

## Comprobación del proyecto

```bash
python validate_project.py
python -m unittest discover -s tests
```
