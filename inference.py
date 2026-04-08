"""
OpenEnv Hackathon Inference Script for CloudIAMEnv
===================================================

CRITICAL: This script follows the MANDATORY structured logging format
required by the hackathon evaluation system. Any deviation in [START], 
[STEP], or [END] format will result in incorrect scoring.

Usage:
    python inference.py

Environment Variables (REQUIRED):
    API_BASE_URL   - The API endpoint for the LLM
    MODEL_NAME     - The model identifier (e.g., gpt-4o-mini)
    OPENAI_API_KEY or HF_TOKEN - Your API key
"""

import os
import json
import time
import sys
from typing import Dict, Any, Optional, List

from openai import OpenAI

# Import environment components
from env import CloudIAMEnv, ActionSpace, ObservationSpace
from tasks import get_tasks

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")

# Inference parameters
TEMPERATURE = 0.2  # Low temperature for deterministic outputs
MAX_TOKENS = 2048  # Enough for IAM policy JSON
MAX_RETRIES = 3    # Retry on parse failures
TIMEOUT = 60       # Seconds per API call

# Hackathon constants
BENCHMARK = "CloudIAMEnv"
MAX_STEPS = 1  # Each task is single-step

# ============================================================================
# MANDATORY STRUCTURED LOGGING FUNCTIONS
# ============================================================================

def log_start(task: str, env: str, model: str) -> None:
    """
    REQUIRED: Log the start of an episode.
    Format must match exactly or evaluation will fail.
    """
    output = {
        "type": "start",
        "task": task,
        "environment": env,
        "model": model,
        "timestamp": time.time()
    }
    print(f"[START] {json.dumps(output)}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    """
    REQUIRED: Log each step taken.
    Format must match exactly or evaluation will fail.
    """
    output = {
        "type": "step",
        "step": step,
        "action": action[:500],  # Truncate long actions
        "reward": reward,
        "done": done
    }
    if error:
        output["error"] = error
    print(f"[STEP] {json.dumps(output)}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """
    REQUIRED: Log the end of an episode.
    Format must match exactly or evaluation will fail.
    """
    output = {
        "type": "end",
        "success": success,
        "steps": steps,
        "score": score,
        "total_reward": sum(rewards),
        "rewards": rewards
    }
    print(f"[END] {json.dumps(output)}", flush=True)

# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are an expert AWS DevSecOps engineer specializing in IAM policy security.

Your task is to fix vulnerable AWS IAM policies based on the given security goal.

RULES:
1. Output ONLY valid JSON - no explanations, no markdown, no code blocks
2. Preserve all existing fields unless they need to be changed for security
3. Keep the same structure (Version, Statement array, etc.)
4. Make minimal changes to achieve the security goal
5. Never break legitimate access while fixing security issues

OUTPUT FORMAT:
Return a single JSON object with the fixed IAM policy. Example:
{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::bucket/*"}]}

DO NOT include any text before or after the JSON. Just the raw JSON object."""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_client() -> OpenAI:
    """Create OpenAI client with configured settings."""
    if not OPENAI_API_KEY:
        raise ValueError(
            "No API key found. Set OPENAI_API_KEY or HF_TOKEN environment variable."
        )
    
    return OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=API_BASE_URL,
        timeout=TIMEOUT
    )


def build_user_prompt(observation: ObservationSpace) -> str:
    """Build the user prompt from the observation."""
    return f"""TASK: {observation.task_id}

SECURITY GOAL:
{observation.goal_description}

VULNERABLE IAM POLICY:
{observation.vulnerable_policy}

Fix this policy to meet the security goal. Output ONLY the corrected JSON policy, nothing else."""


def parse_llm_response(response_text: str) -> Optional[str]:
    """
    Parse the LLM response and extract valid JSON.
    Handles common formatting issues.
    """
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    # Try to find JSON object boundaries
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1
    
    if start_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx]
    
    # Validate it's parseable JSON
    try:
        parsed = json.loads(text)
        # Re-serialize to ensure consistent formatting
        return json.dumps(parsed)
    except json.JSONDecodeError:
        return None


def call_llm(client: OpenAI, observation: ObservationSpace) -> str:
    """
    Call the LLM to generate a fixed policy.
    
    Returns:
        JSON string of the fixed policy, or fallback on failure
    """
    user_prompt = build_user_prompt(observation)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    for attempt in range(MAX_RETRIES):
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False
            )
            
            response_text = completion.choices[0].message.content or ""
            
            # Parse the response
            fixed_policy = parse_llm_response(response_text)
            
            if fixed_policy:
                return fixed_policy
            
            print(f"[DEBUG] Attempt {attempt + 1}: Failed to parse JSON, retrying...", file=sys.stderr)
            
            # Add a hint for the next attempt
            messages.append({"role": "assistant", "content": response_text})
            messages.append({
                "role": "user", 
                "content": "That response was not valid JSON. Please output ONLY the JSON object, no explanations."
            })
            
        except Exception as e:
            print(f"[DEBUG] Attempt {attempt + 1}: API error - {e}", file=sys.stderr)
            time.sleep(2)  # Brief pause before retry
    
    # Fallback: return the original policy (will get score 0.3 - valid JSON but unchanged)
    print("[DEBUG] All attempts failed, using fallback", file=sys.stderr)
    return observation.vulnerable_policy


