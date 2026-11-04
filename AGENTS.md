```markdown
# AGENTS.md · PolyglotTalk

> Este fichero lo leen los agentes de programación (Copilot, Cursor, Codex, Gemini CLI y otros) antes de tocar vuestro código. Para Claude Code, cread un `CLAUDE.md` con una sola línea: `Sigue las instrucciones de AGENTS.md`. Para Gemini CLI, haced lo mismo con `GEMINI.md`.

## Qué es este proyecto

Tutor de idiomas interactivo que permite practicar conversaciones cotidianas en inglés, alemán y japonés con retroalimentación y correcciones gramaticales en tiempo real.

## Cómo está hecho

- Python 3.12.
- Interfaz: Streamlit.
- IA: API de Gemini con el SDK `google-genai`. El modelo está en la constante `MODELO` de `app.py`.
- Archivos: `app.py` (toda la app), `requirements.txt` (dependencias) y `README.md`.
- La especificación completa está en el cuaderno de Colab de la sesión.

## Reglas

- La clave de la API va SIEMPRE en secretos (`st.secrets` en la ruta A). Nunca en el código, en el README ni en el chat.
- Cada llamada a la API va dentro de `try/except` y muestra un mensaje claro para el usuario.
- Textos de la interfaz en español, sencillos, pensados para alguien sin conocimientos técnicos. El bot responderá en el idioma de práctica seleccionado.
- Cambios pequeños: uno por petición. Al terminar, explica qué has cambiado y por qué.
- Si añades una librería, añádela también a `requirements.txt` y dilo.
- No uses datos personales reales. Para probar, inventa ejemplos.

## Cómo comprobar que funciona

- Ruta A: `streamlit run app.py` en local (con `.streamlit/secrets.toml`), o haz push y revisa la app en Streamlit Cloud.
- Casos de prueba (entrada → lo que esperamos):
  1. Selección de Inglés + Escenario Cafetería + "I want order a coffee" → El bot responde siguiendo el rol y el panel de feedback indica que se debe usar "I want to order" o "I would like to order".
  2. Selección de Alemán + Escenario Cafetería + "Ich möchte kaffee" → El bot responde siguiendo el rol y el panel de feedback indica la capitalización correcta de "Kaffee".
  3. Entrada fuera de tema (ej: "¿Cómo hago una pizza?") → El bot o el tutor redirige amablemente la conversación hacia el escenario y el idioma de práctica seleccionado.

## Qué no hacer

- No borres ni reescribas el README sin preguntar.
- No cambies el modelo ni la arquitectura sin preguntar.
- No hagas push ni despliegues sin que yo lo haya revisado.
```
