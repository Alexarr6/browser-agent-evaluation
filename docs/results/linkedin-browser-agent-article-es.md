# Mismo modelo, tres arquitecturas de agente: 63 pruebas reales en el navegador

Cuando un agente falla en el navegador, es tentador culpar al modelo. Sin embargo, el modelo es sólo una parte del sistema. La forma de observar la página, decidir acciones, conservar contexto, recuperarse de errores y verificar el resultado puede cambiar por completo el comportamiento.

Para medir ese efecto comparé tres métodos de agente con el mismo modelo, las mismas tareas, el mismo navegador y los mismos límites:

- un agente propio con acciones restringidas;
- Browser Use;
- un agente conectado a Playwright MCP.

El resultado no fue un ganador universal. Cada arquitectura hizo visible un intercambio diferente entre capacidad de completar tareas, control, consumo y robustez.

## Qué comparé

Los tres agentes utilizaron `gpt-5.6-luna` mediante el endpoint directo de OpenAI. Cada uno ejecutó 21 pruebas: siete tareas repetidas tres veces.

Cinco tareas eran flujos relativamente estables:

- buscar y abrir un artículo en Wikipedia;
- localizar una referencia en MDN;
- completar un formulario de Selenium;
- interactuar con etiquetas cargadas mediante AJAX;
- reproducir una secuencia de teclado.

Las otras dos exigían adaptación sobre sitios públicos:

- abrir una noticia actual de la sección del Real Madrid en Marca y devolver su titular y URL;
- localizar en la primera página de resultados de Amazon.es un café en grano con un precio visible inferior a 14 EUR/kg, sin iniciar sesión, añadir al carrito ni comprar.

Todas las ejecuciones usaron Chromium 140, modo headless, un perfil visual equivalente, sesiones aisladas y un máximo de 300 segundos por tarea. Las tareas abiertas se validaron comparando la respuesta final del agente con datos observados directamente en el DOM por el controlador.

Esto es importante: llegar a una página de Amazon o encontrar el texto “Real Madrid” no contaba como éxito. El título, la URL, la identidad del producto y el precio por kilogramo tenían que coincidir con el estado visible final.

## Resultados observados

Sobre 21 intentos por agente:

- **Browser Use:** 21/21 tareas verificadas.
- **Playwright MCP:** 18/21.
- **Agente restringido:** 17/21.

Pero el agregado oculta una diferencia relevante.

En las 15 pruebas estándar:

- Browser Use: 15/15.
- Playwright MCP: 15/15.
- Agente restringido: 12/15.

En las seis pruebas abiertas de Marca y Amazon:

- Browser Use: 6/6.
- Agente restringido: 5/6.
- Playwright MCP: 3/6.

Browser Use fue el único método que completó todas las tareas observadas. MCP funcionó muy bien en los flujos rutinarios y resolvió Marca, pero falló los tres intentos de Amazon. El agente restringido quedó entre ambos en las tareas abiertas, con tres éxitos en Marca y dos en Amazon.

Estos números describen esta ejecución concreta. No demuestran que un framework siempre supere a otro ni que MCP sea incapaz de resolver Amazon con otra representación de estado o una estrategia diferente.

## El control determinista no es un cuarto agente

También ejecuté recetas deterministas de Playwright. Su papel requiere una distinción metodológica.

En las tareas estándar, esas recetas funcionan como controles de corrección para flujos conocidos y completaron 14 de 15 intentos. En Marca y Amazon, los controles consiguieron producir un estado válido en los tres intentos de cada tarea.

Sin embargo, esos 3/3 no se contabilizan como soluciones de las tareas abiertas.

Una receta determinista dispone de conocimiento privilegiado: selectores, rutas y lógica específica escrita previamente para ese sitio. No recibe una instrucción abierta y descubre una estrategia general. Si Marca cambia su sección o deja de publicar noticias con la estructura esperada, la receta puede fallar aunque un agente encuentre otra vía válida.

Por eso los controles abiertos sólo responden preguntas operativas:

- ¿el sitio estaba disponible?;
- ¿existía un objetivo que cumplía el contrato?;
- ¿el verificador podía reconocerlo?;

