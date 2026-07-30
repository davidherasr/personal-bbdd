# Integración de BBDD Personal 2026

La v1.0 conserva la lógica útil del Excel sin obligar a mantener fórmulas manuales.

## Correspondencia

- `Hechos_Stats` → cada observación jugador-partido: jugador, minutos, fecha, partido, nota y MVP.
- `Dim_Jugadores` → resumen automático con partidos, minutos, nota acumulada/media, MVP, valor competitivo, minutos/partido y scores.
- `Dim_Equipos` → equipos con liga, país, plantilla, jugadores observados y partidos.
- `His_Rank` → ranking simple ordenado por Score Heras.

## Dos scores

- **Rank original** reproduce la fórmula histórica y puede generar números muy grandes. Se muestra por transparencia.
- **Score Heras 0-100** conserva sus ingredientes con suavizado de muestra y retornos decrecientes. Es el que usa la aplicación.

## Flujo recomendado

1. Crear partido.
2. Elegir formación de cada equipo.
3. Registrar jugador, minutos, nota, MVP y nota corta.
4. Consultar Tabla Excel o Rankings.
5. Completar rol/potencial solo para perfiles que merezcan análisis avanzado.
