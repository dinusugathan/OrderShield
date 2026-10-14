from typing import List, Dict, Any, Optional
from engine.models import ToolExecutionResult, WhatsAppInteractiveMessage

class OmnichannelAdapter:
    """
    Omnichannel Message Formatter:
    Transforms core agent reasoning and tool execution outputs into production-ready
    payloads for Web Chat, WhatsApp Cloud API, and SMS.
    """

    @staticmethod
    def format_whatsapp_payload(
        text_body: str, 
        tool_result: Optional[ToolExecutionResult],
        order_id: Optional[str] = None
    ) -> WhatsAppInteractiveMessage:
        """
        Builds a Meta WhatsApp Cloud API / Twilio Interactive Message schema
        with contextual Quick Reply buttons.
        """
        buttons: List[Dict[str, str]] = []

        if tool_result:
            if tool_result.action_taken == "RETRIEVE_STATUS":
                tracking = tool_result.data.get("tracking_number")
                if tracking:
                    buttons.append({"id": "btn_track", "title": "Track Carrier 📦"})
                buttons.append({"id": "btn_help", "title": "More Details ℹ️"})
                buttons.append({"id": "btn_agent", "title": "Human Support 👤"})

            elif tool_result.action_taken == "AUTHORIZE_RETURN":
                buttons.append({"id": "btn_label", "title": "Get Return Label 📄"})
                buttons.append({"id": "btn_policy", "title": "Return Policy 📋"})

            elif tool_result.action_taken in ["REJECT_RETURN", "REJECT_FINAL_SALE"]:
                buttons.append({"id": "btn_policy", "title": "View Policy 📖"})
                buttons.append({"id": "btn_escalate", "title": "Talk to Supervisor 🙋"})

            elif tool_result.action_taken == "CANCEL_ORDER":
                buttons.append({"id": "btn_receipt", "title": "Email Receipt ✉️"})
                buttons.append({"id": "btn_shop", "title": "Browse Products 🛍️"})
        else:
            # Default conversation buttons
            buttons.append({"id": "btn_track_order", "title": "Track My Order 🚚"})
            buttons.append({"id": "btn_return", "title": "Start a Return 🔄"})
            buttons.append({"id": "btn_faq", "title": "Store FAQs ❓"})

        # WhatsApp buttons limit: max 3 interactive quick reply buttons
        clean_buttons = buttons[:3]

        return WhatsAppInteractiveMessage(
            type="interactive_button",
            header_text=f"OrderShield Support • {order_id}" if order_id else "OrderShield Support",
            body_text=text_body,
            footer_text="Reply STOP to unsubscribe • Powered by OrderShield AI",
            action_buttons=clean_buttons
        )

    @staticmethod
    def format_web_display(text_body: str, policy_citations: List[str]) -> str:
        """
        Formats markdown text for rich Web UI presentation.
        """
        formatted = text_body
        if policy_citations:
            citations_str = " ".join([f"`[{c}]`" for c in policy_citations])
            formatted += f"\n\n*Verified Policy Reference*: {citations_str}"
        return formatted
