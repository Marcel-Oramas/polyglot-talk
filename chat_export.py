def format_conversation_markdown(
    language: str,
    scenario: str,
    messages: list[dict[str, str | None]],
) -> str:
    transcript = [
        "# PolyglotTalk — Conversación",
        "",
        f"- **Idioma:** {language}",
        f"- **Tema:** {scenario}",
        "",
    ]
    for message in messages:
        speaker = "Estudiante" if message["role"] == "user" else "Tutor"
        transcript.extend([f"## {speaker}", "", str(message["content"]), ""])
        if message.get("feedback"):
            transcript.extend(
                ["**Feedback pedagógico:**", "", str(message["feedback"]), ""]
            )
    return "\n".join(transcript).rstrip() + "\n"
