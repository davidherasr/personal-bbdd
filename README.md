# Scouting Hub v0.4

Aplicación Streamlit para crear una base propia de scouting: jugadores, equipos, partidos, observaciones, prioridades, duplicados, dashboard, investigación, comparador, campograma y backup.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Desplegar en Streamlit Cloud

1. Sube estos archivos a la raíz de tu repositorio de GitHub.
2. En Streamlit Cloud selecciona `streamlit_app.py` como Main file path.
3. La app instalará dependencias desde `requirements.txt`.

## Uso recomendado

1. Entra en **Añadir / puntuar jugador**.
2. Selecciona país, liga/competición y equipo/selección.
3. Carga plantilla o selecciona jugador existente.
4. Añade observaciones con notas y próximo paso.
5. Revisa **Dashboard**, **Jugadores**, **Investigación** y **Duplicados**.
6. Exporta ZIP o Excel al terminar cada sesión.

## Aviso sobre persistencia

En Streamlit Cloud el almacenamiento local puede reiniciarse. Exporta el ZIP o Excel cuando termines y reimpórtalo cuando quieras continuar.
