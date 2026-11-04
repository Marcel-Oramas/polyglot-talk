import json
import os

import streamlit as st
from google import genai
from google.genai import errors, types
from streamlit.errors import StreamlitSecretNotFoundError


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
LANGUAGES = {
    "Inglés 🇬🇧": "English",
    "Alemán 🇩🇪": "German",
    "Japonés 🇯🇵": "Japanese",
}
SCENARIOS = [
    "Pedir café en una cafetería",
    "Hacer el check-in en un hotel",
    "Preguntar por direcciones en la calle",
]
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "tutor_reply": {
            "type": "STRING",
            "description": "The tutor's next conversational message in the target language.",
        },
        "feedback": {
            "type": "STRING",
            "description": "Constructive language feedback in Spanish, or an empty string for the opening.",
        },
    },
    "required": ["tutor_reply", "feedback"],
}
SYSTEM_INSTRUCTION = """Eres PolyglotTalk, un tutor de idiomas empático para estudiantes de nivel básico a intermedio.
Mantén la conversación dentro del escenario indicado y responde en el idioma objetivo.
Después de cada respuesta del estudiante, da feedback breve y concreto en español:
señala errores reales de gramática, ortografía o naturalidad, ofrece una corrección o alternativa
natural y anima al estudiante. Si no hay errores, dilo claramente y destaca algo que hizo bien.
No inventes errores. El feedback no debe sustituir la continuación de la conversación.
Devuelve únicamente el objeto JSON con tutor_reply y feedback solicitado por el formato de respuesta.
En el primer turno, saluda como el personaje del escenario, formula una pregunta sencilla y deja feedback vacío."""


def get_api_key() -> str | None:
    try:
        secret_api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, StreamlitSecretNotFoundError):
        secret_api_key = None
    return secret_api_key or os.getenv("GEMINI_API_KEY")


def make_contents(messages: list[dict[str, str | None]]) -> list[dict[str, object]]:
    contents: list[dict[str, object]] = []
    for message in messages:
        role = "user" if message["role"] == "user" else "model"
        contents.append(
            {"role": role, "parts": [{"text": str(message["content"])}]}
        )
        feedback = message.get("feedback")
        if feedback:
            contents.append(
                {
                    "role": "model",
                    "parts": [{"text": f"Feedback anterior: {feedback}"}],
                }
            )
    return contents


def generate_tutor_turn(
    client: genai.Client,
    language: str,
    scenario: str,
    messages: list[dict[str, str | None]],
    opening: bool = False,
) -> dict[str, str]:
    contents = make_contents(messages)
    if opening:
        contents.append(
            {
                "role": "user",
                "parts": [
                    {
                        "text": "Inicia una conversación de práctica en este escenario. "
                        "Saluda y haz una pregunta sencilla.",
                    }
                ],
            }
        )

    config = types.GenerateContentConfig(
        system_instruction=(
            f"{SYSTEM_INSTRUCTION}\nIdioma objetivo: {language}.\n"
            f"Escenario: {scenario}."
        ),
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )
    with st.spinner("El tutor está pensando..."):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config,
            )
        except errors.APIError as exc:
            if exc.code != 503 or MODEL == FALLBACK_MODEL:
                raise
            response = client.models.generate_content(
                model=FALLBACK_MODEL,
                contents=contents,
                config=config,
            )
            st.warning(
                f"El modelo principal está temporalmente ocupado. "
                f"Esta respuesta se generó con el modelo alternativo {FALLBACK_MODEL}."
            )

    try:
        result = json.loads(response.text or "")
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini devolvió una respuesta que no se pudo interpretar.") from exc

    if (
        not isinstance(result, dict)
        or not isinstance(result.get("tutor_reply"), str)
        or not result["tutor_reply"].strip()
        or not isinstance(result.get("feedback"), str)
    ):
        raise ValueError("Gemini devolvió una respuesta incompleta. Inténtalo de nuevo.")
    return result


st.set_page_config(
    page_title="PolyglotTalk - Tutor de Idiomas", page_icon="🗣️", layout="centered"
)
st.title("🗣️ PolyglotTalk")
st.subheader("Tu Tutor de Idiomas Inteligente")
st.write(
    "Practica conversaciones de la vida real en inglés, alemán o japonés "
    "con feedback constructivo al instante."
)

st.sidebar.header("Configuración del Tutor")
language_label = st.sidebar.selectbox("Selecciona el idioma:", list(LANGUAGES))
scenario = st.sidebar.selectbox("Selecciona un escenario:", SCENARIOS)

settings = (language_label, scenario)
if st.session_state.get("conversation_settings") != settings:
    st.session_state.messages = []
    st.session_state.conversation_settings = settings
    st.session_state.pending_retry_index = None
    st.session_state.retry_error = None

if st.sidebar.button("Reiniciar Conversación"):
    st.session_state.messages = []
    st.session_state.pending_retry_index = None
    st.session_state.retry_error = None
    st.rerun()

api_key = get_api_key()
if not api_key:
    st.info(
        "Para empezar, configura `GEMINI_API_KEY` como variable de entorno o "
        "en `.streamlit/secrets.toml`. Consulta `README.md` para más detalles."
    )
else:
    client = genai.Client(api_key=api_key)
    if not st.session_state.messages:
        try:
            opening_turn = generate_tutor_turn(
                client,
                LANGUAGES[language_label],
                scenario,
                [],
                opening=True,
            )
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": opening_turn["tutor_reply"],
                    "feedback": None,
                }
            )
        except (errors.APIError, ValueError) as exc:
            st.error(f"No se pudo iniciar la conversación con Gemini: {exc}")

for message in st.session_state.get("messages", []):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("feedback"):
            st.info(f"💡 **Feedback Pedagógico:** {message['feedback']}")

pending_retry_index = st.session_state.get("pending_retry_index")
if pending_retry_index is not None:
    if st.session_state.get("retry_error"):
        st.error(
            "No se pudo obtener una respuesta de Gemini: "
            f"{st.session_state.retry_error}"
        )

    if st.button("Reintentar respuesta", disabled=not api_key):
        try:
            tutor_turn = generate_tutor_turn(
                client,
                LANGUAGES[language_label],
                scenario,
                st.session_state.messages,
            )
        except (errors.APIError, ValueError) as exc:
            st.session_state.retry_error = str(exc)
            st.rerun()
        else:
            pending_message = st.session_state.messages[pending_retry_index]
            pending_message["feedback"] = tutor_turn["feedback"]
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": tutor_turn["tutor_reply"],
                    "feedback": None,
                }
            )
            st.session_state.pending_retry_index = None
            st.session_state.retry_error = None
            st.rerun()

if user_input := st.chat_input(
    "Escribe tu respuesta aquí...",
    disabled=not api_key or pending_retry_index is not None,
):
    user_message = {"role": "user", "content": user_input, "feedback": None}
    try:
        tutor_turn = generate_tutor_turn(
            client,
            LANGUAGES[language_label],
            scenario,
            [*st.session_state.messages, user_message],
        )
    except (errors.APIError, ValueError) as exc:
        st.session_state.messages.append(user_message)
        st.session_state.pending_retry_index = len(st.session_state.messages) - 1
        st.session_state.retry_error = str(exc)
        st.rerun()
    else:
        user_message["feedback"] = tutor_turn["feedback"]
        st.session_state.messages.extend(
            [
                user_message,
                {
                    "role": "assistant",
                    "content": tutor_turn["tutor_reply"],
                    "feedback": None,
                },
            ]
        )
        st.rerun()
