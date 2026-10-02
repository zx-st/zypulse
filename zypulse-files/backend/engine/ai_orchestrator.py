"""
C5: AI Orchestrator (Single LLM Call)

The conversational AI brain. Receives a carefully constructed prompt and
generates a natural-language response. One LLM call per interaction.

Safety restrictions:
- System prompt includes explicit prohibitions
- Output is ALWAYS screened by C4 before reaching user
- If LLM generates numbers, they are stripped and replaced with C3 values
- NO direct database access, NO internet, NO tool-calling

Failure behaviour:
- If LLM unavailable: return deterministic fallback with C3 trends
"""

import os
import json
import requests
from typing import Dict, Any, Optional

from .safety import SafetyEngine


# ============================================================
# SYSTEM PROMPT - Safety rules + role definition + language directive
# ============================================================

SYSTEM_PROMPT = """You are ZyPulse, a personalised AI self-care companion for adults managing Type 2 diabetes. You are NOT a doctor, pharmacist, or medical professional.

YOUR ROLE:
- Help users track and understand their glucose readings, medication, and activity
- Provide educational support about diabetes self-care based on verified information
- Help users identify behavioural barriers and set achievable self-care goals
- Recommend community health activities based on user preferences
- Generate visit preparation summaries

CRITICAL SAFETY RULES - YOU MUST NEVER:
1. Diagnose a medical condition
2. Prescribe medication
3. Recommend changing a medication dose
4. Recommend stopping or starting medication
5. Invent medication instructions
6. Guess unidentified medication
7. Invent patient information or glucose readings
8. Invent events or programme availability
9. Claim that an observed association proves causation
10. Declare an activity medically safe for a particular patient

WHEN ASKED ABOUT MEDICATION OR DIAGNOSIS:
- Acknowledge the user's concern
- Explain that this is outside your scope
- Direct them to consult their doctor or pharmacist

WHEN DISCUSSING GLUCOSE READINGS:
- Use ONLY the numbers provided in the context below
- These numbers are calculated by deterministic code, not by you
- You may explain trends and patterns but never calculate or invent numbers
- Never claim a reading is "good" or "bad" in a clinical sense
- You may note whether a trend is increasing, decreasing, or stable

LANGUAGE:
- Respond in the user's selected language (specified below)
- If the language is not English and you are not confident in medical terminology, use simpler language
- Default to English if language is not specified

TONE:
- Warm, encouraging, practical
- Acknowledge challenges without being dismissive
- Focus on actionable self-care steps within the user's control
- Never use fear-based messaging

FORMAT:
- Keep responses concise (3-5 sentences for conversational replies)
- Use plain language
- If the context contains trend data, reference it naturally
"""


