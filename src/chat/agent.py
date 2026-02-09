"""LLM agent for chatbot interactions using Gemini with function calling."""

from typing import Generator
from google import genai
from google.genai import types

from config.settings import get_settings
from .prompts import SYSTEM_PROMPT
from .tools import GEMINI_TOOLS, execute_tool


class ChatAgent:
    """Chat agent using Gemini with function calling for data queries."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model_name = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[GEMINI_TOOLS],
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
        )

    def chat(
        self,
        user_message: str,
        conversation_history: list[dict],
        context: str = "",
    ) -> Generator[str, None, None]:
        """
        Send a message and yield the response.

        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation
            context: Optional session context string to append to system prompt

        Yields:
            Text chunks as they are generated
        """
        # Use context-augmented config if context is provided
        if context:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT + "\n\n" + context,
                tools=[GEMINI_TOOLS],
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            )
        else:
            config = self.config

        # Convert conversation history to google.genai Content format
        genai_history = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            genai_history.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
            )

        # Create chat session with history
        chat = self.client.chats.create(
            model=self.model_name,
            config=config,
            history=genai_history,
        )

        # Send message and get response
        response = chat.send_message(message=user_message)

        # Process response, handling function calls
        while True:
            # Check for function calls
            if response.function_calls:
                function_call = response.function_calls[0]
                tool_name = function_call.name
                tool_args = dict(function_call.args)

                yield "\n\n*Fetching data...*\n\n"

                # Execute the tool
                tool_result = execute_tool(tool_name, tool_args)

                # Send function response back via chat session
                function_response = types.Part.from_function_response(
                    name=tool_name,
                    response={"result": tool_result},
                )
                response = chat.send_message(message=function_response)
            else:
                # No function call - yield text and exit
                if response.text:
                    yield response.text
                break

    def get_response(
        self,
        user_message: str,
        conversation_history: list[dict],
        context: str = "",
    ) -> str:
        """
        Get a complete response (non-streaming).

        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation
            context: Optional session context string

        Returns:
            Complete response text
        """
        return "".join(self.chat(user_message, conversation_history, context=context))
