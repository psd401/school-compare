"""
Chat Page - AI chatbot for exploring Washington school data.
"""

import streamlit as st

from config.settings import get_settings
from src.chat.agent import ChatAgent

st.set_page_config(
    page_title="Chat - WA School Compare",
    page_icon="💬",
    layout="wide",
)


def main():
    st.title("💬 School Data Chat")
    st.markdown(
        "Ask questions about Washington state schools and districts. "
        "I can help you find schools, compare metrics, and explore data."
    )

    # Check for API key
    settings = get_settings()
    if not settings.has_google_key:
        st.error(
            "⚠️ Google API key not configured. "
            "Please set GOOGLE_API_KEY in your environment or .env file."
        )
        st.info(
            "To use the chatbot, you need a Google AI API key. "
            "Get one at https://aistudio.google.com/apikey"
        )
        return

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent" not in st.session_state:
        st.session_state.agent = ChatAgent()

    # Display example questions
    with st.expander("💡 Example questions you can ask", expanded=False):
        st.markdown(
            """
            - "What are the math proficiency rates for Seattle Public Schools?"
            - "Compare graduation rates between Bellevue and Tacoma districts"
            - "Find schools in Spokane county"
            - "What is the student-teacher ratio at Garfield High School?"
            - "Show me demographics for Kent School District"
            - "Which districts have the highest ELA proficiency in King County?"
            """
        )

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about Washington schools..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # Build conversation history for context
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]  # Exclude current message
            ]

            # Stream response
            try:
                for chunk in st.session_state.agent.chat(prompt, history):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)

            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                message_placeholder.markdown(error_msg)
                full_response = error_msg

        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Sidebar with chat controls
    with st.sidebar:
        st.header("Chat Controls")

        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

        st.divider()

        st.markdown("### About")
        st.markdown(
            """
            This chatbot uses Gemini AI to help you explore Washington state
            education data. It can:

            - Search for schools and districts
            - Retrieve assessment scores
            - Get demographic data
            - Look up graduation rates
            - Find staffing information

            Data source: [data.wa.gov](https://data.wa.gov)
            """
        )

        st.divider()

        st.caption(
            "Note: Data suppressed for privacy (n<10) will be marked with *. "
            "The AI may occasionally make mistakes - verify important findings."
        )


if __name__ == "__main__":
    main()
