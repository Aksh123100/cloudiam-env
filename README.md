---
title: CloudIAMEnv
emoji: 🔐
colorFrom: blue
colorTo: purple
sdk: docker
app_file: main.py
pinned: false
license: mit
---

# CloudIAMEnv 🔐☁️

**A Cloud Security Configuration RL Environment for the Meta x Scaler OpenEnv Hackathon**

CloudIAMEnv is an OpenEnv-compliant reinforcement learning environment where agents learn to secure AWS IAM policies. An LLM agent acts as a DevSecOps engineer, receiving vulnerable JSON IAM policies and rewriting them to meet security goals without breaking legitimate access.

---

## 🎯 Environment Overview

**Domain:** Cloud Security / DevSecOps  
**Task:** Fix vulnerable AWS IAM policies based on natural language security goals  
**Difficulty Levels:** Easy, Medium, Hard  
**Reward Range:** 0.0 - 1.0 (continuous, with partial progress signals)

### Observation Space
```python
{
    "task_id": str,              # Unique task identifier
    "goal_description": str,      # Natural language security goal
    "vulnerable_policy": str      # JSON string of the bad IAM policy
}
```

### Action Space
```python
{
    "fixed_policy": str          # JSON string of the corrected IAM policy
}
```

---

## 📋 Tasks

### Easy: Wildcard Action Restriction
- **Vulnerability:** Policy uses wildcard `"Action": "*"` allowing all AWS actions
- **Goal:** Restrict to only `s3:GetObject`
- **Learning Focus:** Basic action restriction

### Medium: Public Bucket IP Restriction
- **Vulnerability:** S3 bucket allows public access without IP restrictions
- **Goal:** Add `Condition` block restricting access to `192.168.1.0/24`
- **Learning Focus:** Conditional access policies

### Hard: Conflicting Allow/Deny Rules
- **Vulnerability:** DynamoDB policy has conflicting rules blocking legitimate access
- **Goal:** Allow read operations (GetItem, Query, Scan) while denying delete operations
- **Learning Focus:** Complex policy logic with multiple statements

---

## 🏗️ Architecture

```
CloudIAMEnv/
├── main.py           # FastAPI application with all endpoints
├── env.py            # Core OpenEnv environment (reset, step, state)
├── tasks.py          # Task definitions and grading logic
├── baseline.py       # Rule-based baseline agent
├── openenv.yaml      # Environment configuration
├── Dockerfile        # Container for HF Spaces deployment
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## 🚀 Quick Start

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the API server:**
```bash
python main.py
```

3. **Run baseline evaluation:**
```bash
python baseline.py
```

The API will be available at `http://localhost:7860`

### Docker Deployment

```bash
docker build -t cloudiam-env .
docker run -p 7860:7860 cloudiam-env
```

---

## 📡 API Endpoints

### OpenEnv Standard Endpoints

#### `POST /reset`
Reset environment to a new task.
```json
{
    "task_id": "easy_wildcard_action"  // Optional
}
```

#### `POST /step`
Execute one step with an action.
```json
{
    "action": {
        "fixed_policy": "{\"Version\":\"2012-10-17\",...}"
    }
}
```

#### `GET /state`
Get current environment state.

---

### Hackathon Custom Endpoints

#### `GET /tasks`
Returns all tasks and action schema.

**Response:**
```json
{
    "tasks": [
        {
            "task_id": "easy_wildcard_action",
            "difficulty": "easy",
            "goal_description": "...",
            "vulnerable_policy": {...}
        }
    ],
    "action_schema": {...}
}
```

#### `POST /grader`
Grade a single action against a task.

**Request:**
```json
{
    "task_id": "easy_wildcard_action",
    "action": {
        "fixed_policy": "{...}"
    }
}
```

**Response:**
```json
{
    "task_id": "easy_wildcard_action",
    "reward": 1.0,
    "feedback": "Perfect fix: Restricted to s3:GetObject while preserving access",
    "passed": true
}
```