No responden si una arquitectura generaliza mejor. Sus resultados quedaron fuera de los denominadores y rankings de agentes. Además, el fallo de uno de estos controles no impide que los agentes intenten resolver la tarea.

## El consumo revela la arquitectura

Los tres métodos utilizaron el mismo modelo, pero no enviaron el mismo contexto.

Consumo total medido:

- **Agente restringido:** 263.325 tokens y 115 peticiones.
- **Browser Use:** 1.237.552 tokens y 136 peticiones.
- **Playwright MCP:** 1.623.505 tokens y 133 peticiones.

En conjunto, los agentes consumieron 3.124.382 tokens.

El agente restringido utilizó aproximadamente una quinta parte de los tokens de Browser Use y una sexta parte de los de MCP. Esa diferencia no procede del foundation model, sino del sistema construido a su alrededor.

El agente restringido recibe una observación acotada del árbol de accesibilidad y sólo puede proponer un pequeño conjunto de acciones semánticas. El controlador decide qué información entra, qué acciones son legales y cómo se recuperan targets obsoletos. Menos contexto reduce el consumo, pero también puede ocultar información útil o convertir una restricción de seguridad en un obstáculo para completar la tarea.

Browser Use aporta más estado, memoria de ejecución y lógica propia de evaluación y recuperación. En esta prueba, ese contexto adicional coincidió con la mayor tasa de finalización, aunque a costa de muchos más tokens.

MCP produjo respuestas del modelo relativamente compactas, pero los snapshots de accesibilidad y el historial acumulado de herramientas hicieron crecer los prompts. El caso extremo fue Amazon: 1.094.571 tokens entre tres intentos, sin una finalización verificada.

MCP no garantiza por sí mismo una estrategia eficiente. Estandariza la conexión con herramientas; la calidad de las observaciones, el control del historial y la recuperación siguen siendo decisiones de diseño.

## Tiempo: una métrica que necesita contexto

Tiempo acumulado de los 21 intentos de cada agente:

- Agente restringido: 418,1 segundos.
- Playwright MCP: 494,6 segundos.
- Browser Use: 518,8 segundos.

La mediana de los intentos completados fue de 21,2 segundos para el agente restringido, 13,2 para MCP y 25,3 para Browser Use.

Sería incorrecto concluir sólo con esto que MCP fue “el más rápido”. Los métodos no completaron la misma combinación de tareas. Un intento fallido puede terminar antes y reducir el tiempo total, mientras que una arquitectura más persistente puede emplear más tiempo y completar el trabajo.

En las tareas estándar, MCP sí combinó 15/15 resultados con el menor tiempo agregado entre los agentes. En Amazon, en cambio, produjo una cola larga de observación y reintentos sin alcanzar el estado requerido.

El tiempo debe leerse junto con el éxito verificado y el consumo, no como una clasificación independiente.

## El coste todavía no permite un ranking completo

Los artefactos registraron una estimación de USD 0,1017 para el agente restringido y USD 0,1964 para MCP. Browser Use no conservó coste por petición ni suficiente detalle de tokens cacheados para aplicar exactamente la misma regla contable.

Convertir su consumo total en una cifra supondría introducir hipótesis que no están en la evidencia. Por eso no presento un coste total ni una clasificación económica: los importes conocidos sirven para dimensionar el experimento, no para declarar qué método es más barato.

## Qué aporta cada enfoque

### Agente restringido: control y eficiencia

Su principal ventaja es que la aplicación conserva la autoridad. El modelo no recibe un navegador arbitrario: trabaja dentro de una gramática pequeña de acciones, allowlists de navegación, límites y políticas explícitas.

Es una opción atractiva cuando importan especialmente:

- la auditabilidad;
- el control de acciones permitidas;
- la previsibilidad del coste;
- la exposición mínima de estado al modelo.

El coste es de ingeniería. Hay que diseñar observaciones, acciones, recuperación y verificadores. Un vocabulario demasiado limitado puede impedir conductas legítimas. En esta ejecución fue el método más eficiente en tokens, pero falló dos pruebas de MDN, una del formulario y una de Amazon.

