# Scouting Hub v0.8.1 — corrección de estado

## Error corregido

La v0.8 intentaba asignar directamente un valor a `st.session_state` después de crear el widget con esa misma clave. Streamlit lo bloquea con `StreamlitAPIException`.

La v0.8.1 usa una cola temporal (`__pending__...`) y aplica el valor antes de renderizar el widget en el siguiente rerun. Se ha aplicado a:

- País
- Competición
- Equipo / selección
- Jugador creado desde Alta rápida
- Cambio automático de Crear jugador a Observar existente

La base continúa completamente vacía salvo por las cabeceras CSV.