class AIOrchestrator:
    """
    Manages the single LLM call per interaction.
    No agent loops, no tool-calling, no autonomous action.
    """

    def __init__(self, safety_engine: SafetyEngine):
        self.safety = safety_engine
        self.api_url = os.environ.get("ZYPULSE_LLM_API_URL", "")
        self.api_key = os.environ.get("ZYPULSE_LLM_API_KEY", "")
        self.model = os.environ.get("ZYPULSE_LLM_MODEL", "hunyuan-standard")

    def is_configured(self) -> bool:
        """Check if LLM API is configured."""
        return bool(self.api_url and self.api_key)

    def generate_response(
        self,
        user_message: str,
        context: Dict[str, Any],
        language: str = "en",
        conversation_history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Generate a conversational response.

        Input:
        - user_message: already screened by C4 input
        - context: deterministic trends from C3 + user profile summary
        - language: user's selected language
        - conversation_history: recent messages for continuity

        Output:
        - {"response": str, "safety_status": str, "safety_detail": str, "trends": dict}
        """
        # Build the full prompt
        prompt = self._assemble_prompt(user_message, context, language, conversation_history)

        # Try LLM call
        if self.is_configured():
            try:
                llm_response = self._call_llm(prompt)
            except Exception as e:
                # LLM failed - return deterministic fallback
                return self._fallback_response(context, language, f"LLM error: {str(e)}")
        else:
            # LLM not configured - return deterministic fallback
            return self._fallback_response(context, language, "LLM not configured")

        # Screen LLM output through C4
        screen_result = self.safety.screen_output(llm_response, context)

        return {
            "response": screen_result["filtered_response"],
            "safety_status": "blocked" if not screen_result["allowed"] else ("filtered" if screen_result["action"] == "filtered" else "allow"),
            "safety_detail": screen_result["reason"],
            "trends": context,
        }

    def _assemble_prompt(
        self,
        user_message: str,
        context: Dict[str, Any],
        language: str,
        conversation_history: Optional[list] = None,
    ) -> list:
        """
        Assemble the full prompt as a list of messages.
        """
        language_names = {"en": "English", "zh": "Chinese", "ms": "Malay", "ta": "Tamil"}
        lang_name = language_names.get(language, "English")

        messages = []

        # System prompt with language directive
        system_content = SYSTEM_PROMPT + f"\n\nLANGUAGE DIRECTIVE: Respond in {lang_name}."
        messages.append({"role": "system", "content": system_content})

        # Context block (deterministic data)
        context_text = self._format_context(context)
        messages.append({
            "role": "system",
            "content": f"DETERMINISTIC CONTEXT (calculated by code, not AI. Use ONLY these numbers):\n\n{context_text}"
        })

        # Conversation history for continuity
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 6 messages
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        # Current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format the deterministic context into readable text for the LLM."""
        lines = []

        # Glucose trends
        if "glucose_fasting" in context:
            gf = context["glucose_fasting"]
            if gf.get("average") is not None:
                lines.append(f"Fasting glucose (last {gf['days_requested']} days):")
                lines.append(f"  - Average: {gf['average']} mmol/L")
                lines.append(f"  - Range: {gf['min_value']} - {gf['max_value']} mmol/L")
                lines.append(f"  - Trend: {gf['trend_direction']}")
                lines.append(f"  - Readings: {gf['readings_count']}")
            else:
                lines.append(f"Fasting glucose: {gf.get('notes', 'No data')}")

        if "glucose_evening" in context:
            ge = context["glucose_evening"]
            if ge.get("average") is not None:
                lines.append(f"\nEvening glucose (last {ge['days_requested']} days):")
                lines.append(f"  - Average: {ge['average']} mmol/L")
                lines.append(f"  - Trend: {ge['trend_direction']}")

        # Medication adherence
        if "medication_adherence" in context:
            ma = context["medication_adherence"]
            if ma.get("adherence_rate") is not None:
                lines.append(f"\nMedication adherence (last 30 days):")
                lines.append(f"  - Adherence rate: {ma['adherence_rate']}%")
                lines.append(f"  - Taken: {ma['taken_doses']}/{ma['expected_doses']} doses")
                lines.append(f"  - Missed: {ma['missed_doses']} doses")

        # Activity
        if "activity" in context:
            act = context["activity"]
            if not act.get("insufficient_data"):
                lines.append(f"\nActivity (last 30 days):")
                lines.append(f"  - Active days: {act['activity_days']}")
                lines.append(f"  - Total duration: {act['total_duration_min']} minutes")
                lines.append(f"  - Average per session: {act['avg_duration_min']} min")

        return "\n".join(lines) if lines else "No deterministic data available."

    def _call_llm(self, messages: list) -> str:
        """Make the actual LLM API call."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # Low temperature for consistency
            "max_tokens": 500,
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        # Handle OpenAI-compatible response format
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()

        # Handle Tencent Hunyuan format if different
        if "Response" in data:
            for choice in data["Response"].get("Choices", []):
                if "Message" in choice:
                    return choice["Message"]["Content"].strip()

        return ""

    def _fallback_response(
        self, context: Dict[str, Any], language: str, reason: str
    ) -> Dict[str, Any]:
        """
        Deterministic fallback when LLM is unavailable.
        Still provides useful information from C3 calculations.
        """
        lines = []

        if "glucose_fasting" in context:
            gf = context["glucose_fasting"]
            if gf.get("average") is not None:
                lines.append(
                    f"Your fasting glucose averaged {gf['average']} mmol/L "
                    f"over the last {gf['days_requested']} days "
                    f"(range: {gf['min_value']}-{gf['max_value']}, trend: {gf['trend_direction']})."
                )

        if "medication_adherence" in context:
            ma = context["medication_adherence"]
            if ma.get("adherence_rate") is not None:
                lines.append(
                    f"Medication adherence: {ma['adherence_rate']}% "
                    f"({ma['taken_doses']} of {ma['expected_doses']} doses taken)."
                )

        if "activity" in context:
            act = context["activity"]
            if not act.get("insufficient_data"):
                lines.append(
                    f"You logged activity on {act['activity_days']} day(s) "
                    f"totalling {act['total_duration_min']} minutes."
                )

        if not lines:
            response_text = "I don't have enough data to show trends yet. Please log some readings and I'll help you track your progress."
        else:
            response_text = " ".join(lines) + " I wasn't able to generate a conversational response right now. Please try again shortly."

        return {
            "response": response_text,
            "safety_status": "fallback",
            "safety_detail": f"Deterministic fallback: {reason}",
            "trends": context,
        }