### Browser Use: adaptación y finalización

Browser Use obtuvo 21/21 en este conjunto y fue el método más consistente en las tareas abiertas. Su abstracción de más alto nivel permitió que el agente conservara suficiente contexto para adaptarse sin que el proyecto implementara toda la lógica de navegación desde cero.

Encaja bien cuando el objetivo principal es maximizar la capacidad de completar tareas heterogéneas y se acepta:

- delegar más comportamiento al framework;
- procesar observaciones más ricas;
- asumir mayor consumo;
- auditar una capa adicional de abstracción.

No dispongo de coste por petición ni detalle completo de tokens cacheados para Browser Use. Por tanto, no es posible publicar una clasificación económica exacta entre los tres métodos.

### Playwright MCP: interoperabilidad con una advertencia

MCP ofrece una interfaz estandarizada entre el modelo y las herramientas de navegador. En las tareas rutinarias, el resultado fue sólido: 15/15 y la menor mediana de tiempo entre los éxitos de los agentes.

Puede ser una buena opción cuando se busca:

- integrar herramientas existentes con rapidez;
- conservar operaciones de navegador explícitas;
- evitar construir un framework completo desde cero.

Pero el protocolo no resuelve automáticamente la gestión de contexto. Si cada observación añade snapshots grandes y el historial crece sin compresión útil, el agente puede gastar más tokens sin adquirir mejor información. Amazon mostró exactamente ese riesgo.

### Playwright determinista: para flujos conocidos

La automatización determinista sigue siendo la mejor referencia para procesos estables, repetitivos y suficientemente valiosos como para justificar mantenimiento específico.

Ofrece control, repetibilidad y cero consumo de modelo. Pero no debe confundirse con un agente. Una receta por sitio no demuestra capacidad para interpretar una instrucción nueva ni adaptarse a cambios imprevistos.

## Lo que este experimento no demuestra

La muestra tiene límites claros:

- sólo hubo tres repeticiones por tarea y método;
- se utilizó un único modelo;
- los sitios públicos pueden cambiar entre ejecuciones;
- latencia del proveedor, carga del sitio y cookies pueden afectar los resultados;
- las tareas abiertas verifican el estado final, no toda la trayectoria seguida;
- falta evidencia de coste homogénea para Browser Use;
- una única matriz no permite estimar fiabilidad de producción.

Tampoco es una comparación entre modelos. Mantener el mismo modelo base permitió aislar parcialmente el efecto de la arquitectura, pero no elimina todas las diferencias entre frameworks.

Para convertir estas observaciones en conclusiones más generales harían falta más fechas, seeds, modelos, dominios y una revisión humana ciega de las tareas abiertas.

## La decisión práctica no es “qué agente gana”

La pregunta útil es qué propiedad necesita maximizar el sistema.

- Si el flujo es conocido y estable, Playwright determinista ofrece la mayor previsibilidad.
- Si la prioridad es limitar autoridad y consumo, un agente restringido permite diseñar controles precisos.
- Si la prioridad es completar tareas variadas con menos infraestructura propia, Browser Use mostró la mejor cobertura en esta prueba.
- Si la prioridad es interoperar rápidamente con herramientas explícitas, MCP es una base potente, siempre que se controle el crecimiento del contexto.

La conclusión principal es más amplia: **el rendimiento de un agente de navegador pertenece al sistema completo, no sólo al modelo**.

Cambiar la observación, el repertorio de acciones, la memoria, la recuperación o el verificador puede alterar tanto el resultado como cambiar el propio modelo. Por eso evaluar agentes exige medir no sólo si terminaron, sino también qué autoridad recibieron, cuánto contexto consumieron, cómo se verificó el resultado y qué ocurrió cuando la página dejó de parecerse al caso ideal.

---

**Fuente de evidencia:** `runs/linkedin-20260907/run-manifest.json` y `docs/results/english-repeated-20260907.md`.

**Nota de publicación:** resultados observados en una matriz experimental; no constituyen una clasificación universal de frameworks ni una estimación de fiabilidad en producción.
