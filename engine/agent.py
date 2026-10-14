import re
import time
import json
from typing import List, Dict, Any, Optional

from engine.models import (
    OrderRecord, SupportPolicy, ToolExecutionResult, GuardrailCheckResult,
    SupportAgentResponse, WhatsAppInteractiveMessage
)
from engine.oms import OrderManagementSystem
from engine.guardrails import OrderSupportGuardrails
from engine.tools import SupportToolSuite
from engine.omnichannel import OmnichannelAdapter

class OrderShieldAgent:
    """
    OrderShield AI — Post-Purchase Operations & Support Agent.
    Pipeline:
      1. Input Guardrail: PII Masking & Adversarial Defense
      2. Entity & Intent Extraction (Order ID, Action)
      3. Deterministic Tool Execution (OMS State Machine)
      4. Grounded Policy Citation Verification
      5. Output Compliance Guardrail (Financial Hallucination Shield)
      6. Omnichannel Payload Generation (Web + WhatsApp Interactive)
    """
    def __init__(self, orders_db_path: str, policies_path: str):
        self.oms = OrderManagementSystem(orders_db_path)
        self.guardrails = OrderSupportGuardrails()
        self.tools = SupportToolSuite(self.oms)
        self.adapter = OmnichannelAdapter()
        self.policies: Dict[str, SupportPolicy] = {}
        self._load_policies(policies_path)

    def _load_policies(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            for p in raw:
                pol = SupportPolicy(**p)
                self.policies[pol.id] = pol

    def _extract_order_id(self, query: str) -> Optional[str]:
        match = re.search(r"\b(ORD-\d{4})\b", query, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    def process_query(self, query: str) -> SupportAgentResponse:
        start_time = time.time()

        # Step 1: Input Guardrail Check & PII Masking
        guardrail_result = self.guardrails.inspect_and_sanitize_input(query)
        if not guardrail_result.passed and guardrail_result.severity == "BLOCK":
            latency = round((time.time() - start_time) * 1000, 2)
            msg = guardrail_result.reason or "Request blocked by safety policy."
            return SupportAgentResponse(
                query=query,
                sanitized_query=guardrail_result.masked_query,
                answer=msg,
                guardrail=guardrail_result,
                whatsapp_payload=self.adapter.format_whatsapp_payload(msg, None),
                latency_ms=latency
            )

        sanitized_query = guardrail_result.masked_query
        q_lower = sanitized_query.lower()
        order_id = self._extract_order_id(sanitized_query)

        # Step 2: Intent Classification & Deterministic Tool Execution
        tool_result: Optional[ToolExecutionResult] = None
        policy_citations: List[str] = []
        answer = ""

        # Case A: User explicitly provided payment info requesting a refund to a new card
        if guardrail_result.pii_redacted:
            answer = (
                "🔒 **Security Notice**: Payment and credit card numbers have been redacted for your protection. "
                "Per merchant security policy, refunds cannot be sent to new or third-party cards manually. "
                "Any authorized refund is automatically returned exclusively to the original payment method on file."
            )
            policy_citations = ["POL-SEC-3.1-RETURNS"]

        # Case B: Order ID detected -> Process deterministic operational workflow
        elif order_id:
            order = self.oms.get_order(order_id)
            if not order:
                answer = f"I could not locate order **{order_id}** in our order management system. Please check your order confirmation email."
            else:
                # 1. Return or Refund Request
                if any(w in q_lower for w in ["return", "refund", "money back", "send back"]):
                    tool_result = self.tools.verify_return_eligibility(order_id)
                    answer = tool_result.message

                    if tool_result.action_taken == "REJECT_RETURN":
                        policy_citations.append("POL-SEC-3.1-RETURNS")
                        answer += "\n\nIf you experienced a damaged item or clinical adverse reaction, our supervisor team can review an exception for store credit."
                    elif tool_result.action_taken == "REJECT_FINAL_SALE":
                        policy_citations.append("POL-SEC-3.4-EXCLUSIONS")
                    elif tool_result.action_taken == "AUTHORIZE_RETURN":
                        policy_citations.extend(["POL-SEC-3.1-RETURNS", "POL-SEC-3.7-FEES"])

                # 2. Cancellation Request
                elif any(w in q_lower for w in ["cancel", "stop order", "void"]):
                    tool_result = self.tools.execute_order_cancellation(order_id)
                    answer = tool_result.message
                    policy_citations.append("POL-SEC-4.2-MODIFICATIONS")

                # 3. Address Change Request
                elif any(w in q_lower for w in ["address", "moved", "change delivery", "street"]):
                    if order.status in ["IN_TRANSIT", "DELIVERED"]:
                        answer = (
                            f"Address Modification Denied: Order **{order.order_id}** is currently in **{order.status}** status "
                            f"(Carrier: {order.carrier}, Tracking: `{order.tracking_number}`). "
                            f"Once a package has departed our distribution center, carrier regulations prevent delivery address alterations. "
                            f"We recommend contacting {order.carrier} directly with your tracking number to request a package hold."
                        )
                        policy_citations.append("POL-SEC-4.2-MODIFICATIONS")
                        tool_result = ToolExecutionResult(
                            tool_name="get_order_status",
                            success=False,
                            action_taken="REJECT_ADDRESS_CHANGE",
                            data={"status": order.status, "carrier": order.carrier},
                            message=answer
                        )
                    else:
                        answer = f"Order **{order.order_id}** is in '{order.status}' status. Address modification is pending fulfillment coordinator confirmation."
                        policy_citations.append("POL-SEC-4.2-MODIFICATIONS")

                # 4. Tracking / Order Status Request
                else:
                    tool_result = self.tools.get_order_status(order_id)
                    answer = tool_result.message
                    if order.status == "IN_TRANSIT":
                        answer += f"\n\n📍 **Latest Scan**: {order.tracking_checkpoints[-1]['status']} at {order.tracking_checkpoints[-1]['location']} ({order.tracking_checkpoints[-1]['timestamp']})"

        # Case C: General Policy Questions without Order ID
        else:
            if any(w in q_lower for w in ["return", "policy", "refund", "days"]):
                answer = (
                    "**Store Return Policy Overview**:\n"
                    "• **Return Window**: Requests must be initiated within **30 days** of delivery.\n"
                    "• **Condition**: Gently opened skincare products with >50% content remaining are accepted.\n"
                    "• **Exclusions**: Final Sale and clearance items are non-returnable.\n"
                    "• **Restocking Fee**: A flat $5.00 return label fee is deducted from the refund total."
                )
                policy_citations.extend(["POL-SEC-3.1-RETURNS", "POL-SEC-3.4-EXCLUSIONS", "POL-SEC-3.7-FEES"])
            elif any(w in q_lower for w in ["shipping", "delivery", "carrier", "delay", "lost"]):
                answer = (
                    "**Shipping & Delivery Guidelines**:\n"
                    "• **Processing Time**: Orders placed before 2:00 PM EST ship the same business day.\n"
                    "• **Lost Packages**: If no carrier scan update occurs for 5 consecutive business days, we issue an immediate priority replacement."
                )
                policy_citations.append("POL-SEC-5.1-CLAIMS")
            else:
                answer = (
                    "I am your OrderShield support agent. Please provide your **Order ID** (e.g. `ORD-8821`) "
                    "or ask about our return policies, tracking, and cancellations."
                )

        # Step 3: Output Compliance Guardrail
        verified_answer, compliance_ok = self.guardrails.verify_financial_output_compliance(answer, tool_result)
        if not compliance_ok:
            guardrail_result.flags.append("OUTPUT_FINANCIAL_HALLUCINATION_BLOCKED")
            answer = verified_answer

        # Step 4: Generate Omnichannel (WhatsApp) Payload
        whatsapp_msg = self.adapter.format_whatsapp_payload(answer, tool_result, order_id)

        # Current live state of the order if available
        live_order = self.oms.get_order(order_id).model_dump() if order_id and self.oms.get_order(order_id) else None
        latency = round((time.time() - start_time) * 1000, 2)

        return SupportAgentResponse(
            query=query,
            sanitized_query=sanitized_query,
            answer=answer,
            tool_executed=tool_result,
            order_state=live_order,
            policy_citations=policy_citations,
            guardrail=guardrail_result,
            whatsapp_payload=whatsapp_msg,
            latency_ms=latency
        )
