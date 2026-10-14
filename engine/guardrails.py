import re
from typing import Tuple, List, Optional
from engine.models import GuardrailCheckResult, ToolExecutionResult

class OrderSupportGuardrails:
    """
    Two-Tier Guardrail Pipeline:
    1. Input Guardrails: PII Redaction (Credit Cards, CVVs) & Jailbreak Interceptor
    2. Output Guardrails: Financial Hallucination Verifier (Prevents unauthorized refund promises)
    """

    CREDIT_CARD_REGEX = r"\b(?:\d[ -]*?){13,16}\b"
    CVV_REGEX = r"\b(?:cvv|cvc|security\s*code)[:\s]*([0-9]{3,4})\b"
    
    JAILBREAK_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+(rules|instructions)",
        r"(act\s+as\s+an\s+admin|override\s+policy|developer\s+mode)",
        r"grant\s+(me\s+)?(immediate|full)\s+refund\s+without\s+verification",
        r"(drop\s+table|exec\s*\(|system\s*prompt)"
    ]

    def inspect_and_sanitize_input(self, query: str) -> GuardrailCheckResult:
        """
        Input Guardrail: Redacts credit cards and checks for adversarial prompt attacks.
        """
        flags: List[str] = []
        sanitized = query
        pii_found = False

        # 1. PII Redaction: Credit Cards
        if re.search(self.CREDIT_CARD_REGEX, sanitized):
            sanitized = re.sub(self.CREDIT_CARD_REGEX, "[REDACTED_CREDIT_CARD]", sanitized)
            flags.append("PII_CREDIT_CARD_MASKED")
            pii_found = True

        # PII Redaction: CVV codes
        if re.search(self.CVV_REGEX, sanitized, re.IGNORECASE):
            sanitized = re.sub(self.CVV_REGEX, "CVV [REDACTED_CVV]", sanitized, flags=re.IGNORECASE)
            flags.append("PII_CVV_MASKED")
            pii_found = True

        # 2. Jailbreak & Policy Override Defense
        for pattern in self.JAILBREAK_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return GuardrailCheckResult(
                    passed=False,
                    flags=["ADVERSARIAL_POLICY_OVERRIDE"],
                    pii_redacted=pii_found,
                    masked_query=sanitized,
                    severity="BLOCK",
                    reason="Security Violation: Direct policy overrides and administrative commands are prohibited."
                )

        if pii_found:
            return GuardrailCheckResult(
                passed=True,
                flags=flags,
                pii_redacted=True,
                masked_query=sanitized,
                severity="WARNING",
                reason="Sensitive financial payment info detected and masked for customer privacy."
            )

        return GuardrailCheckResult(
            passed=True,
            flags=[],
            pii_redacted=False,
            masked_query=sanitized,
            severity="INFO"
        )

    def verify_financial_output_compliance(
        self, 
        draft_response: str, 
        tool_result: Optional[ToolExecutionResult]
    ) -> Tuple[str, bool]:
        """
        Output Guardrail: Hallucination Prevention.
        Prevents LLM from telling a customer 'I have refunded your order' if the tool did not authorize it.
        """
        lower = draft_response.lower()
        promises_refund = any(p in lower for p in [
            "refund has been processed",
            "refund has been issued",
            "i have refunded",
            "full refund of",
            "credited back to your card"
        ])

        # If LLM claims a refund was processed, but tool_result is not AUTHORIZE_RETURN or REFUND
        if promises_refund and (tool_result is None or tool_result.action_taken not in ["AUTHORIZE_RETURN", "EXECUTE_REFUND"]):
            compliant_correction = (
                "⚠️ Compliance Guardrail Intercepted: An unauthorized refund statement was blocked. "
                "Per store policy, refunds can only be issued after return receipt and verification."
            )
            return compliant_correction, False

        return draft_response, True
