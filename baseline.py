"""
Baseline model for CloudIAMEnv
Simulates a simple rule-based agent that attempts to fix IAM policies
"""
import json
import re
import sys
from typing import Dict, Any
from env import CloudIAMEnv, ActionSpace
from tasks import get_tasks


class BaselineAgent:
    """
    Simple rule-based baseline agent for CloudIAMEnv.
    Uses pattern matching and simple transformations.
    """
    
    def __init__(self):
        self.name = "RuleBasedBaseline"
    
    def generate_action(self, observation: Dict[str, Any]) -> ActionSpace:
        """
        Generate an action based on simple rules.
        
        Args:
            observation: Dictionary containing task info and vulnerable policy
            
        Returns:
            ActionSpace: Action containing the fixed policy
        """
        task_id = observation["task_id"]
        vulnerable_policy_str = observation["vulnerable_policy"]
        
        try:
            vulnerable_policy = json.loads(vulnerable_policy_str)
        except json.JSONDecodeError:
            # Return empty policy if can't parse
            return ActionSpace(fixed_policy=json.dumps({"Statement": []}))
        
        # Apply task-specific rules
        if "easy" in task_id:
            fixed_policy = self._fix_easy_task(vulnerable_policy)
        elif "medium" in task_id:
            fixed_policy = self._fix_medium_task(vulnerable_policy)
        elif "hard" in task_id:
            fixed_policy = self._fix_hard_task(vulnerable_policy)
        else:
            fixed_policy = vulnerable_policy  # No fix
        
        return ActionSpace(fixed_policy=json.dumps(fixed_policy, indent=2))
    
    def _fix_easy_task(self, policy: Dict) -> Dict:
        """Fix wildcard action by replacing with s3:GetObject"""
        fixed = policy.copy()
        if "Statement" in fixed and len(fixed["Statement"]) > 0:
            statement = fixed["Statement"][0].copy()
            # Replace wildcard with specific action
            if statement.get("Action") == "*":
                statement["Action"] = "s3:GetObject"
            fixed["Statement"] = [statement]
        return fixed
    
    def _fix_medium_task(self, policy: Dict) -> Dict:
        """Add IP address condition"""
        fixed = policy.copy()
        if "Statement" in fixed and len(fixed["Statement"]) > 0:
            statement = fixed["Statement"][0].copy()
            # Add Condition block
            statement["Condition"] = {
                "IpAddress": {
                    "aws:SourceIp": "192.168.1.0/24"
                }
            }
            fixed["Statement"] = [statement]
        return fixed
    
    def _fix_hard_task(self, policy: Dict) -> Dict:
        """Fix conflicting rules by separating Allow and Deny"""
        fixed = {
            "Version": "2012-10-17",
            "Statement": []
        }
        
        # Get resource from original policy
        resource = "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
        if "Statement" in policy and len(policy["Statement"]) > 0:
            resource = policy["Statement"][0].get("Resource", resource)
        
        # Allow read operations
        allow_statement = {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": resource
        }
        
        # Deny delete operations
        deny_statement = {
            "Effect": "Deny",
            "Action": "dynamodb:DeleteItem",
            "Resource": resource
        }
        
        fixed["Statement"] = [allow_statement, deny_statement]
        return fixed


def run_baseline_evaluation() -> Dict[str, Any]:
    """
    Run the baseline agent on all tasks and return scores.
    
    Returns:
        Dictionary containing results for each task
    """
    tasks = get_tasks()
    env = CloudIAMEnv(tasks)
    agent = BaselineAgent()
    
    results = {
        "agent_name": agent.name,
        "tasks": []
    }
    
    total_score = 0.0
    
    for task in tasks:
        # Reset environment to this task
        obs = env.reset(task_id=task["task_id"])
        
        # Generate action using baseline agent
        action = agent.generate_action(obs.model_dump())
        
        # Take step in environment
        next_obs, reward, done, info = env.step(action)
        
        # ALWAYS clamp reward to safe range (0.05, 0.95) - strictly between 0 and 1
        safe_reward = max(0.05, min(0.95, float(reward)))
        
        task_result = {
            "task_id": task["task_id"],
            "difficulty": task["difficulty"],
            "reward": safe_reward,
            "passed": info["passed"],
            "feedback": info["feedback"]
        }
        
        results["tasks"].append(task_result)
        total_score += safe_reward
    
    # Calculate average score - ALWAYS clamp to safe range
    avg = total_score / len(tasks)
    safe_avg = max(0.05, min(0.95, float(avg)))
    results["average_score"] = safe_avg
    results["total_tasks"] = len(tasks)
    
    return results


if __name__ == "__main__":
    print("Running baseline evaluation...", file=sys.stderr)
    results = run_baseline_evaluation()
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Baseline Agent: {results['agent_name']}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    for task_result in results["tasks"]:
        print(f"Task: {task_result['task_id']}", file=sys.stderr)
        print(f"  Difficulty: {task_result['difficulty']}", file=sys.stderr)
        print(f"  Reward: {task_result['reward']:.2f}", file=sys.stderr)
        print(f"  Passed: {'✓' if task_result['passed'] else '✗'}", file=sys.stderr)
        print(f"  Feedback: {task_result['feedback']}", file=sys.stderr)
        print(file=sys.stderr)
    
    print(f"{'='*60}", file=sys.stderr)
    print(f"Average Score: {results['average_score']:.2f} / 1.0", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
