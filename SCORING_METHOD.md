# Método de scoring v1.1

## Capa 1 — Score Heras (rendimiento)

Mantiene los elementos del Excel original:

- nota media y nota acumulada;
- partidos vistos;
- minutos totales y minutos por partido;
- MVP y frecuencia de MVP;
- valor competitivo 1-50;
- ajuste mínimo de edad.

La fórmula original se sigue calculando como `Rank original`, pero el ranking operativo usa una escala 0-100 con prior bayesiano y retornos decrecientes.

## Capa 2 — Confianza

Partidos, minutos, fiabilidad, diversidad del visionado, consistencia y completitud. No convierte al jugador en mejor; indica cuánto creer la valoración.

## Capa 3 — Prioridad

Por defecto:

- 60% Score Heras;
- 15% encaje de rol;
- 10% potencial manual;
- 10% necesidad posicional;
- 5% tendencia.

La prioridad final se contrae hacia 50 cuando la confianza es baja.
