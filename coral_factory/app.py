from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from arcadepy import Arcade
from dotenv import load_dotenv
import uvicorn
import os
import uuid
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from factory.builder import WorkflowConfig
from factory.runner import WorkflowRunner

# Authentication configuration
load_dotenv()
BEARER_TOKEN = os.getenv("FACTORY_BEARER_TOKEN", "bearer-token-2024")

# FastAPI app
app = FastAPI(
    title="Factory API", 
    description="API for creating and deploying AI agent workflows with Bearer token authentication"
)

# Security scheme
security = HTTPBearer()

# Track running workflows
running_workflows = {}
workflow_logs = {}  # NEW: Store logs for each workflow

class RunWorkflowRequest(BaseModel):
    workflow_config: dict
    user_id: str
    user_task: str
    
    class Config:
        arbitrary_types_allowed = True

class RunWorkflowResponse(BaseModel):
    success: bool
    trace_id: str


# NEW: Helper function to add logs
def add_workflow_log(trace_id: str, message: str, log_type: str = "info", data: any = None):
    """Add a log entry to a workflow"""
    if trace_id not in workflow_logs:
        workflow_logs[trace_id] = []
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "message": message
    }
    
    if data:
        log_entry["data"] = data
    
    workflow_logs[trace_id].append(log_entry)
    logger.info(f"[{trace_id}] {message}")


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the bearer token"""
    if credentials.credentials != BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


@app.post("/verify/workflow")
async def verify_workflow(request: Request, token: str = Depends(verify_token)):
    """Verify a workflow configuration"""
    body = await request.json()
    print("\n🟡 RAW REQUEST BODY RECEIVED BY FASTAPI:\n", body, "\n")
    return JSONResponse(content={"success": True, "received": body})


@app.post("/run/workflow/local")
async def run_workflow(request: Request, token: str = Depends(verify_token)):
    try:
        body = await request.json()
        logger.info(f"🔍 RAW REQUEST BODY:\n{json.dumps(body, indent=2)}")
        
        run_workflow_request = RunWorkflowRequest(**body)
        trace_id = str(uuid.uuid4())
        
        # NEW: Initialize logs for this workflow
        workflow_logs[trace_id] = []
        add_workflow_log(trace_id, f"🚀 Workflow started: {run_workflow_request.user_task}", "info")
        
        workflow_config_dict = run_workflow_request.workflow_config
        
        if workflow_config_dict.get('relations_type') == 'single':
            workflow_config_dict['relations_type'] = 'chain'
            add_workflow_log(trace_id, "🔄 Mapped relations_type 'single' to 'chain'", "info")
        
        workflow_config = WorkflowConfig(**workflow_config_dict)
        add_workflow_log(trace_id, "✅ Workflow config validated", "info")
        
        runner = WorkflowRunner(
            workflow_config=workflow_config,
            user_id=run_workflow_request.user_id,
            user_task=run_workflow_request.user_task,
            trace_id=trace_id
        )
        
        add_workflow_log(trace_id, "▶️ Starting workflow runner...", "info")
        runner.start()
        running_workflows[trace_id] = runner
        add_workflow_log(trace_id, "🏃 Workflow is now running", "info")
        
        return JSONResponse(content={"success": True, "trace_id": trace_id})
        
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        if 'trace_id' in locals():
            add_workflow_log(trace_id, f"❌ Error: {str(e)}", "error")
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(e),
                "error_type": type(e).__name__
            }
        )


@app.get("/workflow/status/{trace_id}")
async def get_workflow_status(trace_id: str):
    """Get the status of a workflow"""
    if trace_id not in running_workflows:
        return JSONResponse(content={"success": False, "trace_id": trace_id, "status": "not_found"})
    return JSONResponse(content={"success": True, "trace_id": trace_id, "status": running_workflows[trace_id].status})


@app.get("/workflow/result/{trace_id}")
async def get_workflow_result(trace_id: str):
    """Get the result of a workflow"""
    if trace_id not in running_workflows:
        return JSONResponse(content={"success": False, "trace_id": trace_id, "status": "not_found"})
    
    runner = running_workflows[trace_id]
    
    if runner.status in ['pending', 'running']:
        return JSONResponse(content={"success": False, "trace_id": trace_id, "status": "not_completed"})

    result = runner.result
    
    # NEW: Add completion log
    if runner.status == "completed":
        add_workflow_log(trace_id, "✅ Workflow completed successfully", "success")
    else:
        add_workflow_log(trace_id, "❌ Workflow failed", "error")
    
    # Get logs before deleting
    logs = workflow_logs.get(trace_id, [])
    
    del running_workflows[trace_id]

    return JSONResponse(content={
        "success": True, 
        "trace_id": trace_id, 
        "result": result,
        "logs": logs
    })


# NEW: Get all workflow logs
@app.get("/workflow/all-logs")
async def get_all_workflow_logs(token: str = Depends(verify_token)):
    """Get logs for all workflows"""
    all_workflows = []
    
    for trace_id in workflow_logs.keys():
        runner = running_workflows.get(trace_id)
        
        workflow_data = {
            "trace_id": trace_id,
            "status": getattr(runner, 'status', 'completed') if runner else 'completed',
            "user_task": getattr(runner, 'user_task', 'Unknown') if runner else 'Unknown',
            "logs": workflow_logs[trace_id]
        }
        all_workflows.append(workflow_data)
    
    logger.info(f"📊 Returning logs for {len(all_workflows)} workflows")
    return JSONResponse(content={"success": True, "workflows": all_workflows})


# NEW: Get logs for specific workflow
@app.get("/workflow/logs/{trace_id}")
async def get_workflow_logs(trace_id: str, token: str = Depends(verify_token)):
    """Get logs for a specific workflow"""
    if trace_id not in workflow_logs:
        return JSONResponse(
            content={"success": False, "error": "Workflow not found"},
            status_code=404
        )
    
    runner = running_workflows.get(trace_id)
    
    return JSONResponse(content={
        "success": True,
        "trace_id": trace_id,
        "status": getattr(runner, 'status', 'completed') if runner else 'completed',
        "logs": workflow_logs[trace_id]
    })


@app.get("/health")
async def health_check():
    """Health check endpoint - no authentication required"""
    return JSONResponse(content={"status": "healthy", "service": "coral-factory-api"})


@app.get("/auth/status")
async def auth_status(token: str = Depends(verify_token)):
    """Check authentication status"""
    return JSONResponse(content={"authenticated": True, "message": "Valid token"})


@app.get("/auth/authorize/{user_id}/{tool_name}")
async def authorize(user_id: str, tool_name: str, token: str = Depends(verify_token)):
    """Authorize a tool for a user"""
    client = Arcade()
    auth_response = client.tools.authorize(tool_name=tool_name, user_id=user_id)
    if auth_response.status != "completed":
        return JSONResponse(content={"authenticated": False, "message": "Valid token", "url": auth_response.url})
    return JSONResponse(content={"authenticated": True, "message": "Valid token"})


@app.get("/auth/tools")
async def tools(token: str = Depends(verify_token)):
    """Authorize a tool for a user"""
    available_tools = [
        "X.LookupSingleUserByUsername",
        "X.PostTweet",
        "X.ReplyToTweet",
        "X.DeleteTweetById",
        "X.SearchRecentTweetsByUsername",
        "X.SearchRecentTweetsByKeywords",
        "X.LookupTweetById",
        "Linkedin.CreateTextPost",
        "GoogleFinance.GetStockSummary",
        "GoogleFinance.GetStockHistoricalData",
        "Gmail.SendEmail",
        "Gmail.SendDraftEmail",
        "Gmail.WriteDraftEmail",
        "Gmail.UpdateDraftEmail",
        "Gmail.DeleteDraftEmail",
        "Gmail.TrashEmail",
        "Gmail.ListDraftEmails",
        "Gmail.ListEmailsByHeader",
        "Gmail.ListEmails",
        "Gmail.SearchThreads",
        "Gmail.ListThreads",
        "Gmail.GetThread",
    ]
    return JSONResponse(content={"tools": available_tools})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)