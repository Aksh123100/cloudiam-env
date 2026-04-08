"""
CloudIAMEnv: OpenEnv-compliant RL environment for AWS IAM Policy Security
"""
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ObservationSpace(BaseModel):
    """Pydantic model for observation space"""
    task_id: str = Field(description="Unique identifier for the task")
    goal_description: str = Field(description="Natural language description of the security goal")
    vulnerable_policy: str = Field(description="JSON string of the vulnerable IAM policy")


class ActionSpace(BaseModel):
    """Pydantic model for action space"""
    fixed_policy: str = Field(description="JSON string of the corrected IAM policy")


class CloudIAMEnv:
    """
    Cloud Security Configuration environment where an agent must fix vulnerable IAM policies.
    """
    
    def __init__(self, tasks: list):
        """
        Initialize the environment with a list of tasks.
        
        Args:
            tasks: List of task dictionaries containing task specifications
        """
        self.tasks = tasks
        self.current_task = None
        self.current_task_idx = 0
        self._state = None
        
    def reset(self, task_id: Optional[str] = None) -> ObservationSpace:
        """
        Reset the environment to a new task.
        
        Args:
            task_id: Optional task ID to reset to. If None, cycles through tasks.
            
        Returns:
            ObservationSpace: Initial observation
        """
        if task_id:
            # Find task by ID
            task = next((t for t in self.tasks if t["task_id"] == task_id), None)
            if not task:
                raise ValueError(f"Task ID {task_id} not found")
            self.current_task = task
        else:
            # Cycle through tasks
            self.current_task = self.tasks[self.current_task_idx % len(self.tasks)]
            self.current_task_idx += 1
        
        # Create observation
        observation = ObservationSpace(
            task_id=self.current_task["task_id"],
            goal_description=self.current_task["goal_description"],
            vulnerable_policy=json.dumps(self.current_task["vulnerable_policy"], indent=2)
        )
        
        self._state = observation
        return observation
    
    def step(self, action: ActionSpace) -> tuple[ObservationSpace, float, bool, Dict[str, Any]]:
        """
        Execute one step in the environment.
        
        Args:
            action: ActionSpace containing the fixed policy
            
        Returns:
            tuple: (observation, reward, done, info)
        """
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        
        # Grade the action
        reward, info = self._grade_action(action)
        
        # Episode ends after one step (single-shot policy fixing)
        done = True
        
        return self._state, reward, done, info
    
    def state(self) -> ObservationSpace:
        """
        Get the current state of the environment.
        
        Returns:
            ObservationSpace: Current observation
        """
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        return self._state
    
    def _grade_action(self, action: ActionSpace) -> tuple[float, Dict[str, Any]]:
        """
        Grade the agent's action based on the task requirements.
        
        Args:
            action: ActionSpace containing the fixed policy
            
        Returns:
            tuple: (reward, info_dict)
        """
        info = {
            "task_id": self.current_task["task_id"],
            "difficulty": self.current_task["difficulty"],
            "feedback": "",
            "passed": False
        }
        
        # Try to parse the fixed policy
        try:
            fixed_policy = json.loads(action.fixed_policy)
        except json.JSONDecodeError as e:
            info["feedback"] = f"Invalid JSON: {str(e)}"
            return 0.1, info
        
        # Validate basic structure
        if not isinstance(fixed_policy, dict):
            info["feedback"] = "Policy must be a JSON object"
            return 0.1, info
        
        # Call task-specific grader
        task_grader = self.current_task.get("grader")
        if not task_grader:
            info["feedback"] = "No grader defined for this task"
            return 0.1, info
        
        try:
            reward, feedback = task_grader(
                fixed_policy,
                self.current_task["vulnerable_policy"],
                self.current_task.get("expected_checks", {})
            )
            info["feedback"] = feedback
            info["passed"] = reward >= 0.85  # Consider >=0.85 as passed
            return reward, info
        except Exception as e:
            info["feedback"] = f"Grader error: {str(e)}"
            return 0.1, info
