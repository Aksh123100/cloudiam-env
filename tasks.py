"""
Task definitions and grading logic for CloudIAMEnv
"""
import json
from typing import Dict, Any, Tuple


def grade_easy_task(fixed_policy: Dict, vulnerable_policy: Dict, checks: Dict) -> Tuple[float, str]:
    """
    Grade the Easy task: Restrict wildcard action to specific S3 action.
    
    Expected fix: Change "Action": "*" to "Action": "s3:GetObject"
    """
    # Check if policy has Statement
    if "Statement" not in fixed_policy:
        return 0.0, "Missing 'Statement' field in policy"
    
    statements = fixed_policy["Statement"]
    if not isinstance(statements, list) or len(statements) == 0:
        return 0.0, "Statement must be a non-empty list"
    
    statement = statements[0]
    
    # Check if Action exists
    if "Action" not in statement:
        return 0.3, "Missing 'Action' field in statement"
    
    action = statement["Action"]
    
    # Check if wildcard is still present (security goal not met)
    if action == "*":
        return 0.3, "Security goal not met: wildcard action still present"
    
    # Check if it's the correct specific action
    if action == "s3:GetObject" or (isinstance(action, list) and "s3:GetObject" in action):
        # Verify other required fields are preserved
        if "Effect" not in statement or statement["Effect"] != "Allow":
            return 0.7, "Legitimate access broken: Effect field missing or incorrect"
        
        if "Resource" not in statement:
            return 0.7, "Legitimate access broken: Resource field missing"
        
        return 1.0, "Perfect fix: Restricted to s3:GetObject while preserving access"
    
    # Action is restricted but not to the correct one
    if isinstance(action, str) and action.startswith("s3:"):
        return 0.8, "Good progress: Action restricted to S3, but not exactly s3:GetObject"
    
    return 0.5, "Action changed but not to the required s3:GetObject"


def grade_medium_task(fixed_policy: Dict, vulnerable_policy: Dict, checks: Dict) -> Tuple[float, str]:
    """
    Grade the Medium task: Add IP address condition to restrict access.
    
    Expected fix: Add "Condition" block with IpAddress restriction to 192.168.1.0/24
    """
    if "Statement" not in fixed_policy:
        return 0.0, "Missing 'Statement' field in policy"
    
    statements = fixed_policy["Statement"]
    if not isinstance(statements, list) or len(statements) == 0:
        return 0.0, "Statement must be a non-empty list"
    
    statement = statements[0]
    
    # Check basic fields are preserved
    if "Effect" not in statement or "Action" not in statement or "Resource" not in statement:
        return 0.3, "Basic policy structure incomplete (missing Effect/Action/Resource)"
    
    # Check if Condition block exists
    if "Condition" not in statement:
        return 0.3, "Security goal not met: Missing Condition block for IP restriction"
    
    condition = statement["Condition"]
    if not isinstance(condition, dict):
        return 0.4, "Condition must be a JSON object"
    
    # Check for IpAddress condition
    if "IpAddress" not in condition:
        return 0.5, "Condition exists but missing IpAddress restriction"
    
    ip_condition = condition["IpAddress"]
    if not isinstance(ip_condition, dict):
        return 0.6, "IpAddress condition must be a JSON object"
    
    # Check for aws:SourceIp key
    if "aws:SourceIp" not in ip_condition:
        return 0.7, "IpAddress condition missing aws:SourceIp key"
    
    source_ip = ip_condition["aws:SourceIp"]
    
    # Check if it's the correct IP range
    expected_ip = "192.168.1.0/24"
    if source_ip == expected_ip or (isinstance(source_ip, list) and expected_ip in source_ip):
        # Verify other fields are preserved
        if statement.get("Effect") != "Allow":
            return 0.8, "Nearly perfect: IP restriction added but Effect modified incorrectly"
        
        return 1.0, "Perfect fix: IP restriction to 192.168.1.0/24 added with all fields preserved"
    
    # Some IP restriction added but not correct
    if isinstance(source_ip, str):
        return 0.8, f"IP restriction added but incorrect: {source_ip} instead of {expected_ip}"
    
    return 0.7, "Condition structure correct but IP range incorrect"


