import json
import os
import sys
import re
from typing import List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.agent import OrderShieldAgent
from engine.models import EvalCaseScore

def run_support_benchmark(
    orders_db_path: str = "data/orders_db.json",
    policies_path: str = "data/support_policies.json",
    dataset_path: str = "data/golden_support_evals.json",
    output_report_path: str = "evals/benchmark_report.json"
) -> Dict[str, Any]:
    print("=" * 68)
    print("OrderShield AI — Support Quality Scoring & Hallucination Benchmark")
    print("=" * 68)

    agent = OrderShieldAgent(orders_db_path, policies_path)

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    results: List[EvalCaseScore] = []
    total_cases = len(test_cases)
    passed_cases = 0
    zero_hallucination_count = 0

    for tc in test_cases:
        t_id = tc["id"]
        scenario = tc["scenario"]
        query = tc["query"]
        expected_action = tc.get("expected_action")
        expected_tool = tc.get("expected_tool")
        expected_citations = tc.get("expected_citations", [])
        bad_pattern = tc.get("bad_answer_pattern")

        print(f"\n[Running {t_id}] Scenario: {scenario}")
        print(f"  Query: \"{query}\"")

        resp = agent.process_query(query)

        # 1. Hallucination Check (Bad answer pattern matching)
        hallucination_detected = False
        if bad_pattern and re.search(bad_pattern, resp.answer, re.IGNORECASE):
            hallucination_detected = True

        # 2. Tool Execution Check
        tool_correct = True
        if expected_tool:
            if resp.tool_executed is None or resp.tool_executed.tool_name != expected_tool:
                tool_correct = False

        # 3. Action Check
        action_correct = True
        if expected_action:
            if expected_action == "PII_REDACTION_ALERT":
                action_correct = resp.guardrail.pii_redacted
            elif expected_action == "REJECT_ADDRESS_CHANGE":
                action_correct = resp.tool_executed is not None and resp.tool_executed.action_taken == "REJECT_ADDRESS_CHANGE"
            elif resp.tool_executed:
                action_correct = resp.tool_executed.action_taken == expected_action
            else:
                action_correct = False

        # 4. Citations Check
        citations_matched = True
        if expected_citations:
            citations_matched = any(c in resp.policy_citations for c in expected_citations)

        # Overall Case Pass
        case_passed = not hallucination_detected and tool_correct and action_correct and citations_matched

        if not hallucination_detected:
            zero_hallucination_count += 1

        if case_passed:
            passed_cases += 1
            status_symbol = "[PASS]"
        else:
            status_symbol = "[FAIL]"

        explanation = (
            f"Action: {resp.tool_executed.action_taken if resp.tool_executed else 'GUARD_ONLY'} | "
            f"PII Redacted: {resp.guardrail.pii_redacted} | Citations: {resp.policy_citations} | Latency: {resp.latency_ms}ms"
        )

        print(f"  Result: {status_symbol} (Hallucination: {hallucination_detected}, Tool: {tool_correct})")
        print(f"  Details: {explanation}")

        results.append(EvalCaseScore(
            test_id=t_id,
            scenario=scenario,
            passed=case_passed,
            good_answer=case_passed,
            hallucination_detected=hallucination_detected,
            tool_called_correctly=tool_correct,
            citations_matched=citations_matched,
            latency_ms=resp.latency_ms,
            explanation=explanation
        ))

    pass_rate = round((passed_cases / total_cases) * 100, 1)
    hallucination_rate = round(((total_cases - zero_hallucination_count) / total_cases) * 100, 1)

    summary = {
        "total_test_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate_percentage": pass_rate,
        "hallucination_rate_percentage": hallucination_rate,
        "deterministic_tool_accuracy": 100.0 if pass_rate == 100.0 else pass_rate,
        "results": [r.model_dump() for r in results]
    }

    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 68)
    print("BENCHMARK SCORECARD SUMMARY:")
    print(f"  Total Test Cases       : {total_cases}")
    print(f"  Passed Cases           : {passed_cases}/{total_cases} ({pass_rate}%)")
    print(f"  Hallucination Rate     : {hallucination_rate}% (0.0% = perfect compliance)")
    print(f"  Tool Execution Accuracy: {summary['deterministic_tool_accuracy']}%")
    print(f"  Report File            : Saved to {output_report_path}")
    print("=" * 68)

    return summary

if __name__ == "__main__":
    run_support_benchmark()
