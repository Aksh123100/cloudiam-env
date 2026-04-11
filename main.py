"""
FastAPI application for CloudIAMEnv
Exposes OpenEnv standard endpoints plus custom hackathon endpoints
"""
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import json

from env import CloudIAMEnv, ObservationSpace, ActionSpace
from tasks import get_tasks, get_task_by_id
from baseline import run_baseline_evaluation

# Initialize FastAPI app
app = FastAPI(
    title="CloudIAMEnv - Cloud Security RL Environment",
    description="OpenEnv-compliant environment for training agents to fix AWS IAM policy vulnerabilities",
    version="1.0.0"
)

# Global environment instance
env_instance = None


# Request/Response Models
class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(None, description="Optional task ID to reset to")


class StepRequest(BaseModel):
    action: ActionSpace = Field(description="Action containing the fixed IAM policy")


class GraderRequest(BaseModel):
    task_id: str = Field(description="Task ID to grade against")
    action: ActionSpace = Field(description="Action containing the fixed policy")


class TaskInfo(BaseModel):
    task_id: str
    difficulty: str
    goal_description: str
    vulnerable_policy: Dict[str, Any]


class TasksResponse(BaseModel):
    tasks: List[TaskInfo]
    action_schema: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Initialize the environment on startup"""
    global env_instance
    tasks = get_tasks()
    env_instance = CloudIAMEnv(tasks)
    print("CloudIAMEnv initialized with", len(tasks), "tasks", file=sys.stderr)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "CloudIAMEnv",
        "description": "Cloud Security Configuration RL Environment",
        "version": "1.0.0",
        "endpoints": {
            "openenv_standard": ["/reset", "/step", "/state"],
            "hackathon_custom": ["/tasks", "/grader", "/baseline"],
            "info": ["/", "/health"]
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "environment": "CloudIAMEnv"}


# OpenEnv Standard Endpoints

@app.post("/reset", response_model=ObservationSpace)
async def reset(request: Optional[ResetRequest] = None):
    """
    Reset the environment to start a new episode.
    
    Args:
        request: Optional request containing task_id
        
    Returns:
        ObservationSpace: Initial observation
    """
    try:
        if request and request.task_id:
            observation = env_instance.reset(task_id=request.task_id)
        else:
            observation = env_instance.reset()
        return observation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@app.post("/step")
async def step(request: StepRequest):
    """
    Execute one step in the environment.
    
    Args:
        request: StepRequest containing the action
        
    Returns:
        Dictionary containing observation, reward, done, and info
    """
    try:
        observation, reward, done, info = env_instance.step(request.action)
        safe_reward = max(0.2, min(0.8, float(reward)))
        
        return {
            "observation": observation.model_dump(),
            "reward": safe_reward,
            "score": safe_reward,
            "done": done,
            "info": info
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step failed: {str(e)}")


@app.get("/state", response_model=ObservationSpace)
async def state():
    """
    Get the current state of the environment.
    
    Returns:
        ObservationSpace: Current observation
    """
    try:
        current_state = env_instance.state()
        return current_state
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")


# Hackathon Custom Endpoints

@app.get("/tasks", response_model=TasksResponse)
async def get_tasks_endpoint():
    """
    Get the list of all tasks and the action schema.
    
    Returns:
        TasksResponse: List of tasks and action schema
    """
    try:
        tasks = get_tasks()
        
        # Format tasks for response
        task_infos = []
        for task in tasks:
            task_info = TaskInfo(
                task_id=task["task_id"],
                difficulty=task["difficulty"],
                goal_description=task["goal_description"],
                vulnerable_policy=task["vulnerable_policy"]
            )
            task_infos.append(task_info)
        
        # Get action schema from Pydantic model
        action_schema = ActionSpace.model_json_schema()
        
        return TasksResponse(
            tasks=task_infos,
            action_schema=action_schema
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@app.post("/grader")
async def grader(request: GraderRequest):
    """
    Grade a single action against a specific task.
    
    Args:
        request: GraderRequest containing task_id and action
        
    Returns:
        Dictionary containing reward and feedback
    """
    try:
        # Get the task
        task = get_task_by_id(request.task_id)
        
        # Create a temporary environment instance for this task
        temp_env = CloudIAMEnv([task])
        temp_env.reset(task_id=request.task_id)
        
        # Grade the action
        _, reward, _, info = temp_env.step(request.action)
        
        # ALWAYS clamp reward to safe range (0.2, 0.8) - clearly away from 0 and 1
        safe_reward = max(0.2, min(0.8, float(reward)))
        
        return {
            "task_id": request.task_id,
            "score": safe_reward,
            "reward": safe_reward,
            "feedback": info["feedback"],
            "passed": info["passed"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grading failed: {str(e)}")


@app.post("/baseline")
async def baseline():
    """
    Run the baseline agent on all tasks and return scores.
    
    Returns:
        Dictionary containing baseline results for all tasks
    """
    try:
        results = run_baseline_evaluation()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline evaluation failed: {str(e)}")


# Additional utility endpoints

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    Get details of a specific task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task details
    """
    try:
        task = get_task_by_id(task_id)
        # Remove grader function for JSON serialization
        task_copy = task.copy()
        task_copy.pop("grader", None)
        return task_copy
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/observation-space")
async def get_observation_space():
    """Get the observation space schema"""
    return ObservationSpace.model_json_schema()


@app.get("/action-space")
async def get_action_space():
    """Get the action space schema"""
    return ActionSpace.model_json_schema()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
