# Auditoría de la v0.7 y decisiones de la v0.8

## Problemas detectados

1. **Archivo monolítico**: la lógica de datos, scoring, diseño y páginas convivía en un único script de más de 1.800 líneas.
2. **Datos semilla mezclados con la aplicación**: al arrancar, la base podía repoblar países y competiciones aunque el objetivo fuese empezar desde cero.
3. **Potencial condicionado por edad**: el motor añadía puntos por ser joven, lo que podía confundir juventud con proyección real.
4. **Estado manual dentro de la urgencia**: marcar un jugador como prioritario influía indirectamente en su ranking y generaba circularidad.
5. **Encaje demasiado genérico**: el rol existía como etiqueta, pero el score se apoyaba principalmente en cinco notas macro.
6. **Confianza como descuento multiplicativo**: la poca evidencia tendía a rebajar el resultado, en lugar de acercarlo a una zona neutral.
7. **IDs secuenciales**: podían colisionar al unir CSV procedentes de varias copias de la app.
8. **Escritura directa**: un fallo durante el guardado podía dejar un CSV incompleto.
9. **Comparación visual limitada**: faltaban radar real, percentiles, similitud funcional, distribución y alineaciones guardables.
10. **Backup sin migración amplia**: la restauración esperaba rutas concretas dentro del ZIP.

## Soluciones aplicadas

- Refactor en módulos: configuración, almacenamiento, dominio, scoring, visuales, páginas y aplicación.
- Todos los CSV de scouting quedan con cabecera y cero filas.
- Roles con seis criterios y pesos propios.
- Potencial manual sin bonificación automática por edad.
- Prioridad manual solo como señal de discrepancia.
- Contracción del score hacia 50 cuando la confianza es baja.
- IDs basados en UUID corto.
- Guardado atómico con archivo temporal y reemplazo.
- Snapshot automático antes de restaurar o borrar.
- Restauración por nombre de archivo, incluso si el ZIP contiene una carpeta raíz antigua.
- Radar SVG, percentiles, comparador, strip plot, similitud y constructor de alineaciones sin dependencias gráficas externas.
