import os
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from google import genai
from google.genai import errors
from streamlit.testing.v1 import AppTest

from chat_export import format_conversation_print_html


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
OPENING_RESPONSE = '{"tutor_reply":"Welcome!","feedback":""}'
TUTOR_RESPONSE = '{"tutor_reply":"Sure!","feedback":"Looks good."}'


class FakeModels:
    def __init__(self, responses: list[str | errors.APIError]):
        self.responses = iter(responses)
        self.models_used: list[str] = []
        self.requests: list[tuple[str, object, object]] = []

    def generate_content(
        self, *, model: str, contents: object, config: object
    ) -> SimpleNamespace:
        self.models_used.append(model)
        self.requests.append((model, contents, config))
        response = next(self.responses)
        if isinstance(response, errors.APIError):
            raise response
        return SimpleNamespace(text=response)


class RetryFlowTests(unittest.TestCase):
    def make_unavailable_error(self) -> errors.ServerError:
        return errors.ServerError(
            503, {"error": {"message": "busy", "status": "UNAVAILABLE"}}
        )

    def make_rate_limit_error(self) -> errors.ClientError:
        return errors.ClientError(
            429, {"error": {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"}}
        )

    def run_app_with_responses(self, responses: list[str | errors.APIError]) -> AppTest:
        self.models = FakeModels(responses)
        self.client = SimpleNamespace(models=self.models)
        self.environment = patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client_patch = patch.object(genai, "Client", return_value=self.client)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        return AppTest.from_file(str(APP_PATH)).run()

    def click_retry(self, app: AppTest) -> AppTest:
        retry_button = next(
            button for button in app.button if button.label == "Reintentar respuesta"
        )
        return retry_button.click().run()

    def test_streamlit_theme_keeps_light_dark_and_system_choices(self) -> None:
        config_path = APP_PATH.parent / ".streamlit" / "config.toml"
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)

        self.assertNotIn("base", config.get("theme", {}))
        self.assertEqual(config["theme"]["light"]["primaryColor"], "#8795A8")
        self.assertEqual(config["theme"]["dark"]["primaryColor"], "#AAB7C7")

    def test_retry_reuses_failed_user_message(self) -> None:
        app = self.run_app_with_responses(
            [
                OPENING_RESPONSE,
                self.make_unavailable_error(),
                self.make_unavailable_error(),
                TUTOR_RESPONSE,
            ]
        )

        app.chat_input[0].set_value("Hello").run()

        self.assertEqual(len(app.session_state["messages"]), 2)
        self.assertEqual(app.session_state["pending_retry_index"], 1)
        self.assertTrue(app.chat_input[0].disabled)

        app = self.click_retry(app)

        messages = app.session_state["messages"]
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[1]["content"], "Hello")
        self.assertEqual(messages[1]["feedback"], "Looks good.")
        self.assertEqual(messages[2]["content"], "Sure!")
        self.assertIsNone(app.session_state["pending_retry_index"])
        self.assertFalse(app.chat_input[0].disabled)
        self.assertEqual(
            self.models.models_used,
            [
                "gemini-3.8-flash",
                "gemini-3.8-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
            ],
        )

    def test_normal_turn_saves_user_feedback_and_tutor_reply(self) -> None:
        app = self.run_app_with_responses([OPENING_RESPONSE, TUTOR_RESPONSE])

        app.chat_input[0].set_value("Hello").run()

        messages = app.session_state["messages"]
        self.assertEqual(
            [(message["role"], message["content"]) for message in messages],
            [
                ("assistant", "Welcome!"),
                ("user", "Hello"),
                ("assistant", "Sure!"),
            ],
        )
        self.assertEqual(messages[1]["feedback"], "Looks good.")
        self.assertEqual(
            [message.proto.name for message in app.chat_message],
            ["assistant", "user", "assistant"],
        )
        self.assertIsNone(app.session_state["pending_retry_index"])
        self.assertFalse(app.error)

    def test_conversation_can_be_printed(self) -> None:
        app = self.run_app_with_responses([OPENING_RESPONSE, TUTOR_RESPONSE])
        initial_print_html = format_conversation_print_html(
            "English",
            "cafe",
            app.session_state["messages"],
        )
        self.assertIn("disabled", initial_print_html)
        self.assertTrue(
            any("Envía tu primer mensaje" in item.value for item in app.info)
        )

        app.chat_input[0].set_value("Hello").run()

        print_html = format_conversation_print_html(
            "English",
            "cafe",
            app.session_state["messages"],
        )
        self.assertIn("window.print()", print_html)
        self.assertIn("Looks good.", print_html)
        self.assertIn("@media print", print_html)
        self.assertNotIn("disabled", print_html)
        self.assertFalse(app.get("download_button"))
        self.assertIn("Ctrl+P", app.sidebar.caption[-1].value)
        self.assertFalse(any("Envía tu primer mensaje" in item.value for item in app.info))

    def test_service_unavailable_uses_fallback_model(self) -> None:
        app = self.run_app_with_responses(
            [OPENING_RESPONSE, self.make_unavailable_error(), TUTOR_RESPONSE]
        )

        app.chat_input[0].set_value("Hello").run()

        self.assertEqual(
            self.models.models_used,
            [
                "gemini-3.8-flash",
                "gemini-3.8-flash",
                "gemini-3.5-flash-lite",
            ],
        )
        self.assertEqual(app.session_state["messages"][-1]["content"], "Sure!")

    def test_changing_settings_starts_a_clean_conversation(self) -> None:
        app = self.run_app_with_responses(
            [OPENING_RESPONSE, TUTOR_RESPONSE, OPENING_RESPONSE]
        )
        app.chat_input[0].set_value("Hello").run()
        app.session_state["conversation_summary"] = "old context"
        app.session_state["summarized_message_count"] = 2
        app.session_state["pending_retry_index"] = 1
        app.session_state["retry_error"] = "temporary error"

        app.selectbox[1].select("Hacer el check-in en un hotel").run()

        messages = app.session_state["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "assistant")
        self.assertEqual(messages[0]["content"], "Welcome!")
        self.assertEqual(app.session_state["conversation_summary"], "")
        self.assertEqual(app.session_state["summarized_message_count"], 0)
        self.assertIsNone(app.session_state["pending_retry_index"])
        self.assertIsNone(app.session_state["retry_error"])
        self.assertEqual(self.models.models_used, ["gemini-3.8-flash"] * 3)

    def test_custom_scenario_starts_and_resets_conversation(self) -> None:
        app = self.run_app_with_responses(
            [OPENING_RESPONSE, OPENING_RESPONSE, TUTOR_RESPONSE, OPENING_RESPONSE]
        )

        app.selectbox[1].select("Otro (tema personalizado)").run()
        self.assertTrue(app.chat_input[0].disabled)
        self.assertEqual(len(self.models.requests), 1)

        app.text_input[0].set_value("una entrevista de trabajo").run()
        self.assertEqual(len(app.session_state["messages"]), 1)
        self.assertIn(
            "una entrevista de trabajo",
            self.models.requests[1][2].system_instruction,
        )
        self.assertFalse(app.chat_input[0].disabled)

        app.chat_input[0].set_value("Tell me about the role").run()
        self.assertEqual(len(app.session_state["messages"]), 3)
        app.session_state["conversation_summary"] = "previous topic context"
        app.session_state["summarized_message_count"] = 2

        app.text_input[0].set_value("pedir comida en un restaurante").run()

        self.assertEqual(len(app.session_state["messages"]), 1)
        self.assertEqual(app.session_state["messages"][0]["content"], "Welcome!")
        self.assertIn(
            "pedir comida en un restaurante",
            self.models.requests[3][2].system_instruction,
        )
        self.assertEqual(app.session_state["conversation_summary"], "")
        self.assertEqual(app.session_state["summarized_message_count"], 0)

    def test_failed_retry_keeps_turn_available_without_duplicates(self) -> None:
        unavailable_errors = [self.make_unavailable_error() for _ in range(4)]
        app = self.run_app_with_responses(
            [OPENING_RESPONSE, *unavailable_errors, TUTOR_RESPONSE]
        )
        app.chat_input[0].set_value("Hello").run()

        app = self.click_retry(app)
        self.assertEqual(len(app.session_state["messages"]), 2)
        self.assertEqual(app.session_state["pending_retry_index"], 1)
        self.assertTrue(app.chat_input[0].disabled)
        self.assertTrue(
            any("No se pudo obtener una respuesta de Gemini" in error.value for error in app.error)
        )

        app = self.click_retry(app)

        self.assertEqual(len(app.session_state["messages"]), 3)
        self.assertEqual(app.session_state["messages"][1]["content"], "Hello")
        self.assertEqual(app.session_state["messages"][2]["content"], "Sure!")
        self.assertIsNone(app.session_state["pending_retry_index"])

    def test_rate_limit_uses_fallback_model(self) -> None:
        app = self.run_app_with_responses(
            [
                OPENING_RESPONSE,
                self.make_rate_limit_error(),
                TUTOR_RESPONSE,
            ]
        )

        app.chat_input[0].set_value("Hello").run()

        self.assertEqual(
            self.models.models_used,
            [
                "gemini-3.8-flash",
                "gemini-3.8-flash",
                "gemini-3.5-flash-lite",
            ],
        )
        self.assertEqual(len(app.session_state["messages"]), 3)
        self.assertEqual(app.session_state["messages"][-1]["content"], "Sure!")

    def test_old_turns_are_summarized_and_recent_context_is_bounded(self) -> None:
        responses = [
            OPENING_RESPONSE,
            *[TUTOR_RESPONSE for _ in range(9)],
            "summary-v1",
            TUTOR_RESPONSE,
            *[TUTOR_RESPONSE for _ in range(3)],
            "summary-v2",
            TUTOR_RESPONSE,
        ]
        app = self.run_app_with_responses(responses)

        for turn_number in range(1, 15):
            app.chat_input[0].set_value(f"learner turn {turn_number}").run()

        messages = app.session_state["messages"]
        self.assertEqual(len(messages), 29)
        self.assertEqual(app.session_state["conversation_summary"], "summary-v2")
        self.assertEqual(app.session_state["summarized_message_count"], 17)

        first_summary = self.models.requests[10][1][0]["parts"][0]["text"]
        self.assertIn("learner turn 1", first_summary)
        self.assertIn("learner turn 4", first_summary)
        self.assertNotIn("learner turn 5", first_summary)

        turn_ten_model, turn_ten_contents, turn_ten_config = self.models.requests[11]
        turn_ten_context = str(turn_ten_contents)
        self.assertEqual(turn_ten_model, "gemini-3.8-flash")
        self.assertNotIn("learner turn 4", turn_ten_context)
        self.assertIn("learner turn 5", turn_ten_context)
        self.assertIn("summary-v1", turn_ten_config.system_instruction)

        second_summary = self.models.requests[15][1][0]["parts"][0]["text"]
        self.assertIn("summary-v1", second_summary)
        self.assertIn("learner turn 5", second_summary)
        self.assertIn("learner turn 8", second_summary)
        self.assertNotIn("learner turn 9", second_summary)

        _, turn_fourteen_contents, turn_fourteen_config = self.models.requests[16]
        turn_fourteen_context = str(turn_fourteen_contents)
        self.assertNotIn("learner turn 8", turn_fourteen_context)
        self.assertIn("learner turn 9", turn_fourteen_context)
        self.assertIn("learner turn 14", turn_fourteen_context)
        self.assertIn("summary-v2", turn_fourteen_config.system_instruction)


if __name__ == "__main__":
    unittest.main()
