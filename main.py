import os
import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.agent import OrderShieldAgent
from engine.models import SupportAgentResponse
from evals.run_evals import run_support_benchmark

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORDERS_PATH = os.path.join(BASE_DIR, "data", "orders_db.json")
POLICIES_PATH = os.path.join(BASE_DIR, "data", "support_policies.json")
EVAL_PATH = os.path.join(BASE_DIR, "evals", "benchmark_report.json")
STATIC_DIR = os.path.join(BASE_DIR, "web")

app = FastAPI(
    title="OrderShield AI — Guardrailed Omnichannel Support & Action Agent",
    version="1.0.0",
    description="Deterministic post-purchase e-commerce agent with state machine tool calling, hard policy guardrails, and WhatsApp interactive messaging."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agent
agent = OrderShieldAgent(ORDERS_PATH, POLICIES_PATH)

class QueryRequest(BaseModel):
    query: str

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "OrderShield AI",
        "active_orders": len(agent.oms.orders),
        "policy_count": len(agent.policies)
    }

@app.post("/api/chat", response_model=SupportAgentResponse)
def handle_support_query(payload: QueryRequest):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    return agent.process_query(payload.query.strip())

@app.get("/api/orders")
def get_orders():
    return [o.model_dump() for o in agent.oms.list_orders()]

@app.post("/api/orders/reset")
def reset_orders():
    agent.oms.reset_db()
    return {"status": "success", "message": "OMS database reset to original test state."}

@app.get("/api/policies")
def get_policies():
    with open(POLICIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/evals")
def get_evals():
    if not os.path.exists(EVAL_PATH):
        return run_support_benchmark(ORDERS_PATH, POLICIES_PATH, output_report_path=EVAL_PATH)
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/evals/run")
def trigger_evals():
    return run_support_benchmark(ORDERS_PATH, POLICIES_PATH, output_report_path=EVAL_PATH)

# Mount Static Web Assets
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Use port 8001 so both Project 1 (port 8000) and Project 2 (port 8001) can run side-by-side!
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