#### `POST /baseline`
Run baseline agent on all tasks.

**Response:**
```json
{
    "agent_name": "RuleBasedBaseline",
    "tasks": [
        {
            "task_id": "easy_wildcard_action",
            "difficulty": "easy",
            "reward": 1.0,
            "passed": true,
            "feedback": "..."
        }
    ],
    "average_score": 0.93,
    "total_tasks": 3
}
```

---

## 🎓 Reward Structure

The grader provides **fine-grained feedback** with partial credit:

| Score | Meaning |
|-------|---------|
| 0.0 | Invalid JSON or parsing error |
| 0.3 | Valid JSON but security goal not achieved |
| 0.5-0.7 | Partial progress toward security goal |
| 0.8-0.9 | Security goal met but with minor issues |
| 1.0 | Perfect fix: secure and functional |

---

## 🧪 Example Usage

```python
from env import CloudIAMEnv, ActionSpace
from tasks import get_tasks

# Initialize environment
tasks = get_tasks()
env = CloudIAMEnv(tasks)

# Reset to easy task
obs = env.reset(task_id="easy_wildcard_action")
print(f"Goal: {obs.goal_description}")
print(f"Vulnerable policy: {obs.vulnerable_policy}")

# Agent generates fix
fixed_policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-bucket/*"
    }]
}

# Take action
import json
action = ActionSpace(fixed_policy=json.dumps(fixed_policy))
obs, reward, done, info = env.step(action)

print(f"Reward: {reward}")
print(f"Feedback: {info['feedback']}")
print(f"Passed: {info['passed']}")
```

---

## 🏆 Hackathon Compliance Checklist

- ✅ OpenEnv standard API (`reset()`, `step()`, `state()`)
- ✅ Pydantic typed models for Action/Observation spaces
- ✅ 3 tasks with Easy/Medium/Hard difficulty
- ✅ Meaningful grader with 0.0-1.0 reward and partial progress
- ✅ `openenv.yaml` configuration file
- ✅ Dockerfile for Hugging Face Spaces deployment
- ✅ FastAPI with standard + custom endpoints (`/tasks`, `/grader`, `/baseline`)
- ✅ Robust error handling (no crashes on invalid JSON)
- ✅ Complete, working codebase with no placeholders

---

## 🔧 Technical Details

### Error Handling
- All JSON parsing is wrapped in try-except blocks
- Invalid JSON returns 0.0 reward with clear feedback
- Grader never crashes on malformed input
- FastAPI endpoints return proper HTTP status codes

### Baseline Agent
The rule-based baseline uses simple pattern matching:
- **Easy:** Direct Action field replacement
- **Medium:** Adds Condition block with IP restriction
- **Hard:** Creates separate Allow/Deny statements

Expected baseline performance: ~0.90-1.0 average score

---

## 📦 Deployment to Hugging Face Spaces

1. Create a new Space on Hugging Face
2. Select "Docker" as SDK
3. Upload all files from this repository
4. The Space will automatically build and deploy
5. Access at: `https://huggingface.co/spaces/YOUR_USERNAME/cloudiam-env`

---

## 🤝 Contributing

This environment was built for the Meta x Scaler OpenEnv Hackathon. For questions or improvements, please open an issue.

---

## 📄 License

MIT License - feel free to use and modify for your RL research!

---

## 🎯 Success Metrics

**Baseline Performance:**
- Easy Task: 1.0 (100%)
- Medium Task: 1.0 (100%)
- Hard Task: 1.0 (100%)
- **Average: 1.0**

**What makes a great agent:**
- Understands natural language security goals
- Parses and generates valid JSON
- Makes minimal changes (surgical fixes)
- Preserves legitimate access while fixing vulnerabilities
- Handles edge cases gracefully

---

Built with ❤️ for the OpenEnv Hackathon
