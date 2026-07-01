# Scouting Hub v0.7

Aplicación Streamlit para construir una base propia de scouting: jugadores, equipos, partidos, observaciones, importación masiva, duplicados, análisis, rankings y backup.

## Novedades v0.7

- Página nueva **Rankings**.
- Motor de scoring separado en **nivel observado**, **potencial**, **encaje**, **confianza**, **urgencia** y **prioridad final**.
- Prioridad **B+** para jugadores con señal alta pero poca evidencia.
- Ranking por prioridad, nivel, potencial, encaje, confianza, jugadores que necesitan segunda observación y alertas.
- Ficha de jugador con desglose visual del ranking.
- Campos nuevos: rol principal/secundario, encaje táctico, necesidad posicional, tipo de visionado, nivel rival, dificultad, fiabilidad y tendencia.
- Comparador actualizado con el nuevo motor de scoring.
- Importador CSV actualizado para aceptar roles, encaje y necesidad posicional.
- Mantiene el dataset inicial, importador masivo, cobertura de datos y backup de v0.6.

## Ejecutar local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Streamlit Cloud

Main file path:

```txt
streamlit_app.py
```

Sube también la carpeta `data/`.

## Flujo recomendado

1. Entra en **Importador masivo** para cargar equipos, partidos o jugadores por CSV.
2. Usa **Añadir / puntuar jugador** para añadir observaciones con fiabilidad, tendencia y contexto.
3. Revisa **Rankings** para decidir quién necesita segunda observación, informe largo o descarte.
4. Entra en **Jugadores** para ver la ficha individual y el desglose completo.
5. Descarga siempre backup ZIP o Excel al terminar.

## Aviso de datos

La app trae datos semilla para arrancar. No son una certificación oficial completa de plantillas 2025/26. Para plantillas completas y actualizadas, usa el importador CSV con fuentes fiables y corrige desde la propia app.
