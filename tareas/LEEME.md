# Cómo usar estos paquetes con OpenCode

1. Abre OpenCode en la carpeta del proyecto, en una sesión nueva por tarea.
2. Pega este mensaje (cambia `D01` por la tarea que toca):

   > Lee `AGENTS.md`. Tu tarea es **D01**. Sigue literalmente `tareas/D01.md`. Las pruebas ya existen y fallan a propósito: haz que pasen sin editarlas. Una sola tarea; al terminar, haz el commit que pide la hoja y detente.

3. Orden: **D01 → D03 → D04a**. Una sesión y un commit por tarea. D02, D04b, D05 y D06 están bloqueadas.
4. Antes de dar por buena una tarea, el supervisor revisa el commit (`git show --stat`) y vuelve a correr `pytest`.
5. Si OpenCode toca `tests/`, `reglas/` o archivos que la hoja no menciona: deshaz con `git checkout -- <archivo>` y pídele que lo rehaga.