def run_episode(
    env: CloudIAMEnv, 
    client: OpenAI, 
    task_id: str
) -> Dict[str, Any]:
    """
    Run a single episode for one task with MANDATORY structured logging.
    
    Returns:
        Dictionary with task results
    """
    # Log episode start (REQUIRED)
    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)
    
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    error_msg: Optional[str] = None
    
    try:
        # Reset to the specific task
        observation = env.reset(task_id=task_id)
        
        print(f"[DEBUG] Starting task: {task_id}", file=sys.stderr)
        print(f"[DEBUG] Goal: {observation.goal_description[:100]}...", file=sys.stderr)
        
        # Call LLM to generate fix
        start_time = time.time()
        fixed_policy_json = call_llm(client, observation)
        inference_time = time.time() - start_time
        
        # Create action and step
        action = ActionSpace(fixed_policy=fixed_policy_json)
        _, reward, done, info = env.step(action)
        
        steps_taken = 1
        rewards.append(reward)
        score = reward
        success = info['passed']
        
        # Log step (REQUIRED)
        log_step(
            step=1,
            action=fixed_policy_json,
            reward=reward,
            done=done,
            error=error_msg
        )
        
        # Debug output to stderr (won't interfere with structured logs)
        print(f"[DEBUG] Reward: {reward:.2f}", file=sys.stderr)
        print(f"[DEBUG] Passed: {'✓' if info['passed'] else '✗'}", file=sys.stderr)
        print(f"[DEBUG] Feedback: {info['feedback']}", file=sys.stderr)
        print(f"[DEBUG] Inference time: {inference_time:.2f}s", file=sys.stderr)
        
        result = {
            "task_id": task_id,
            "difficulty": info["difficulty"],
            "reward": reward,
            "passed": info["passed"],
            "feedback": info["feedback"],
            "inference_time": inference_time,
            "action": fixed_policy_json[:200] + "..." if len(fixed_policy_json) > 200 else fixed_policy_json
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[DEBUG] Episode error: {e}", file=sys.stderr)
        result = {
            "task_id": task_id,
            "difficulty": "unknown",
            "reward": 0.1,  # Must be strictly between 0 and 1
            "passed": False,
            "feedback": f"Error: {error_msg}",
            "inference_time": 0.1,
            "action": ""
        }
    
    finally:
        # Log episode end (REQUIRED)
        log_end(
            success=success,
            steps=steps_taken,
            score=score,
            rewards=rewards
        )
    
    return result


# ============================================================================
# MAIN INFERENCE FUNCTION
# ============================================================================

def main():
    """
    Main inference function.
    Runs the LLM agent on all tasks with MANDATORY structured logging.
    """
    # Configuration info to stderr (doesn't interfere with structured logs)
    print("\n" + "="*70, file=sys.stderr)
    print("CloudIAMEnv - OpenEnv Hackathon Inference Script", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"\nConfiguration:", file=sys.stderr)
    print(f"  API Base URL: {API_BASE_URL}", file=sys.stderr)
    print(f"  Model: {MODEL_NAME}", file=sys.stderr)
    print(f"  API Key: {'***' + OPENAI_API_KEY[-4:] if OPENAI_API_KEY else 'NOT SET'}", file=sys.stderr)
    
    # Validate API key
    if not OPENAI_API_KEY:
        print("\n❌ ERROR: No API key found!", file=sys.stderr)
        print("Please set OPENAI_API_KEY or HF_TOKEN environment variable.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize
    print("\n[DEBUG] Initializing environment...", file=sys.stderr)
    tasks = get_tasks()
    env = CloudIAMEnv(tasks)
    client = create_client()
    
    print(f"[DEBUG] Found {len(tasks)} tasks", file=sys.stderr)
    
    # Run all tasks
    results = []
    total_start_time = time.time()
    
    for task in tasks:
        task_result = run_episode(env, client, task["task_id"])
        results.append(task_result)
    
    total_time = time.time() - total_start_time
    
    # Summary to stderr
    print("\n" + "="*70, file=sys.stderr)
    print("INFERENCE RESULTS SUMMARY", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    total_reward = 0.0
    tasks_passed = 0
    
    for result in results:
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"\n[{result['difficulty'].upper()}] {result['task_id']}", file=sys.stderr)
        print(f"  Score: {result['reward']:.2f} / 1.00  {status}", file=sys.stderr)
        print(f"  Time:  {result['inference_time']:.2f}s", file=sys.stderr)
        
        total_reward += result["reward"]
        if result["passed"]:
            tasks_passed += 1
    
    average_score = total_reward / len(results)
    
    print("\n" + "-"*70, file=sys.stderr)
    print(f"FINAL SCORE: {average_score:.2f} / 1.00", file=sys.stderr)
    print(f"Tasks Passed: {tasks_passed} / {len(results)}", file=sys.stderr)
    print(f"Total Time: {total_time:.2f}s", file=sys.stderr)
    print("-"*70, file=sys.stderr)
    
    # Output structured results to file (for manual inspection)
    structured_output = {
        "model": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "tasks": results,
        "summary": {
            "average_score": round(average_score, 4),
            "tasks_passed": tasks_passed,
            "total_tasks": len(results),
            "total_time_seconds": round(total_time, 2)
        }
    }
    
    # Write results to file
    with open("inference_results.json", "w") as f:
        json.dump(structured_output, f, indent=2)
    print("\n[DEBUG] ✓ Results saved to inference_results.json", file=sys.stderr)
    
    return structured_output


if __name__ == "__main__":
    main()
