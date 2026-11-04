from html import escape


def format_conversation_print_html(
    language: str,
    scenario: str,
    messages: list[dict[str, str | None]],
) -> str:
    has_student_message = any(message["role"] == "user" for message in messages)
    transcript = [
        "<!doctype html>",
        '<html lang="es"><head><meta charset="utf-8">',
        "<style>",
        "body{font-family:Arial,sans-serif;margin:0;color:#222;overflow:hidden}",
        "button{width:100%;padding:8px;border:1px solid #888;border-radius:6px;",
        "background:#fff;cursor:pointer;font-size:14px}",
        ".transcript{display:none}",
        "@media print{body{overflow:visible;margin:20mm}button{display:none}",
        ".transcript{display:block}h1{font-size:20pt}h2{font-size:14pt;",
        "break-after:avoid}.message{white-space:pre-wrap;overflow-wrap:anywhere}",
        ".feedback{white-space:pre-wrap;margin-top:8px;color:#444}",
        "@page{margin:18mm}}",
        "</style></head><body>",
        f'<button onclick="window.print()" {"disabled" if not has_student_message else ""}>'
        "Imprimir conversación</button>",
        '<main class="transcript">',
        "<h1>PolyglotTalk — Conversación</h1>",
        f"<p><b>Idioma:</b> {escape(language)}<br>",
        f"<b>Tema:</b> {escape(scenario)}</p>",
    ]
    for message in messages:
        speaker = "Estudiante" if message["role"] == "user" else "Tutor"
        transcript.extend(
            [
                f"<h2>{speaker}</h2>",
                f'<div class="message">{escape(str(message["content"]))}</div>',
            ]
        )
        if message.get("feedback"):
            transcript.extend(
                [
                    '<div class="feedback"><b>Feedback pedagógico:</b><br>',
                    f'{escape(str(message["feedback"]))}</div>',
                ]
            )
    transcript.extend(["</main></body></html>"])
    return "\n".join(transcript)
