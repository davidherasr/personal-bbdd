# Método de scoring v0.8

## 1. Nivel observado

Las notas macro —técnica, táctica, físico, mental y global— se ponderan de forma distinta según la posición. Cada observación recibe un peso de evidencia basado en:

- minutos vistos;
- tipo de visionado;
- fiabilidad declarada;
- nivel del rival;
- dificultad del partido.

Una nota `0` significa «no evaluado» y no entra en la media.

## 2. Encaje de rol

Cada rol tiene seis criterios y pesos propios. Ejemplos:

- central corrector: coberturas, velocidad al espacio, anticipación, defensa 1v1, colocación y pase seguro;
- mediocentro organizador: pase progresivo, orientación, escaneo, ritmo, resistencia a presión y posición defensiva;
- delantero móvil: movilidad, rupturas, asociación, finalización, presión y decisión.

Cuando existe evaluación detallada, se usa como fuente principal. Si no existe, se genera una estimación provisional a partir de las notas macro.

## 3. Potencial

Es una valoración manual de 0 a 10. La edad no añade puntos automáticamente. Ser joven no equivale por sí mismo a tener mayor proyección.

## 4. Necesidad

Valoración manual de 0 a 10 sobre cuánto necesita el proyecto ese perfil o posición.

## 5. Tendencia

Las tres observaciones más recientes pesan de forma creciente. «Sube», «mantiene» y «baja» se convierten en una señal moderada, no en el núcleo del ranking.

## 6. Prioridad base

Pesos recomendados:

- nivel: 35%;
- encaje de rol: 25%;
- potencial: 20%;
- necesidad: 10%;
- tendencia: 10%.

Los pesos se pueden editar en **Ajustes del scoring**.

## 7. Confianza

La confianza combina:

- número de observaciones;
- minutos vistos;
- partidos distintos;
- diversidad de fuentes;
- fiabilidad;
- completitud de ficha;
- consistencia de las notas.

La completitud no mejora al jugador: solo hace más fiable la decisión.

## 8. Ajuste por evidencia

El score base se contrae hacia 50 cuando la confianza es baja:

```text
factor_evidencia = 0.45 + 0.55 × confianza
score_decisión = 50 + (score_base - 50) × factor_evidencia
```

Así, una muestra pequeña no hunde ni dispara artificialmente el resultado.

## 9. Etiquetas

- **A**: score alto y confianza suficiente.
- **B+**: señal de nivel A, pero evidencia insuficiente.
- **B**: seguimiento fuerte.
- **C**: seguimiento normal o datos todavía ambiguos.
- **D**: baja prioridad; con confianza alta puede ser un descarte razonado.

La prioridad manual no cambia la nota. Si no coincide con el modelo, aparece como discrepancia para revisión.
