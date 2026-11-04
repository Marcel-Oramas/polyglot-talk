import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from google import genai
from google.genai import errors
from streamlit.testing.v1 import AppTest


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


if __name__ == "__main__":
    unittest.main()
