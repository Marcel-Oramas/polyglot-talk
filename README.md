# PolyglotTalk

**Enlace a la app:** Pendiente de despliegue
**Autor/a:** Pendiente de completar

## Pitch

Quienes estudian un idioma suelen tener pocas oportunidades de practicar conversaciones cotidianas sin miedo a equivocarse. PolyglotTalk les permite practicar en inglés, alemán o japonés en escenarios como una cafetería, un hotel o la calle. Gemini mantiene la conversación en el idioma elegido y ofrece feedback constructivo en español después de cada respuesta. La prueba automatizada con respuestas simuladas confirmó el flujo de conversación y la presentación del feedback, pero todavía no se ha probado con una clave real de Gemini ni con estudiantes. El siguiente paso es probarlo con usuarios y desplegar la aplicación.

## El problema

Los estudiantes de nivel básico e intermedio necesitan practicar respuestas espontáneas y recibir correcciones relacionadas con lo que acaban de decir. Las lecciones rígidas no siempre ofrecen esa práctica contextual, y conversar con otras personas puede resultar intimidante. Un tutor disponible en cualquier momento puede ayudar a practicar con más confianza.

## Qué hace la app

1. El usuario elige inglés, alemán o japonés y un escenario: pedir café, hacer el check-in en un hotel o preguntar por direcciones.
2. El tutor inicia la conversación con una pregunta en el idioma elegido.
3. El usuario escribe una respuesta en el chat.
4. Gemini continúa la conversación y proporciona feedback en español sobre errores reales o formas más naturales de expresarse.
5. El historial permanece visible durante la sesión. Al cambiar de idioma o escenario, empieza una conversación nueva.

## La pieza de IA

- **Qué usa:** API de Gemini mediante el SDK oficial `google-genai`. El modelo predeterminado es `gemini-3.8-flash`; se puede cambiar con la variable `GEMINI_MODEL`. Si responde con un error 429 (límite de solicitudes) o 503 (servicio temporalmente no disponible), la app reintenta una vez con `gemini-3.5-flash-lite`, configurable con `GEMINI_FALLBACK_MODEL`.
- **Por qué esa opción:** Gemini permite generar una respuesta conversacional y feedback multilingüe en la misma llamada. La salida estructurada separa el mensaje del tutor del feedback pedagógico.
- **Qué pasa si falla:** La aplicación muestra un aviso si falta la clave o si Gemini devuelve un error. La clave se lee en el servidor desde `GEMINI_API_KEY`, ya sea como variable de entorno o mediante los secretos de Streamlit; no se incluye en el frontend.

## Cómo la he construido

- **Herramientas:** Python, Streamlit, SDK oficial `google-genai` y GitHub Copilot en VS Code.
- **Fichero de contexto del agente:** No se encontró un `AGENTS.md` en esta copia del repositorio.
- **Prompt clave del tutor:**

  ```text
  Eres PolyglotTalk, un tutor de idiomas empático para estudiantes de nivel básico a intermedio.
  Mantén la conversación dentro del escenario indicado y responde en el idioma objetivo.
  Después de cada respuesta del estudiante, da feedback breve y concreto en español:
  señala errores reales de gramática, ortografía o naturalidad, ofrece una corrección o alternativa
  natural y anima al estudiante. Si no hay errores, dilo claramente y destaca algo que hizo bien.
  No inventes errores. El feedback no debe sustituir la continuación de la conversación.
  Devuelve únicamente el objeto JSON con tutor_reply y feedback solicitado por el formato de respuesta.
  En el primer turno, saluda como el personaje del escenario, formula una pregunta sencilla y deja feedback vacío.
  ```

- **Qué delegué al agente y qué revisé a mano:** Se utilizó asistencia de Copilot para integrar Gemini y documentar la configuración. Se revisó el flujo de la aplicación y se validaron la carga sin clave y un turno de chat con respuestas simuladas; no se verificó una llamada en vivo a Gemini.

## Prueba y mejora

| Quién la probó | Qué probó | Qué pasó | Qué cambié |
|---|---|---|---|
| Prueba automatizada local | Inicio sin clave y conversación con respuesta simulada | Se mostró la indicación para configurar la clave; el chat conservó la respuesta y mostró el feedback por separado | Se agregó manejo del caso sin archivo de secretos y mensajes visibles ante errores de Gemini |

La prueba automatizada no reemplaza una prueba con usuarios ni una llamada real a la API.

## Ejecutar en local

1. Crea una clave en [Google AI Studio](https://aistudio.google.com/apikey).
2. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Configura la clave en el entorno:

   ```bash
   export GEMINI_API_KEY="tu-clave"
   ```

   O guárdala en `.streamlit/secrets.toml` (no subas ese archivo al repositorio):

   ```toml
   GEMINI_API_KEY = "tu-clave"
   ```

4. Inicia Streamlit:

   ```bash
   streamlit run app.py
   ```

Opcionalmente, selecciona otros modelos definiendo `GEMINI_MODEL` y `GEMINI_FALLBACK_MODEL`.

## Capturas

Pendientes: agregar capturas de la app en funcionamiento, un caso límite y la prueba, sin mostrar ninguna clave.
