# Mismo modelo, tres arquitecturas de agente y 63 pruebas en el navegador

Cuando un agente falla en una web, es fácil culpar al modelo. Pero el modelo es sólo una parte del sistema.

He comparado tres arquitecturas de agente usando `gpt-5.6-luna`, el mismo Chromium, los mismos límites y 21 ejecuciones por método. Cinco tareas eran acotadas y dos exigían adaptarse a páginas públicas.

Las tareas abiertas utilizaron verificadores sobre el estado final. Los scripts deterministas se mantuvieron como controles, pero no participaron en el ranking: una receta escrita específicamente para una web no es un agente generalista.

## Resultados

| Método | Acotadas | Abiertas | Total | Tokens |
|---|---:|---:|---:|---:|
| Agente restringido | 12/15 | 5/6 | 17/21 | 263.325 |
| Browser Use | 15/15 | 6/6 | 21/21 | 1.237.552 |
| Playwright MCP | 15/15 | 3/6 | 18/21 | 1.623.505 |

Browser Use fue el único que completó las 21 ejecuciones. Su memoria y su bucle de planificación le permitieron adaptarse mejor, aunque necesitó bastante más contexto que el agente restringido.

El resultado agregado de MCP necesita una matización. En las tareas acotadas consiguió 15/15 utilizando 407.840 tokens, frente a los 851.205 de Browser Use: menos de la mitad. Su consumo se disparó en una de las tareas abiertas, donde los snapshots y el historial hicieron crecer demasiado el prompt.

El agente restringido fue, con diferencia, el más eficiente. Su vocabulario limitado y sus observaciones controladas redujeron el consumo, pero también provocaron tres fallos en tareas acotadas y uno en las abiertas.

## No hay un ganador universal

Cada arquitectura optimiza algo distinto:

→ **Control y eficiencia:** un agente restringido permite decidir qué observa, qué acciones puede ejecutar y cómo se verifica el resultado.

→ **Adaptación:** Browser Use mostró la mayor capacidad para completar tareas heterogéneas sin implementar toda la navegación desde cero.

→ **Interoperabilidad:** Playwright MCP fue rápido y eficiente en flujos acotados, pero necesita controlar el crecimiento de snapshots e historial.

→ **Previsibilidad:** para un proceso conocido y estable, Playwright programado sigue siendo la opción más directa.

La conclusión no es que el modelo no importe. Es que su rendimiento pertenece al sistema completo: observación, herramientas, memoria, recuperación y verificación.

Antes de cambiar de modelo, quizá convenga revisar qué contexto le estamos dando.

¿Qué priorizas tú al automatizar un navegador con IA: control, autonomía, interoperabilidad o eficiencia?

Puedes consultar el código, las tareas y los resultados completos del experimento en GitHub: [enlace al repositorio].
