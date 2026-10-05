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

PERSONALISATION:
- Use a user-shared goal, barrier, preference, location, or recent conversation only when relevant.
- Make one concrete connection rather than giving a generic list of tips.
- You may restate a number only when it appears in the deterministic context or a user-shared goal.
- Do not infer personal facts that are not in the deterministic or user-shared context.

FORMAT:
- Keep responses concise (3-5 sentences for conversational replies)
- Use plain language
- If the context contains trend data, reference it naturally
"""

BRIEFING_PROMPT = """Create a short Daily Briefing analysis using only the deterministic context.
Write two concise sentences: first describe only the available record or trend; second suggest one low-risk logging, reflection, or care-conversation action. If the user-shared context is relevant, make one specific connection to it; otherwise do not force personalisation. Do not diagnose, assess medical risk, prescribe, claim causation, or introduce any number that is not in the context. State when the available data is limited."""


class AIOrchestrator:
    """
    Manages the single LLM call per interaction.
    No agent loops, no tool-calling, no autonomous action.
    """

    def __init__(self, safety_engine: SafetyEngine):
        self.safety = safety_engine
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.api_url = os.environ.get("ZYPULSE_LLM_API_URL", "")
        self.api_key = os.environ.get("ZYPULSE_LLM_API_KEY", "")
        self.model = os.environ.get("OPENAI_MODEL", os.environ.get("ZYPULSE_LLM_MODEL", "gpt-5.4-mini"))

    def is_configured(self) -> bool:
        """Check if LLM API is configured."""
        return bool(self.openai_api_key or (self.api_url and self.api_key))

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

    def generate_briefing(self, context: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """Generate a short, safe explanation for the Daily Briefing screen."""
        prompt = self._assemble_prompt(BRIEFING_PROMPT, context, language)
        try:
            if not self.is_configured():
                return self._fallback_briefing(context, "LLM not configured")
            llm_response = self._call_llm(prompt)
            screen_result = self.safety.screen_output(llm_response, context)
            return {
                "response": screen_result["filtered_response"],
                "safety_status": "blocked" if not screen_result["allowed"] else ("filtered" if screen_result["action"] == "filtered" else "allow"),
                "safety_detail": screen_result["reason"],
            }
        except Exception as e:
            return self._fallback_briefing(context, f"LLM error: {str(e)}")

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
        language_names = {"en": "English", "zh": "Chinese"}
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

        user_context = context.get("user_context", {})
        if user_context:
            lines.append("\nUser-shared context (use only when relevant; do not infer beyond it):")
            fields = [
                ("Name", "display_name"), ("Area", "location_area"), ("Goals", "goals"),
                ("Reported barriers", "barriers"), ("Activity preferences", "activity_types"),
                ("Availability", "availability"),
            ]
            for label, key in fields:
                value = user_context.get(key)
                if value:
                    if isinstance(value, list):
                        value = "; ".join(str(item) for item in value)
                    lines.append(f"  - {label}: {value}")

        return "\n".join(lines) if lines else "No deterministic data available."

    def _call_llm(self, messages: list) -> str:
        """Make the actual LLM API call."""
        if self.openai_api_key:
            return self._call_openai_responses(messages)

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

    def _call_openai_responses(self, messages: list) -> str:
        """Call OpenAI's Responses API; the key remains server-side only."""
        instructions = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        input_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages if m["role"] in ("user", "assistant")
        ]
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.openai_api_key}"},
            json={"model": self.model, "instructions": instructions, "input": input_messages, "max_output_tokens": 220, "store": False},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("output_text"):
            return data["output_text"].strip()
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content.get("text", "").strip()
        raise ValueError("OpenAI returned no text output")

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

    def _fallback_briefing(self, context: Dict[str, Any], reason: str) -> Dict[str, Any]:
        gf = context.get("glucose_fasting", {})
        med = context.get("medication_adherence", {})
        if gf.get("average") is not None:
            text = f"Your verified fasting-glucose record shows a {gf.get('trend_direction', 'stable')} trend over the last {gf.get('days_requested', 7)} days. Keep logging your next routine record to build a clearer picture for discussion with your care team."
        elif med.get("adherence_rate") is not None:
            text = "Your medication-status records are available for review. Keep recording your next status so your self-care record remains clear."
        else:
            text = "There is not enough verified information for a trend explanation yet. Add your next routine record to start building a clearer self-care picture."
        return {"response": text, "safety_status": "fallback", "safety_detail": f"Deterministic fallback: {reason}"}
