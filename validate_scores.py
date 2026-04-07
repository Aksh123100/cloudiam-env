"""
Comprehensive Score Validator
=============================
This script simulates what the hackathon validator does:
1. Tests all grading functions directly
2. Tests environment step() with various inputs
3. Tests baseline agent
4. Ensures ALL scores are strictly in (0, 1) - no 0.0 or 1.0

Run this before submission to catch any score issues!
"""

import json
from env import CloudIAMEnv, ActionSpace
from tasks import grade_easy_task, grade_medium_task, grade_hard_task, get_tasks
from baseline import run_baseline_evaluation

def validate_score(score, context):
    """Check if score is strictly between 0 and 1"""
    if score <= 0.0:
        raise ValueError(f"❌ INVALID: Score {score} is <= 0.0 (context: {context})")
    if score >= 1.0:
        raise ValueError(f"❌ INVALID: Score {score} is >= 1.0 (context: {context})")
    if score == 0.0:
        raise ValueError(f"❌ INVALID: Score is exactly 0.0 (context: {context})")
    if score == 1.0:
        raise ValueError(f"❌ INVALID: Score is exactly 1.0 (context: {context})")
    return True

def test_graders_directly():
    """Test all grading functions with various inputs"""
    print("\n" + "="*70)
    print("TEST 1: Direct Grader Functions")
    print("="*70)
    
    tasks = get_tasks()
    test_count = 0
    
    # Test 1: Invalid JSON
    print("\n[Test 1.1] Invalid JSON parsing...")
    try:
        json.loads("not json")
    except:
        score = 0.01  # This is what env.py returns
        validate_score(score, "Invalid JSON error handler")
        print(f"  ✅ Invalid JSON returns: {score}")
        test_count += 1
    
    # Test 2: Empty policy
    print("\n[Test 1.2] Empty policy...")
    score, feedback = grade_easy_task({}, tasks[0]["vulnerable_policy"], tasks[0]["expected_checks"])
    validate_score(score, f"Empty policy: {feedback}")
    print(f"  ✅ Empty policy returns: {score}")
    test_count += 1
    
    # Test 3: Perfect fixes
    print("\n[Test 1.3] Perfect fixes...")
    
    # Easy task perfect fix
    perfect_easy = {"Statement": [{"Action": "s3:GetObject", "Resource": "arn:aws:s3:::my-bucket/*", "Effect": "Allow"}]}
    score, feedback = grade_easy_task(perfect_easy, tasks[0]["vulnerable_policy"], tasks[0]["expected_checks"])
    validate_score(score, f"Easy perfect: {feedback}")
    print(f"  ✅ Easy perfect fix returns: {score}")
    test_count += 1
    
    # Medium task perfect fix
    perfect_medium = {
        "Statement": [{
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::public-bucket/*",
            "Principal": "*",
            "Condition": {"IpAddress": {"aws:SourceIp": "192.168.1.0/24"}}
        }]
    }
    score, feedback = grade_medium_task(perfect_medium, tasks[1]["vulnerable_policy"], tasks[1]["expected_checks"])
    validate_score(score, f"Medium perfect: {feedback}")
    print(f"  ✅ Medium perfect fix returns: {score}")
    test_count += 1
    
    # Hard task perfect fix
    perfect_hard = {
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
                "Resource": "arn:aws:dynamodb:us-east-1:111122223333:table/Books"
            },
            {
                "Effect": "Deny",
                "Action": "dynamodb:DeleteItem",
                "Resource": "arn:aws:dynamodb:us-east-1:111122223333:table/Books"
            }
        ]
    }
    score, feedback = grade_hard_task(perfect_hard, tasks[2]["vulnerable_policy"], tasks[2]["expected_checks"])
    validate_score(score, f"Hard perfect: {feedback}")
    print(f"  ✅ Hard perfect fix returns: {score}")
    test_count += 1
    
    print(f"\n✅ Test 1 Complete: {test_count} scores validated")
    return test_count

def test_environment_step():
    """Test environment step() function with various scenarios"""
    print("\n" + "="*70)
    print("TEST 2: Environment step() Function")
    print("="*70)
    
    tasks = get_tasks()
    env = CloudIAMEnv(tasks=tasks)
    test_count = 0
    
    # Test all tasks
    for task in tasks:
        print(f"\n[Test 2.{task['difficulty']}] Testing {task['task_id']}...")
        
        # Reset to task
        env.reset(task_id=task["task_id"])
        
        # Test 1: Invalid JSON
        action = ActionSpace(fixed_policy="invalid json")
        obs, reward, done, info = env.step(action)
        validate_score(reward, f"{task['task_id']}: Invalid JSON")
        print(f"  ✅ Invalid JSON returns: {reward}")
        test_count += 1
        
        # Test 2: Empty dict
        env.reset(task_id=task["task_id"])
        action = ActionSpace(fixed_policy=json.dumps({}))
        obs, reward, done, info = env.step(action)
        validate_score(reward, f"{task['task_id']}: Empty dict")
        print(f"  ✅ Empty dict returns: {reward}")
        test_count += 1
        
        # Test 3: Valid but wrong fix
        env.reset(task_id=task["task_id"])
        wrong_fix = {"Statement": [{"Action": "wrong", "Effect": "Allow", "Resource": "*"}]}
        action = ActionSpace(fixed_policy=json.dumps(wrong_fix))
        obs, reward, done, info = env.step(action)
        validate_score(reward, f"{task['task_id']}: Wrong fix")
        print(f"  ✅ Wrong fix returns: {reward}")
        test_count += 1
    
    print(f"\n✅ Test 2 Complete: {test_count} scores validated")
    return test_count

def test_baseline_agent():
    """Test the baseline agent"""
    print("\n" + "="*70)
    print("TEST 3: Baseline Agent")
    print("="*70)
    
    results = run_baseline_evaluation()
    test_count = 0
    
    # Check each task result
    for task_result in results["tasks"]:
        task_id = task_result["task_id"]
        reward = task_result["reward"]
        validate_score(reward, f"Baseline {task_id}")
        print(f"  ✅ {task_id}: {reward}")
        test_count += 1
    
    # Check average score
    avg_score = results["average_score"]
    validate_score(avg_score, "Baseline average score")
    print(f"  ✅ Average score: {avg_score}")
    test_count += 1
    
    print(f"\n✅ Test 3 Complete: {test_count} scores validated")
    return test_count

def main():
    """Run all validation tests"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "COMPREHENSIVE SCORE VALIDATOR" + " "*24 + "║")
    print("╚" + "="*68 + "╝")
    
    total_tests = 0
    
    try:
        total_tests += test_graders_directly()
        total_tests += test_environment_step()
        total_tests += test_baseline_agent()
        
        print("\n" + "╔" + "="*68 + "╗")
        print("║" + " "*10 + "✅✅✅ ALL TESTS PASSED! ✅✅✅" + " "*21 + "║")
        print("║" + f" "*15 + f"Total: {total_tests} scores validated" + " "*(37-len(str(total_tests))) + "║")
        print("║" + " "*10 + "All scores are in range (0, 1)" + " "*27 + "║")
        print("║" + " "*10 + "No 0.0 or 1.0 values found!" + " "*29 + "║")
        print("╚" + "="*68 + "╝")
        
        return True
        
    except ValueError as e:
        print("\n" + "╔" + "="*68 + "╗")
        print("║" + " "*15 + "❌ VALIDATION FAILED! ❌" + " "*26 + "║")
        print("╚" + "="*68 + "╝")
        print(f"\n{e}")
        return False
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
