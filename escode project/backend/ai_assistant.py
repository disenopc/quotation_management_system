from config import Config
import requests
import json

# ============================================================================
# BEDROCK MIGRATION GUIDE
# ============================================================================
# When you're ready to migrate to AWS Bedrock:
#
# 1. Set environment variable: USE_BEDROCK=True (and others to False)
# 2. Uncomment the bedrock imports below
# 3. Set AWS credentials in .env file
# 4. Uncomment _init_bedrock() and _generate_bedrock() implementations
# ============================================================================

# BEDROCK IMPORTS (uncomment when migrating)
# import boto3
# from botocore.config import Config as BotoConfig


class AIAssistant:
    """
    AI Assistant for generating email responses.
    Supports three providers:
    1. Local AI with Ollama (USE_LOCAL_AI=True)
    2. External Free AI like Groq (USE_EXTERNAL_FREE_AI=True)
    3. AWS Bedrock (USE_BEDROCK=True)
    """

    def __init__(self):
        self.use_bedrock = Config.USE_BEDROCK
        self.use_local_ai = Config.USE_LOCAL_AI
        self.use_external_free_ai = Config.USE_EXTERNAL_FREE_AI

        # Validate that only one provider is enabled
        enabled_count = sum(
            [self.use_bedrock, self.use_local_ai, self.use_external_free_ai]
        )
        if enabled_count == 0:
            raise ValueError(
                "No AI provider enabled. Set USE_LOCAL_AI, USE_EXTERNAL_FREE_AI, or USE_BEDROCK to True"
            )
        if enabled_count > 1:
            raise ValueError(
                "Multiple AI providers enabled. Only one can be active at a time"
            )

        # Initialize based on selected provider
        if self.use_local_ai:
            self._init_local_ai()
        elif self.use_external_free_ai:
            self._init_external_ai()
        elif self.use_bedrock:
            self._init_bedrock()

    def _init_local_ai(self):
        """Initialize Local AI with Ollama"""
        self.base_url = Config.LOCAL_AI_BASE_URL
        self.model = Config.LOCAL_AI_MODEL
        self.api_key = "ollama"  # Ollama doesn't need real API key
        print(f"AI Assistant initialized with LOCAL AI (Ollama) - Model: {self.model}")

    def _init_external_ai(self):
        """Initialize External Free AI (Groq, Together, etc)"""
        self.api_key = Config.EXTERNAL_AI_API_KEY
        self.base_url = Config.EXTERNAL_AI_BASE_URL
        self.model = Config.EXTERNAL_AI_MODEL

        if not self.api_key:
            raise ValueError(
                "EXTERNAL_AI_API_KEY is required. Get free key from your AI provider"
            )

        print(f"AI Assistant initialized with EXTERNAL FREE AI - Model: {self.model}")

    def _init_bedrock(self):
        """Initialize AWS Bedrock (only if USE_BEDROCK=True)"""
        # BEDROCK INITIALIZATION (uncomment when migrating)
        # boto_config = BotoConfig(
        #     region_name=Config.AWS_REGION,
        #     retries={'max_attempts': 3}
        # )
        #
        # self.bedrock_client = boto3.client(
        #     service_name='bedrock-runtime',
        #     region_name=Config.AWS_REGION,
        #     aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        #     config=boto_config
        # )
        # self.model_id = Config.BEDROCK_MODEL_ID
        # print(f"AI Assistant initialized with AWS Bedrock - Model: {self.model_id}")
        raise NotImplementedError(
            "Bedrock not configured yet. Set up AWS credentials and uncomment code above."
        )

    def generate_response(self, inquiry_subject, inquiry_message, context=None):
        """Generate AI response to inquiry"""
        if self.use_local_ai or self.use_external_free_ai:
            return self._generate_openai_compatible(
                inquiry_subject, inquiry_message, context
            )
        elif self.use_bedrock:
            return self._generate_bedrock(inquiry_subject, inquiry_message, context)

    def _generate_openai_compatible(self, subject, message, context):
        """Generate response using OpenAI-compatible API (Ollama or external)"""
        system_prompt = (
            "You are a professional business assistant helping to respond to client inquiries.\n"
            "Generate clear, helpful, and professional email responses.\n"
            "Be concise but thorough. Always maintain a friendly, professional tone."
        )

        # Extract user info from context if available
        user_signature = ""
        if context and isinstance(context, dict):
            user_name = context.get("user_name", "[Your Name]")
            user_email = context.get("user_email", "")
            user_phone = context.get("user_phone", "")
            user_position = context.get("user_position", "Sales Representative")

            user_signature = f"\n\nSign the email with this signature format:\n"
            user_signature += f"Best regards,\n{user_name}\n{user_position}"
            if user_phone:
                user_signature += f"\nPhone: {user_phone}"
            if user_email:
                user_signature += f"\nEmail: {user_email}"

        user_prompt = f"""Generate a professional response to this inquiry:

Subject: {subject}

Message: {message}

{f'Additional context: {context}' if context and not isinstance(context, dict) else ''}
{user_signature}

Generate only the email response text."""

        try:
            headers = {"Content-Type": "application/json"}
            if not self.use_local_ai:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            provider = "Ollama" if self.use_local_ai else "External AI"
            return f"Error generating {provider} response: {str(e)}"

    def _generate_bedrock(self, subject, message, context):
        raise NotImplementedError(
            "Bedrock implementation not active. Uncomment code above."
        )

    def generate_summary(self, text, max_length=200):
        """Generate summary of text"""
        if self.use_local_ai or self.use_external_free_ai:
            return self._summarize_openai_compatible(text, max_length)
        elif self.use_bedrock:
            return self._summarize_bedrock(text, max_length)

    def _summarize_openai_compatible(self, text, max_length):
        try:
            headers = {"Content-Type": "application/json"}
            if not self.use_local_ai:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Summarize this text in {max_length} characters or less:\n\n{text}",
                        }
                    ],
                    "temperature": 0.5,
                    "max_tokens": 150,
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            return text[:max_length] + "..." if len(text) > max_length else text

    def _summarize_bedrock(self, text, max_length):
        raise NotImplementedError("Bedrock summarization not implemented yet")

    def test_connection(self):
        """Test AI provider connection"""
        try:
            if self.use_local_ai or self.use_external_free_ai:
                headers = {"Content-Type": "application/json"}
                if not self.use_local_ai:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 10,
                    },
                    timeout=10,
                )
                response.raise_for_status()

                provider = "Ollama (Local)" if self.use_local_ai else "External Free AI"
                return {
                    "success": True,
                    "message": f"{provider} connection successful",
                    "provider": provider,
                    "model": self.model,
                }

            elif self.use_bedrock:
                return {
                    "success": False,
                    "message": "Bedrock not implemented yet",
                    "provider": "bedrock",
                }

        except Exception as e:
            provider = (
                "Ollama"
                if self.use_local_ai
                else "External AI" if self.use_external_free_ai else "Bedrock"
            )
            return {"success": False, "message": str(e), "provider": provider}


# ===================== GLOBAL INSTANCE & HELPERS =====================
# Create a global AI assistant instance
ai_assistant = AIAssistant()


def get_ai_response(subject, message, context=None):
    """Helper function to generate AI response for an inquiry"""
    return ai_assistant.generate_response(subject, message, context)


def get_inquiry_priority(message):
    """Determine inquiry priority based on message content"""
    message_lower = message.lower()
    if any(word in message_lower for word in ["urgent", "immediately", "asap"]):
        return "high"
    elif any(word in message_lower for word in ["soon", "important"]):
        return "medium"
    else:
        return "low"