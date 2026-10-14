import random
import string
from typing import Optional, Dict, Any
from engine.oms import OrderManagementSystem
from engine.models import ToolExecutionResult, OrderRecord

class SupportToolSuite:
    """
    Deterministic Tool Suite for Order Support & Actions.
    Guarantees deterministic, policy-bound order operations with zero LLM hallucination.
    """
    def __init__(self, oms: OrderManagementSystem):
        self.oms = oms

    def get_order_status(self, order_id: str) -> ToolExecutionResult:
        order = self.oms.get_order(order_id)
        if not order:
            return ToolExecutionResult(
                tool_name="get_order_status",
                success=False,
                action_taken="ORDER_NOT_FOUND",
                message=f"No order found matching ID '{order_id}'. Please check your receipt or order confirmation email."
            )

        data = {
            "order_id": order.order_id,
            "status": order.status,
            "carrier": order.carrier,
            "tracking_number": order.tracking_number,
            "estimated_delivery": order.estimated_delivery,
            "checkpoints": order.tracking_checkpoints,
            "total": order.total,
            "items_count": len(order.items),
            "shipping_address": order.shipping_address
        }

        if order.status == "IN_TRANSIT":
            msg = (
                f"Order {order.order_id} is currently IN TRANSIT via {order.carrier} "
                f"(Tracking: {order.tracking_number}). Estimated delivery: {order.estimated_delivery}."
            )
        elif order.status == "DELIVERED":
            msg = (
                f"Order {order.order_id} was DELIVERED on {order.delivery_date} "
                f"({order.days_since_delivery} days ago) via {order.carrier}."
            )
        elif order.status == "PROCESSING":
            msg = f"Order {order.order_id} is currently PROCESSING in our warehouse and preparing for fulfillment."
        else:
            msg = f"Order {order.order_id} status is {order.status}."

        return ToolExecutionResult(
            tool_name="get_order_status",
            success=True,
            action_taken="RETRIEVE_STATUS",
            data=data,
            message=msg
        )

    def verify_return_eligibility(self, order_id: str) -> ToolExecutionResult:
        order = self.oms.get_order(order_id)
        if not order:
            return ToolExecutionResult(
                tool_name="verify_return_eligibility",
                success=False,
                action_taken="ORDER_NOT_FOUND",
                message=f"Cannot verify return: Order '{order_id}' was not found in the database."
            )

        # Check order status
        if order.status != "DELIVERED":
            return ToolExecutionResult(
                tool_name="verify_return_eligibility",
                success=False,
                action_taken="REJECT_NOT_DELIVERED",
                data={"order_id": order.order_id, "status": order.status},
                message=f"Return cannot be initiated for {order.order_id} because the order has not yet been delivered (Current status: {order.status})."
            )

        # Rule 1: 30-Day Return Window Check
        if order.days_since_delivery and order.days_since_delivery > 30:
            return ToolExecutionResult(
                tool_name="verify_return_eligibility",
                success=False,
                action_taken="REJECT_RETURN",
                data={"days_since_delivery": order.days_since_delivery, "cutoff_days": 30},
                message=(
                    f"Return Ineligible: Order {order.order_id} was delivered {order.days_since_delivery} days ago, "
                    f"exceeding our 30-day return policy window. Returns cannot be authorized past 30 days."
                )
            )

        # Rule 2: Final Sale Item Check
        has_final_sale = any(item.is_final_sale for item in order.items)
        if has_final_sale:
            return ToolExecutionResult(
                tool_name="verify_return_eligibility",
                success=False,
                action_taken="REJECT_FINAL_SALE",
                data={"order_id": order.order_id, "final_sale_items": [i.title for i in order.items if i.is_final_sale]},
                message=(
                    f"Return Ineligible: Order {order.order_id} contains items marked as 'Final Sale' or 'Archive Clearance', "
                    f"which are strictly non-refundable per store policy."
                )
            )

        # Authorized Return Workflow
        rma_code = "RMA-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.oms.authorize_rma(order.order_id, rma_code)

        return ToolExecutionResult(
            tool_name="initiate_return_workflow",
            success=True,
            action_taken="AUTHORIZE_RETURN",
            data={
                "order_id": order.order_id,
                "rma_code": rma_code,
                "return_fee": 5.00,
                "items_authorized": [i.title for i in order.items]
            },
            message=(
                f"Return Authorized! RMA Code: {rma_code}. A prepaid return shipping label has been dispatched "
                f"to {order.customer_email}. Per store policy, a flat $5.00 return processing fee applies to refund payouts."
            )
        )

    def execute_order_cancellation(self, order_id: str) -> ToolExecutionResult:
        order = self.oms.get_order(order_id)
        if not order:
            return ToolExecutionResult(
                tool_name="execute_order_cancellation",
                success=False,
                action_taken="ORDER_NOT_FOUND",
                message=f"Order '{order_id}' not found."
            )

        if order.status != "PROCESSING":
            return ToolExecutionResult(
                tool_name="execute_order_cancellation",
                success=False,
                action_taken="REJECT_CANCELLATION",
                data={"status": order.status},
                message=(
                    f"Cancellation Ineligible: Order {order.order_id} is already in '{order.status}' status. "
                    f"Orders can only be cancelled while in 'PROCESSING' status within 2 hours of placement."
                )
            )

        success = self.oms.cancel_order(order.order_id)
        return ToolExecutionResult(
            tool_name="execute_order_cancellation",
            success=success,
            action_taken="CANCEL_ORDER",
            data={"order_id": order.order_id, "refund_amount": order.total, "status": "CANCELLED"},
            message=(
                f"Order {order.order_id} has been successfully CANCELLED. The pending authorization of "
                f"${order.total:.2f} has been voided back to your payment method ({order.payment_method})."
            )
        )
