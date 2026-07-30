# Scouting Hub v1.2

Aplicación Streamlit de scouting personal basada en un flujo rápido:

**partido → alineación flexible → minutos/nota/MVP → ranking**.

La base se entrega completamente vacía para empezar desde cero.

## Novedades v1.2

- 18 formaciones predefinidas.
- Opción **Personalizada** con entre 1 y 20 titulares.
- Número inicial de suplentes configurable entre 0 y 30.
- La tabla permite añadir y borrar filas dinámicamente.
- Columna **Titular** editable: cualquier dibujo puede corregirse sobre la marcha.
- Relleno inicial desde la plantilla, desde el último partido del equipo o completamente vacío.
- Control de MVP único o compartido.
- Opción para registrar o ignorar convocados sin minutos.
- Edición y eliminación de partidos desde la interfaz.
- Edición y eliminación de observaciones históricas.
- Rankings ordenables por Score Heras, nota, MVP, prioridad, proyección, rol, confianza o consistencia.
- Filtros adicionales por competición, muestra mínima, nota y MVP.
- Podio visual y exportación del ranking filtrado.
- Página de jugadores con fichas pendientes de completar.
- Investigación por competición y tramo de edad.
- Constructor de alineaciones con roles compatibles y estructuras personalizadas.
- Perfiles de scoring: Excel simple, equilibrado y proyección.
- Todos los textos, backups y metadatos actualizados a **v1.2**.

## Despliegue en Streamlit Community Cloud

1. Descomprime el ZIP.
2. Sube **todo el contenido** a la raíz de tu repositorio.
3. Haz commit y push a la rama usada por Streamlit.
4. Selecciona `streamlit_app.py` como archivo principal.
5. Conserva las carpetas `scouting_hub/`, `data/`, `templates/` y `.streamlit/`.

## Ejecución local

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## Validación

```bash
python validate_project.py
python -m unittest discover -s tests -v
```

## Persistencia

Streamlit Community Cloud no debe considerarse almacenamiento permanente. Descarga periódicamente el **Backup ZIP** o el **Excel estilo BBDD** desde la aplicación.
