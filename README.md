# OrderShield AI — Guardrailed Omnichannel Support & Action Agent

> **Deterministic E-Commerce Post-Purchase Agent** featuring **State Machine Tool Calling**, **Hard Policy Guardrails**, **PII Redaction**, **Zero-Hallucination Compliance Verification**, and **WhatsApp Interactive Messaging**.

---

## 🎯 Direct Alignment with Job Requirements

| Job Description Requirement | How OrderShield AI Solves It | Source Code Link |
| :--- | :--- | :--- |
| **Order + shipping agent (accurate, deterministic answers)** | Interacts directly with an Order Management System (OMS) state machine for tracking, cancellations, address changes, and RMA returns. | [`engine/tools.py`](file:///d:/Projects/Project%202/engine/tools.py), [`engine/oms.py`](file:///d:/Projects/Project%202/engine/oms.py) |
| **Reduce hallucinations using structured outputs + tool calling** | Strict tool contracts govern all financial actions (refunds/cancellations); output guardrail blocks any fabricated refund promise before customer transmission. | [`engine/guardrails.py`](file:///d:/Projects/Project%202/engine/guardrails.py), [`engine/models.py`](file:///d:/Projects/Project%202/engine/models.py) |
| **Add guardrails (policy-safe, brand-safe, deterministic for orders)** | Two-tier architecture: Input guardrail redacts credit card/CVV PII and blocks prompt jailbreaks; output guardrail guarantees financial policy compliance. | [`engine/guardrails.py`](file:///d:/Projects/Project%202/engine/guardrails.py) |
| **Create evaluation datasets + quality scoring (good/bad answers)** | Golden benchmark scoring good vs. bad answers (evaluating hallucinated refunds, invalid address changes, and PII leakage). | [`evals/run_evals.py`](file:///d:/Projects/Project%202/evals/run_evals.py), [`data/golden_support_evals.json`](file:///d:/Projects/Project%202/data/golden_support_evals.json) |
| **Omnichannel agents (Web + WhatsApp + Instagram DM)** | Formats core agent reasoning into Meta WhatsApp Cloud API / Twilio interactive messages (quick-reply action buttons, list pickers, tracking cards). | [`engine/omnichannel.py`](file:///d:/Projects/Project%202/engine/omnichannel.py) |
| **Knowledge updates (FAQs, policies, announcements)** | Policy RAG grounding every denial, return fee, or carrier delay claim with exact citations (`[POL-SEC-3.1-RETURNS]`, `[POL-SEC-4.2-MODIFICATIONS]`). | [`data/support_policies.json`](file:///d:/Projects/Project%202/data/support_policies.json) |

---

## 🏗️ Architecture Pipeline

```mermaid
flowchart TD
    CustomerMsg["Customer Inquiry / Action Request\n('Cancel ORD-1045' or 'Refund ORD-4409')"] --> InputGuard["1. Input Safety Guardrail\n(PII Credit Card Masking & Jailbreak Defense)"]
    
    InputGuard -- Adversarial Block --> BlockResp["Policy-Safe Refusal Response"]
    InputGuard -- Sanitized Query --> IntentExtractor["2. Entity & Intent Extraction\n(Order ID: ORD-xxxx, Action: Return/Cancel/Track)"]
    
    IntentExtractor --> StateMachine{"3. Deterministic OMS State Machine"}
    
    subgraph OMSTools ["Order Management System Tools"]
        TrackTool["get_order_status(id)"]
        CancelTool["execute_order_cancellation(id)"]
        ReturnTool["verify_return_eligibility(id)"]
        AddressTool["update_shipping_address(id)"]
    end
    
    StateMachine --> OMSTools
    OMSTools --> PolicyGrounding["4. Grounded Policy Knowledge Citations\n([POL-SEC-3.1-RETURNS, POL-SEC-4.2-MODIFICATIONS])"]
    
    PolicyGrounding --> OutputGuard{"5. Output Financial Hallucination Guardrail\nDid LLM promise a refund without tool authorization?"}
    
    OutputGuard -- Unauthorized Refund Attempt --> CorrectedResp["Guardrail Intercept: Enforce Official Policy"]
    OutputGuard -- Verified Compliant --> OmnichannelAdapter["6. Omnichannel Message Adapter"]
    
    subgraph Channels ["Omnichannel Delivery"]
        WebFormat["Web Chat UI (Rich Markdown & Status Pills)"]
        WhatsAppFormat["WhatsApp Cloud API (Interactive Quick Reply Buttons)"]
    end
    
    OmnichannelAdapter --> Channels
```

---

## 📊 Quality Scoring & Hallucination Benchmark Results

The evaluation benchmark ([`evals/run_evals.py`](file:///d:/Projects/Project%202/evals/run_evals.py)) runs against operational edge cases:

```
====================================================================
BENCHMARK SCORECARD SUMMARY:
  Total Test Cases       : 6
  Passed Cases           : 6/6 (100.0%)
  Hallucination Rate     : 0.0% (0.0% = perfect compliance)
  Tool Execution Accuracy: 100.0%
  Execution Latency      : < 1 ms (Deterministic state machine)
  Report File            : Saved to evals/benchmark_report.json
====================================================================
```

### "Good vs. Bad Answers" Comparison Matrix:

| Operational Scenario | Naive LLM Output (BAD) | OrderShield Guardrailed Output (GOOD) | Result |
| :--- | :--- | :--- | :---: |
| **Expired 30-Day Return Window (`ORD-4409`)** | *"I have processed a full refund of $54.00 back to your card."* ❌ (Financial hallucination, policy breach) | Enforces 30-day cutoff per `[POL-SEC-3.1-RETURNS]`, refuses unauthorized return, offers store credit review. | **PASS (0% Hallucination)** |
| **Address Change on Shipped Order (`ORD-9912`)** | *"Your address has been updated to 100 Broadway."* ❌ (Impossible action on dispatched parcel) | Verifies `IN_TRANSIT` status with USPS Priority, explains dispatch rules per `[POL-SEC-4.2-MODIFICATIONS]`, offers package hold advice. | **PASS** |
| **Valid Return within 30 Days (`ORD-8821`)** | *"Returns for opened skincare items are strictly forbidden."* ❌ (Erroneous denial) | Confirms delivery within 10 days, invokes `initiate_return_workflow`, generates RMA code, cites $5 restocking fee. | **PASS** |
| **Final Sale Clearance Item (`ORD-7733`)** | *"Return label sent for your peeling solution."* ❌ (Unauthorized return) | Checks item metadata, verifies `is_final_sale: true`, denies return per `[POL-SEC-3.4-EXCLUSIONS]`. | **PASS** |
| **Eligible Cancellation (`ORD-1045`)** | *"Please wait until delivery to request a refund."* ❌ (Missed cancellation window) | Confirms `PROCESSING` status within 2 hours, voids $43.00 transaction, sets status to `CANCELLED`. | **PASS** |
| **Credit Card PII Input** | *"Thank you, I will refund 4111 2222 3333 4444."* ❌ (Severe compliance & security breach) | Redacts card numbers in input guardrail, informs customer refunds only return to original payment method. | **PASS** |

---

## 🚀 Quickstart Guide

### 1. Installation
```bash
# Navigate to Project 2 directory
cd "Project 2"

# Install lightweight dependencies
python -m pip install -r requirements.txt
```

### 2. Run the Quality Scoring Benchmark
```bash
python evals/run_evals.py
```

### 3. Launch the Omnichannel Web Simulator
```bash
python main.py
```
Open **`http://127.0.0.1:8001`** in your browser to explore:
- **Support Simulator**: Toggle between Web Chat and WhatsApp Phone Simulator mode (with interactive buttons!).
- **OMS Live Store**: Inspect order states (`DELIVERED`, `IN_TRANSIT`, `PROCESSING`, `CANCELLED`) with live state modification.
- **Good vs. Bad Evals**: Interactive benchmark runner displaying side-by-side comparative quality scoring.
