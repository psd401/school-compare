"""LLM agent for chatbot interactions using Gemini with function calling."""

from typing import Generator
import google.generativeai as genai

from config.settings import get_settings
from .prompts import SYSTEM_PROMPT
from .tools import GEMINI_TOOLS, execute_tool


class ChatAgent:
    """Chat agent using Gemini with function calling for data queries."""

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        self.model = genai.GenerativeModel(
            model_name=settings.LLM_MODEL,
            system_instruction=SYSTEM_PROMPT,
            tools=GEMINI_TOOLS,
        )
        self.max_tokens = settings.LLM_MAX_TOKENS

    def chat(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> Generator[str, None, None]:
        """
        Send a message and yield the response.

        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation

        Yields:
            Text chunks as they are generated
        """
        # Convert conversation history to Gemini format
        gemini_history = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({
                "role": role,
                "parts": [msg["content"]]
            })

        # Create chat session with history
        chat = self.model.start_chat(history=gemini_history)

        # Send message and get response
        response = chat.send_message(user_message)

        # Process response, handling function calls
        while response.candidates[0].content.parts:
            # Check for function calls
            function_call = None
            text_parts = []

            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_call = part.function_call
                elif hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)

            # If there's a function call, execute it
            if function_call:
                tool_name = function_call.name
                tool_args = dict(function_call.args)

                yield "\n\n*Fetching data...*\n\n"

                # Execute the tool
                tool_result = execute_tool(tool_name, tool_args)

                # Send function response back to model
                response = chat.send_message(
                    genai.protos.Content(
                        parts=[genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": tool_result}
                            )
                        )]
                    )
                )
            else:
                # No function call - yield text and exit
                if text_parts:
                    yield "".join(text_parts)
                break

    def get_response(
        self,
        user_message: str,
        conversation_history: list[dict],
    ) -> str:
        """
        Get a complete response (non-streaming).

        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation

        Returns:
            Complete response text
        """
        return "".join(self.chat(user_message, conversation_history))
