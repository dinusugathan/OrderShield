from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class OrderItem(BaseModel):
    sku: str
    title: str
    price: float
    quantity: int
    is_final_sale: bool = False

class OrderRecord(BaseModel):
    order_id: str
    customer_name: str
    customer_email: str
    order_date: str
    status: str                         # PROCESSING, IN_TRANSIT, DELIVERED, CANCELLED, RETURNED
    delivery_date: Optional[str] = None
    days_since_delivery: Optional[int] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[str] = None
    tracking_checkpoints: List[Dict[str, str]] = Field(default_factory=list)
    shipping_address: Dict[str, str] = Field(default_factory=dict)
    items: List[OrderItem] = Field(default_factory=list)
    subtotal: float
    shipping_fee: float = 0.0
    total: float
    payment_method: str
    return_status: str = "NONE"         # NONE, RMA_AUTHORIZED, RETURN_IN_TRANSIT, REFUNDED

class SupportPolicy(BaseModel):
    id: str
    topic: str
    rule: str
    citation: str

class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    action_taken: str                   # e.g., "RETRIEVE_TRACKING", "REJECT_RETURN", "CANCEL_ORDER", "INITIATE_RMA"
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str

class GuardrailCheckResult(BaseModel):
    passed: bool = True
    flags: List[str] = Field(default_factory=list)
    pii_redacted: bool = False
    masked_query: str = ""
    severity: str = "INFO"              # INFO, WARNING, BLOCK
    reason: Optional[str] = None

class WhatsAppInteractiveMessage(BaseModel):
    type: str = "interactive"           # button, list, or text
    body_text: str
    action_buttons: List[Dict[str, str]] = Field(default_factory=list)
    header_text: Optional[str] = None
    footer_text: Optional[str] = None

class SupportAgentResponse(BaseModel):
    query: str
    sanitized_query: str
    answer: str
    tool_executed: Optional[ToolExecutionResult] = None
    order_state: Optional[Dict[str, Any]] = None
    policy_citations: List[str] = Field(default_factory=list)
    guardrail: GuardrailCheckResult = Field(default_factory=GuardrailCheckResult)
    whatsapp_payload: WhatsAppInteractiveMessage
    latency_ms: float = 0.0

class EvalCaseScore(BaseModel):
    test_id: str
    scenario: str
    passed: bool
    good_answer: bool
    hallucination_detected: bool
    tool_called_correctly: bool
    citations_matched: bool
    latency_ms: float
    explanation: str
