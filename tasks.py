"""
Task definitions and grading logic for CloudIAMEnv
"""
import json
from typing import Dict, Any, Tuple


def grade_easy_task(fixed_policy: Dict, vulnerable_policy: Dict, checks: Dict) -> Tuple[float, str]:
    if "Statement" not in fixed_policy:
        return 0.3, "Missing 'Statement' field in policy"
    
    statements = fixed_policy["Statement"]
    if not isinstance(statements, list) or len(statements) == 0:
        return 0.3, "Statement must be a non-empty list"
    
    statement = statements[0]
    
    if "Action" not in statement:
        return 0.3, "Missing 'Action' field in statement"
    
    action = statement["Action"]
    
    if action == "*":
        return 0.3, "Security goal not met: wildcard action still present"
    
    if action == "s3:GetObject" or (isinstance(action, list) and "s3:GetObject" in action):
        if "Effect" not in statement or statement["Effect"] != "Allow":
            return 0.5, "Legitimate access broken: Effect field missing or incorrect"
        if "Resource" not in statement:
            return 0.5, "Legitimate access broken: Resource field missing"
        return 0.7, "Perfect fix: Restricted to s3:GetObject while preserving access"
    
    if isinstance(action, str) and action.startswith("s3:"):
        return 0.5, "Good progress: Action restricted to S3, but not exactly s3:GetObject"
    
    return 0.3, "Action changed but not to the required s3:GetObject"


def grade_medium_task(fixed_policy: Dict, vulnerable_policy: Dict, checks: Dict) -> Tuple[float, str]:
    if "Statement" not in fixed_policy:
        return 0.3, "Missing 'Statement' field in policy"
    
    statements = fixed_policy["Statement"]
    if not isinstance(statements, list) or len(statements) == 0:
        return 0.3, "Statement must be a non-empty list"
    
    statement = statements[0]
    
    if "Effect" not in statement or "Action" not in statement or "Resource" not in statement:
        return 0.3, "Basic policy structure incomplete"
    
    if "Condition" not in statement:
        return 0.3, "Security goal not met: Missing Condition block for IP restriction"
    
    condition = statement["Condition"]
    if not isinstance(condition, dict):
        return 0.3, "Condition must be a JSON object"
    
    if "IpAddress" not in condition:
        return 0.5, "Condition exists but missing IpAddress restriction"
    
    ip_condition = condition["IpAddress"]
    if not isinstance(ip_condition, dict):
        return 0.5, "IpAddress condition must be a JSON object"
    
    if "aws:SourceIp" not in ip_condition:
        return 0.5, "IpAddress condition missing aws:SourceIp key"
    
    source_ip = ip_condition["aws:SourceIp"]
    expected_ip = "192.168.1.0/24"
    
    if source_ip == expected_ip or (isinstance(source_ip, list) and expected_ip in source_ip):
        return 0.7, "Perfect fix: IP restriction to 192.168.1.0/24 added correctly"
    
    return 0.5, "IP restriction added but incorrect range"


def grade_hard_task(fixed_policy: Dict, vulnerable_policy: Dict, checks: Dict) -> Tuple[float, str]:
    if "Statement" not in fixed_policy:
        return 0.3, "Missing 'Statement' field in policy"
    
    statements = fixed_policy["Statement"]
    if not isinstance(statements, list) or len(statements) == 0:
        return 0.3, "Statement must be a non-empty list"
    
    if len(statements) < 2:
        return 0.3, "Policy needs separate Allow and Deny statements"
    
    allow_statement = None
    deny_statement = None
    
    for stmt in statements:
        if stmt.get("Effect") == "Allow":
            allow_statement = stmt
        elif stmt.get("Effect") == "Deny":
            deny_statement = stmt
    
    if not allow_statement:
        return 0.3, "Missing Allow statement for DynamoDB read operations"
    
    if not deny_statement:
        return 0.5, "Missing explicit Deny statement for DynamoDB delete operations"
    
    allow_actions = allow_statement.get("Action", [])
    if isinstance(allow_actions, str):
        allow_actions = [allow_actions]
    
    required_read_actions = {"dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"}
    allowed_read = set(a for a in allow_actions if a in required_read_actions)
    
    if len(allowed_read) == 0:
        return 0.5, "Allow statement doesn't grant any DynamoDB read permissions"
    
    deny_actions = deny_statement.get("Action", [])
    if isinstance(deny_actions, str):
        deny_actions = [deny_actions]
    
    has_delete_deny = any(a in ("dynamodb:DeleteItem", "dynamodb:*") for a in deny_actions)
    
    if not has_delete_deny:
        return 0.5, "Deny statement doesn't explicitly block DeleteItem"
    
    return 0.7, "Perfect fix: Allows DynamoDB reads and explicitly denies deletes"


TASKS = [
    {
        "task_id": "easy_wildcard_action",
        "difficulty": "easy",
        "goal_description": "The policy currently allows all actions using a wildcard '*'. Restrict it to only allow 's3:GetObject' action while preserving all other fields.",
        "vulnerable_policy": {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "arn:aws:s3:::my-bucket/*"}]
        },
        "expected_checks": {"action": "s3:GetObject"},
        "grader": grade_easy_task
    },
    {
        "task_id": "medium_public_bucket",
        "difficulty": "medium",
        "goal_description": "This S3 bucket policy allows public access. Add a 'Condition' block to restrict access to only IP addresses from the range '192.168.1.0/24'. Use the 'IpAddress' condition with 'aws:SourceIp'.",
        "vulnerable_policy": {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::public-bucket/*", "Principal": "*"}]
        },
        "expected_checks": {"condition": "IpAddress", "ip_range": "192.168.1.0/24"},
        "grader": grade_medium_task
    },
    {
        "task_id": "hard_conflicting_rules",
        "difficulty": "hard",
        "goal_description": "This cross-account role has conflicting Allow/Deny rules. Fix the policy to: (1) Allow DynamoDB read operations (GetItem, Query, Scan), and (2) Explicitly deny DynamoDB delete operations (DeleteItem). Use separate statements for Allow and Deny.",
        "vulnerable_policy": {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": "dynamodb:*", "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"},
                {"Effect": "Deny", "Action": "dynamodb:GetItem", "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"}
            ]
        },
        "expected_checks": {
            "allow_actions": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
            "deny_actions": ["dynamodb:DeleteItem"]
        },
        "grader": grade_hard_task
    }
]


def get_tasks() -> list:
    return TASKS


def get_task_by_id(task_id: str) -> Dict:
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise ValueError(f"Task ID {task_id} not found")