def grade_hard_task(fixed_policy: Dict, vulnerable_policy: Dict, checks: Dict) -> Tuple[float, str]:
    """
    Grade the Hard task: Fix conflicting Allow/Deny rules for DynamoDB access.
    
    Expected fix:
    - Allow DynamoDB read operations (GetItem, Query, Scan)
    - Explicitly deny DynamoDB delete operations (DeleteItem)
    """
    if "Statement" not in fixed_policy:
        return 0.0, "Missing 'Statement' field in policy"
    
    statements = fixed_policy["Statement"]
    if not isinstance(statements, list) or len(statements) == 0:
        return 0.0, "Statement must be a non-empty list"
    
    # We need at least 2 statements: one Allow, one Deny
    if len(statements) < 2:
        return 0.3, "Policy needs separate Allow and Deny statements to resolve conflict"
    
    allow_statement = None
    deny_statement = None
    
    for stmt in statements:
        if stmt.get("Effect") == "Allow":
            allow_statement = stmt
        elif stmt.get("Effect") == "Deny":
            deny_statement = stmt
    
    if not allow_statement:
        return 0.4, "Missing Allow statement for DynamoDB read operations"
    
    if not deny_statement:
        return 0.5, "Missing explicit Deny statement for DynamoDB delete operations"
    
    # Check Allow statement
    allow_actions = allow_statement.get("Action", [])
    if isinstance(allow_actions, str):
        allow_actions = [allow_actions]
    
    # Check if read actions are allowed
    required_read_actions = {"dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"}
    allowed_read = set()
    
    for action in allow_actions:
        if action in required_read_actions:
            allowed_read.add(action)
        elif action == "dynamodb:*":
            return 0.6, "Allow statement too permissive: uses dynamodb:* instead of specific read actions"
    
    if len(allowed_read) == 0:
        return 0.5, "Allow statement doesn't grant any DynamoDB read permissions"
    
    # Check Deny statement
    deny_actions = deny_statement.get("Action", [])
    if isinstance(deny_actions, str):
        deny_actions = [deny_actions]
    
    # Check if delete is denied
    has_delete_deny = False
    for action in deny_actions:
        if action == "dynamodb:DeleteItem" or action == "dynamodb:*":
            has_delete_deny = True
            break
    
    if not has_delete_deny:
        return 0.7, "Deny statement doesn't explicitly block DeleteItem"
    
    # Check Resource fields are present
    if "Resource" not in allow_statement or "Resource" not in deny_statement:
        return 0.8, "Resource fields missing from one or more statements"
    
    # Perfect score if all criteria met
    if len(allowed_read) >= 2:  # At least 2 read operations
        return 1.0, "Perfect fix: Allows DynamoDB reads and explicitly denies deletes"
    else:
        return 0.9, "Good fix but could include more read operations (GetItem, Query, Scan)"


# Task definitions
TASKS = [
    {
        "task_id": "easy_wildcard_action",
        "difficulty": "easy",
        "goal_description": "The policy currently allows all actions using a wildcard '*'. Restrict it to only allow 's3:GetObject' action while preserving all other fields.",
        "vulnerable_policy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "*",
                    "Resource": "arn:aws:s3:::my-bucket/*"
                }
            ]
        },
        "expected_checks": {
            "action": "s3:GetObject"
        },
        "grader": grade_easy_task
    },
    {
        "task_id": "medium_public_bucket",
        "difficulty": "medium",
        "goal_description": "This S3 bucket policy allows public access. Add a 'Condition' block to restrict access to only IP addresses from the range '192.168.1.0/24'. Use the 'IpAddress' condition with 'aws:SourceIp'.",
        "vulnerable_policy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::public-bucket/*",
                    "Principal": "*"
                }
            ]
        },
        "expected_checks": {
            "condition": "IpAddress",
            "ip_range": "192.168.1.0/24"
        },
        "grader": grade_medium_task
    },
    {
        "task_id": "hard_conflicting_rules",
        "difficulty": "hard",
        "goal_description": "This cross-account role has conflicting Allow/Deny rules. Fix the policy to: (1) Allow DynamoDB read operations (GetItem, Query, Scan), and (2) Explicitly deny DynamoDB delete operations (DeleteItem). Use separate statements for Allow and Deny.",
        "vulnerable_policy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "dynamodb:*",
                    "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
                },
                {
                    "Effect": "Deny",
                    "Action": "dynamodb:GetItem",
                    "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
                }
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
    """Return all task definitions"""
    return TASKS


def get_task_by_id(task_id: str) -> Dict:
    """Get a specific task by ID"""
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise ValueError(f"Task ID {task_id} not found")
