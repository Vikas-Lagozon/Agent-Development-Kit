"""
main.py — FastAPI Human-in-the-Loop endpoints.

Run with:
    python main.py
or:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import (
    ensure_session,
    run_agent_turn,
    pending_actions,
    sensitive_data_update,
)

app = FastAPI(title="HITL Privacy Guard API")

# -----------------------------------------------------------------------
# REQUEST MODELS
# -----------------------------------------------------------------------
class ChatRequest(BaseModel):
    user_input: str
    session_id: str

class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool

# -----------------------------------------------------------------------
# /chat — user sends a message; returns REQUIRES_APPROVAL if tool fired
# -----------------------------------------------------------------------
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Guarantee the session exists before talking to the runner
        await ensure_session(request.session_id)

        # Clear any stale pending action left over from a previous turn
        pending_actions.pop(request.session_id, None)

        # Run one agent turn
        agent_response = await run_agent_turn(request.session_id, request.user_input)

        # Check whether the HITL callback parked a tool call during this turn
        if request.session_id in pending_actions:
            pending = pending_actions[request.session_id]
            return {
                "status":         "REQUIRES_APPROVAL",
                "message":        f"Agent wants to call tool: '{pending['tool_name']}'",
                "tool_name":      pending["tool_name"],
                "arguments":      pending["arguments"],
                "agent_response": agent_response,
            }

        return {
            "status":  "SUCCESS",
            "message": agent_response,
        }

    except Exception as e:
        print(f"[/chat] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat Error: {str(e)}")


# -----------------------------------------------------------------------
# /approve — human approves or rejects the pending tool call
# -----------------------------------------------------------------------
@app.post("/approve")
async def approve_endpoint(request: ApprovalRequest):
    pending = pending_actions.get(request.session_id)

    if not pending:
        raise HTTPException(
            status_code=404,
            detail=(
                "No pending action found for this session. "
                "Either it was already resolved or the session_id is wrong."
            ),
        )

    try:
        if request.approved:
            # Execute the real tool locally (bypassing the agent)
            result = sensitive_data_update(**pending["arguments"])

            continuation = (
                f"The human APPROVED the action. "
                f"Tool '{pending['tool_name']}' was executed successfully. "
                f"Result: {result}. "
                "Please inform the user that their update has been completed."
            )
            status = "COMPLETED"
        else:
            continuation = (
                f"The human REJECTED the action. "
                f"Tool '{pending['tool_name']}' was NOT executed. "
                "Please inform the user that their request has been denied "
                "and no changes were made."
            )
            status = "DENIED"

        # Remove from pending store BEFORE continuing (prevents re-triggering)
        del pending_actions[request.session_id]

        # Let the agent compose a user-facing reply based on the outcome
        agent_response = await run_agent_turn(request.session_id, continuation)

        return {
            "status":         status,
            "agent_response": agent_response,
        }

    except Exception as e:
        print(f"[/approve] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Approval Error: {str(e)}")


# -----------------------------------------------------------------------
# RUN
# -----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
