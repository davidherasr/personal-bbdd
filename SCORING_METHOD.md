# Método de scoring v1.2

La aplicación separa rendimiento, proyección, encaje y confianza.

## Score Heras

Mantiene la lógica útil del Excel personal:

- nota media;
- partidos y minutos;
- MVP;
- valor competitivo;
- participación media;
- ajuste moderado de edad.

El resultado se normaliza entre 0 y 100 para evitar que un MVP o una edad baja disparen la fórmula.

## Prioridad

La prioridad combina:

- Score Heras;
- encaje de rol;
- potencial manual;
- necesidad posicional;
- tendencia.

La confianza actúa como freno: una señal alta con poca muestra exige otra observación en lugar de convertirse automáticamente en prioridad A.

## Perfiles disponibles

- **Excel simple:** máxima importancia al rendimiento observado.
- **Equilibrado:** configuración recomendada.
- **Proyección:** mayor peso de potencial y encaje.
