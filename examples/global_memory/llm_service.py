import os
from typing import List, Dict
import litellm
from litellm import completion, acompletion
from models import Message, ChatSession
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, model: str = None):
        self.model = model or os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")

        # Configure LiteLLM
        self._configure_litellm()

    def _configure_litellm(self):
        """Configure LiteLLM with environment variables"""
        # Set various API keys from environment variables
        if os.getenv("OPENAI_API_KEY"):
            litellm.openai_key = os.getenv("OPENAI_API_KEY")

        if os.getenv("ANTHROPIC_API_KEY"):
            litellm.anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if os.getenv("GOOGLE_API_KEY"):
            litellm.google_key = os.getenv("GOOGLE_API_KEY")

        # AWS Bedrock configuration
        if os.getenv("AWS_ACCESS_KEY_ID"):
            litellm.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            litellm.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            litellm.aws_region_name = os.getenv("AWS_REGION", "us-east-1")

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response using LiteLLM"""
        try:
            logger.info(f"Generating response with model: {self.model}")
            logger.debug(f"Messages: {messages}")

            response = await acompletion(
                model=self.model, messages=messages, temperature=0.7, max_tokens=1000
            )

            content = response.choices[0].message.content
            logger.info("Response generated successfully")
            return content

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error: Unable to generate response. {str(e)}"

    def generate_response_sync(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response using LiteLLM (synchronous version)"""
        try:
            logger.info(f"Generating response with model: {self.model}")
            logger.debug(f"Messages: {messages}")

            response = completion(
                model=self.model, messages=messages, temperature=0.7, max_tokens=1000
            )

            content = response.choices[0].message.content
            logger.info("Response generated successfully")
            return content

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error: Unable to generate response. {str(e)}"

    async def generate_session_summary(self, session: ChatSession) -> str:
        """Generate a summary of the conversation session"""
        if not session.messages:
            return "Empty session with no messages."

        # Prepare conversation text for summarization
        conversation_text = self._format_conversation_for_summary(session.messages)

        summary_prompt = f"""
        Please provide a concise summary of the following conversation.
        Focus on the main topics discussed, key questions asked, and important information shared.
        Keep the summary under 200 words.

        Conversation:
        {conversation_text}

        Summary:
        """

        try:
            messages = [{"role": "user", "content": summary_prompt}]
            summary = await self.generate_response(messages)
            logger.info(f"Generated summary for session {session.session_id}")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error generating session summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def generate_session_summary_sync(self, session: ChatSession) -> str:
        """Generate a summary of the conversation session (synchronous version)"""
        if not session.messages:
            return "Empty session with no messages."

        # Prepare conversation text for summarization
        conversation_text = self._format_conversation_for_summary(session.messages)

        summary_prompt = f"""
        Please provide a concise summary of the following conversation.
        Focus on the main topics discussed, key questions asked, and important information shared.
        Keep the summary under 200 words.

        Conversation:
        {conversation_text}

        Summary:
        """

        try:
            messages = [{"role": "user", "content": summary_prompt}]
            summary = self.generate_response_sync(messages)
            logger.info(f"Generated summary for session {session.session_id}")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error generating session summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def _format_conversation_for_summary(self, messages: List[Message]) -> str:
        """Format conversation messages for summary generation"""
        conversation_lines = []
        for message in messages:
            if message.role == "system":
                continue  # Skip system messages in summary

            role_label = "User" if message.role == "user" else "Assistant"
            conversation_lines.append(f"{role_label}: {message.content}")

        return "\n".join(conversation_lines)

    def test_connection(self) -> bool:
        """Test if the LLM service is properly configured and accessible"""
        try:
            test_messages = [{"role": "user", "content": "Hello"}]
            response = self.generate_response_sync(test_messages)
            return not response.startswith("Error:")
        except Exception:
            return False
