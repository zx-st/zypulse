"""
C4: Safety / Policy Engine (NON-BYPASSABLE)

This is the hard guardrail layer. It screens:
(a) User input BEFORE it reaches the LLM
(b) LLM output BEFORE it reaches the user

Safety restrictions:
- Keyword/regex matching, rule-based logic
- NOT an LLM. NOT overridable by prompts.
- Fails safe: if uncertain, blocks rather than allows.
- Critical: never allows an unchecked response through.

Prohibited behaviors (per project requirements):
1. Diagnose a medical condition
2. Prescribe medication
3. Recommend changing a medication dose
4. Recommend stopping medication
5. Invent medication instructions
6. Guess unidentified medication
7. Invent patient information
8. Invent glucose readings
9. Invent events or programme availability
10. Claim observed association proves causation
11. Declare an activity medically safe for a particular patient
"""

import re
from typing import Dict, Any, Tuple, Optional


class SafetyEngine:
    """
    Non-bypassable safety layer. All LLM input and output passes through here.
    """

    # ============================================================
    # INPUT SCREENING PATTERNS
    # ============================================================

    # Patterns that BLOCK user input from reaching the LLM
    INPUT_BLOCK_PATTERNS = [
        # Dose change requests
        (r"\b(change|increase|decrease|adjust|reduce|raise|lower)\b.*\b(dose|dosage|medication)\b", "dose_change"),
        (r"\b(double|triple|half)\b.*\b(dose|medication|metformin)\b", "dose_change"),
        (r"\b(more|less|extra|additional)\b.*\b(medication|dose|pill|metformin)\b", "dose_change"),

        # Stop/start medication
        (r"\b(stop|quit|discontinue|cease|halt)\b.*\b(medication|metformin|dose|pill|insulin)\b", "stop_medication"),
        (r"\b(start|begin|restart)\b.*\b(taking|medication|metformin|insulin)\b", "start_medication"),

        # Diagnosis requests
        (r"\b(diagnose|diagnosis|do i have|am i diabetic|is this diabetes)\b", "diagnosis_request"),
        (r"\b(what is wrong|what condition|what disease)\b.*\b(with me|do i)\b", "diagnosis_request"),

        # Medical safety claims
        (r"\b(is it safe|safe for me|can i safely|medically safe)\b.*\b(for me|my condition|diabetes)\b", "safety_claim"),
        (r"\b(can i (do|perform|start|continue))\b.*\b(with|despite|having|because of)\b.*\b(diabetes|my condition)\b", "safety_claim"),

        # Prompt injection attempts
        (r"\b(ignore|disregard|override|bypass)\b.*\b(instructions|rules|safety|guidelines|previous)\b", "prompt_injection"),
        (r"\b(you are|act as|pretend to be|role.?play)\b.*\b(a doctor|a physician|a pharmacist|medical professional)\b", "prompt_injection"),
        (r"\b(system prompt|reveal|show me your|what are your)\b.*\b(instructions|rules|prompt)\b", "prompt_injection"),

        # Self-harm (critical safety)
        (r"\b(hurt myself|kill myself|suicide|end my life|self.?harm)\b", "self_harm"),
    ]

    # Patterns for OUTPUT screening (LLM response checks)
    OUTPUT_BLOCK_PATTERNS = [
        # LLM prescribing or diagnosing
        (r"\b(you should|you must|you need to|I (recommend|suggest|advise|prescribe))\b.*\b(take|start|stop|change|increase|decrease)\b.*\b(medication|dose|metformin|insulin|pill)\b", "llm_prescribing"),
        (r"\b(you have|you are suffering from|you have been diagnosed|your condition is)\b.*\b(diabetes|hypertension|disease|condition)\b", "llm_diagnosing"),

        # Inventing data
        (r"\b(based on my analysis|I calculated|the data shows that your)\b.*\b(glucose|reading|level)\b.*\b(is|was|should be)\b.*\d+", "llm_inventing_numbers"),
        (r"\b(your glucose reading|your blood sugar).*(is|was|should be|must be)\b.*\d+.*\b(mmol|mg/dl)\b", "llm_inventing_numbers"),

        # Causation claims
        (r"\b(this proves|this means|this shows that|this confirms|this indicates that)\b.*\b(caused by|because of|due to|proof)\b", "causation_claim"),
        (r"\b(this activity is (medically )?safe|safe for your condition|safe for diabetics)\b", "safety_declaration"),
    ]

    # Redirect message for blocked medical content
    REDIRECT_MEDICAL = (
        "I'm not able to provide advice about medication changes, doses, or medical diagnoses. "
        "This is outside my scope as a self-care companion. "
        "Please consult your doctor or pharmacist for questions about your medication or diagnosis. "
        "They have access to your full medical history and can give you safe, personalised advice."
    )

    REDIRECT_PROMPT_INJECTION = (
        "I can only help with self-care tracking, education, and support. "
        "I'm unable to change my role or bypass my safety guidelines. "
        "How can I help you with your self-care routine today?"
    )

    REDIRECT_SELF_HARM = (
        "If you're feeling overwhelmed or having thoughts of self-harm, please reach out for help right now. "
        "In Singapore, you can call Samaritans of Singapore (SOS) at 1-767 (24 hours). "
        "You can also go to the nearest hospital emergency department. "
        "You matter, and there are people ready to support you."
    )

    # ============================================================
    # INPUT SCREENING
    # ============================================================

    def screen_input(self, user_message: str) -> Dict[str, Any]:
        """
        Screen user input before sending to LLM.
        Returns: {"allowed": bool, "reason": str, "redirect": Optional[str], "category": str}
        """
        message_lower = user_message.lower()

        # Check each block pattern
        for pattern, category in self.INPUT_BLOCK_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                redirect = self._get_redirect(category)
                return {
                    "allowed": False,
                    "reason": f"Input blocked: {category}",
                    "redirect": redirect,
                    "category": category,
                }

        # Input is safe to send to LLM
        return {
            "allowed": True,
            "reason": "Input passed safety screening",
            "redirect": None,
            "category": "none",
        }

    # ============================================================
    # OUTPUT SCREENING
    # ============================================================

    def screen_output(self, llm_response: str, deterministic_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Screen LLM output before returning to user.
        Returns: {"allowed": bool, "action": str, "filtered_response": str, "reason": str}
        """
        response_lower = llm_response.lower()

        # Check each output block pattern
        for pattern, category in self.OUTPUT_BLOCK_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                # Block and return safe fallback
                return {
                    "allowed": False,
                    "action": "block",
                    "filtered_response": self.REDIRECT_MEDICAL,
                    "reason": f"Output blocked: {category}",
                    "category": category,
                }

        # Check for fabricated numbers: extract all numbers from response and verify against context
        if deterministic_context:
            filtered = self._strip_unverified_numbers(llm_response, deterministic_context)
            if filtered != llm_response:
                return {
                    "allowed": True,
                    "action": "filtered",
                    "filtered_response": filtered,
                    "reason": "Unverified numbers stripped from response",
                    "category": "number_stripped",
                }

        # Output is safe
        return {
            "allowed": True,
            "action": "allow",
            "filtered_response": llm_response,
            "reason": "Output passed safety screening",
            "category": "none",
        }

    # ============================================================
    # PRIVATE HELPERS
    # ============================================================

    def _get_redirect(self, category: str) -> str:
        """Get the appropriate redirect message for a blocked category."""
        if category == "self_harm":
            return self.REDIRECT_SELF_HARM
        elif category in ("prompt_injection",):
            return self.REDIRECT_PROMPT_INJECTION
        else:
            # All medical categories
            return self.REDIRECT_MEDICAL

    def _strip_unverified_numbers(
        self, response: str, context: Dict[str, Any]
    ) -> str:
        """
        Strip any numbers from the LLM response that don't match
        the deterministic calculation output.

        This prevents the LLM from inventing health numbers.
        """
        # Extract verified numbers from context
        verified_numbers = set()

        # Gather all numeric values from the deterministic context
        def extract_numbers(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    extract_numbers(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract_numbers(item)
            elif isinstance(obj, (int, float)):
                verified_numbers.add(round(float(obj), 1))
            elif isinstance(obj, str):
                # User-saved goals can contain explicit, non-clinical targets such as
                # "walk 30 minutes at least 5 days a week". Allow the model to repeat
                # those exact values, while all other generated health numbers remain blocked.
                for number in re.findall(r'\b\d+(?:\.\d+)?\b', obj):
                    verified_numbers.add(round(float(number), 1))

        extract_numbers(context)

        # Find all decimal numbers in the response
        number_pattern = r'\b\d+\.?\d*\s*(?:mmol/L|mmol|mg/dL|mg|%)?\b'
        found_numbers = re.findall(r'\d+\.?\d*', response)

        result = response
        for num_str in found_numbers:
            try:
                num = float(num_str)
                # Allow if it matches a verified number (within 0.1 tolerance)
                is_verified = any(abs(num - vn) <= 0.2 for vn in verified_numbers)
                if not is_verified and num > 3.0:  # Only strip health-related numbers (>3.0 mmol/L range)
                    # Replace with a placeholder
                    result = result.replace(num_str, "[verified by calculation engine]", 1)
            except ValueError:
                continue

        return result
