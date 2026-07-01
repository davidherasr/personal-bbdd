# Scouting Hub v0.7 - Motor de ranking

La v0.7 separa el ranking en cinco dimensiones para evitar que una sola nota o una etiqueta manual decida todo:

- **Nivel observado**: rendimiento mostrado en observaciones, ponderado por posición.
- **Potencial**: proyección por edad, potencial manual y señales de margen.
- **Encaje**: rol, encaje táctico y necesidad posicional.
- **Confianza**: número de observaciones, minutos vistos, fuente, fiabilidad y completitud.
- **Urgencia**: estado de seguimiento y señales de mercado/seguimiento.

La prioridad final se calcula con una base ponderada y luego se modula por confianza:

```text
Prioridad base = 40% nivel + 25% potencial + 20% encaje + 15% urgencia
Prioridad final = prioridad_base × (0.70 + 0.30 × confianza)
```

Excepción importante: si el nivel/potencial es alto pero la confianza es baja, la app tiende a marcar B+ o B y propone segunda observación urgente, no decisión definitiva.

## Lectura práctica

- **A**: datos suficientes + prioridad fuerte.
- **B+**: señal fuerte, pero evidencia insuficiente.
- **B**: buen seguimiento.
- **C**: mantener/completar.
- **D**: baja prioridad o sin datos suficientes.
