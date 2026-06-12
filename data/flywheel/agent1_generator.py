import os
import sys
import json
import uuid
import time
import random
import argparse

# Ensure output directories exist
QUEUE_DIR = "/home/ethan/karl/data/flywheel/queue"
os.makedirs(QUEUE_DIR, exist_ok=True)

def generate_math_problem_3var():
    # Category: Math/Algebra Systems (3 Variables)
    # x: apple, y: banana, z: cherry
    x = random.randint(2, 12)
    y = random.randint(2, 12)
    z = random.randint(2, 12)
    while x == y or y == z or x == z:
        y = random.randint(2, 12)
        z = random.randint(2, 12)
        
    # Generate coefficients
    # Eq 1: a1*x + b1*y + c1*z = e1
    # Eq 2: a2*x + b2*y + c2*z = e2
    # Eq 3: a3*x + b3*y + c3*z = e3
    coeffs = [
        [2, 1, 3],
        [1, 3, 2],
        [3, 2, 1]
    ]
    # Add minor randomness but keep them linearly independent
    for i in range(3):
        coeffs[i] = [c + random.randint(0, 2) for c in coeffs[i]]
        
    e1 = coeffs[0][0]*x + coeffs[0][1]*y + coeffs[0][2]*z
    e2 = coeffs[1][0]*x + coeffs[1][1]*y + coeffs[1][2]*z
    e3 = coeffs[2][0]*x + coeffs[2][1]*y + coeffs[2][2]*z
    
    item1, item2, item3 = "apple", "banana", "cherry"
    
    statement = (
        f"Solve the following system of 3 linear equations to find the price of one {item1}, one {item2}, and one {item3}. Show your work step-by-step.\n"
        f"1) {coeffs[0][0]} {item1}s, {coeffs[0][1]} {item2}s, and {coeffs[0][2]} {item3}s cost a total of ${e1}.\n"
        f"2) {coeffs[1][0]} {item1}s, {coeffs[1][1]} {item2}s, and {coeffs[1][2]} {item3}s cost a total of ${e2}.\n"
        f"3) {coeffs[2][0]} {item1}s, {coeffs[2][1]} {item2}s, and {coeffs[2][2]} {item3}s cost a total of ${e3}.\n"
        f"State the final answer clearly in the format: price of {item1} = X, price of {item2} = Y, price of {item3} = Z."
    )
    
    ground_truth = f"price of {item1} = {x}, price of {item2} = {y}, price of {item3} = {z}"
    
    verification_script = f"""
def verify(response):
    import re
    resp_clean = response.replace(" ", "").lower()
    # Check if target values are present
    if str({x}) in resp_clean and str({y}) in resp_clean and str({z}) in resp_clean:
        return True
    return False
"""
    return {
        "id": str(uuid.uuid4()),
        "category": "arithmetic_3var",
        "problem_statement": statement,
        "ground_truth_answer": ground_truth,
        "verification_type": "exact_match",
        "verification_script": verification_script
    }

def generate_coding_problem_extended():
    challenges = [
        {
            "name": "is_balanced_parentheses",
            "desc": "Write a python function `solve(s: str) -> bool` that returns True if the input string `s` has balanced parentheses (including '()', '[]', and '{}'), and False otherwise.",
            "test_cases": [
                ("()", True), ("()[]{}", True), ("(]", False), ("([)]", False), ("{[]}", True), ("", True)
            ]
        },
        {
            "name": "matrix_transpose",
            "desc": "Write a python function `solve(matrix: list[list[int]]) -> list[list[int]]` that computes and returns the transpose of a 2D matrix (list of lists).",
            "test_cases": [
                ([[1, 2], [3, 4]], [[1, 3], [2, 4]]),
                ([[1, 2, 3], [4, 5, 6]], [[1, 4], [2, 5], [3, 6]]),
                ([[]], [[]])
            ]
        },
        {
            "name": "group_anagrams",
            "desc": "Write a python function `solve(strs: list[str]) -> list[list[str]]` that groups anagrams together. Two words are anagrams if they contain the same characters in different orders. The order of the groups and the words within the groups does not matter.",
            "test_cases": [
                (["eat", "tea", "tan", "ate", "nat", "bat"], [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]])
            ],
            "custom_checker": """
        # Custom checker for group anagrams
        try:
            res = fn(["eat", "tea", "tan", "ate", "nat", "bat"])
            res_sorted = sorted([sorted(group) for group in res])
            expected = sorted([sorted(group) for group in [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]]])
            return res_sorted == expected
        except Exception:
            return False
            """
        },
        {
            "name": "run_length_encoding",
            "desc": "Write a python function `solve(s: str) -> str` that performs basic run-length encoding. For example, `solve('aabcccccaaa')` should return `'a2b1c5a3'`. If the encoded string is not shorter than the original, return the original string.",
            "test_cases": [
                ("aabcccccaaa", "a2b1c5a3"),
                ("abcd", "abcd"),
                ("a", "a"),
                ("", "")
            ]
        }
    ]
    
    challenge = random.choice(challenges)
    statement = f"{challenge['desc']}\nReturn ONLY the python code for the function, enclosed in a python code block."
    
    # Custom test checking
    if "custom_checker" in challenge:
        verification_script = f"""
def verify(response):
    import re
    code_match = re.search(r"```python\\n([\\s\\S]*?)```", response)
    if not code_match:
        code_match = re.search(r"```\\n([\\s\\S]*?)```", response)
    if not code_match:
        code = response
    else:
        code = code_match.group(1)
        
    sandbox = {{}}
    try:
        exec(code, sandbox)
        if 'solve' not in sandbox:
            return False
        fn = sandbox['solve']
        {challenge['custom_checker']}
    except Exception as e:
        return False
"""
    else:
        test_cases_str = repr(challenge['test_cases'])
        verification_script = f"""
def verify(response):
    import re
    code_match = re.search(r"```python\\n([\\s\\S]*?)```", response)
    if not code_match:
        code_match = re.search(r"```\\n([\\s\\S]*?)```", response)
    if not code_match:
        code = response
    else:
        code = code_match.group(1)
        
    sandbox = {{}}
    try:
        exec(code, sandbox)
        if 'solve' not in sandbox:
            return False
        fn = sandbox['solve']
        test_cases = {test_cases_str}
        for inp, expected in test_cases:
            if fn(inp) != expected:
                return False
        return True
    except Exception as e:
        return False
"""
    
    return {
        "id": str(uuid.uuid4()),
        "category": "coding_extended",
        "problem_statement": statement,
        "ground_truth_answer": f"Function implementation of {challenge['name']}",
        "verification_type": "unit_test",
        "verification_script": verification_script
    }

def generate_symbolic_problem_extended():
    choices = ["matrix_det", "combinations"]
    choice = random.choice(choices)
    
    if choice == "matrix_det":
        a = random.randint(-5, 10)
        b = random.randint(-5, 10)
        c = random.randint(-5, 10)
        d = random.randint(-5, 10)
        det = a * d - b * c
        
        statement = (
            f"Calculate the determinant of the following 2x2 matrix:\n"
            f"| {a}   {b} |\n"
            f"| {c}   {d} |\n"
            f"Show your work and state the final determinant clearly as a single integer."
        )
        ground_truth = str(det)
        
        verification_script = f"""
def verify(response):
    import re
    numbers = re.findall(r"-?\\b\\d+\\b", response)
    if str({det}) in numbers:
        return True
    return False
"""
    else:
        n = random.randint(5, 12)
        r = random.randint(2, n - 1)
        import math
        combinations = math.comb(n, r)
        
        statement = (
            f"A student committee of {r} members is to be formed from a group of {n} eligible students. "
            f"In how many unique ways can this committee be chosen? Explain your logic "
            f"and state the final answer clearly as a single integer."
        )
        ground_truth = str(combinations)
        
        verification_script = f"""
def verify(response):
    import re
    numbers = re.findall(r"\\b\\d+\\b", response)
    if str({combinations}) in numbers:
        return True
    return False
"""

    return {
        "id": str(uuid.uuid4()),
        "category": "symbolic_reasoning_extended",
        "problem_statement": statement,
        "ground_truth_answer": ground_truth,
        "verification_type": "symbolic_match",
        "verification_script": verification_script
    }

def main():
    parser = argparse.ArgumentParser(description="Agent 1 (Problem Generator) for Karl Self-Improvement Flywheel")
    parser.add_argument("--limit", type=int, default=100, help="Max number of tasks to generate (when infinite mode is off)")
    parser.add_argument("--infinite", action="store_true", help="Run indefinitely in an infinite loop")
    parser.add_argument("--interval", type=float, default=1.0, help="Sleep interval in seconds between loops")
    parser.add_argument("--buffer", type=int, default=15, help="Maximum number of pending tasks in the queue before throttling")
    args = parser.parse_args()
    
    print(f"Starting Agent 1 (Problem Generator)...")
    print(f"Settings: infinite={args.infinite}, limit={args.limit}, interval={args.interval}s, buffer={args.buffer}")
    
    count = 0
    while True:
        # Check termination condition if infinite mode is off
        if not args.infinite and count >= args.limit:
            print(f"Reached generation limit ({args.limit}). Exiting.")
            break
            
        # Check queue size to prevent flooding
        try:
            queue_files = [f for f in os.listdir(QUEUE_DIR) if f.startswith("task_") and f.endswith(".json")]
        except Exception:
            queue_files = []
            
        if len(queue_files) >= args.buffer:
            # Queue is full, throttle generation and sleep
            time.sleep(2.0)
            continue
            
        # Pick category randomly
        category_choice = random.choice(["math", "coding", "symbolic"])
        if category_choice == "math":
            task = generate_math_problem_3var()
        elif category_choice == "coding":
            task = generate_coding_problem_extended()
        else:
            task = generate_symbolic_problem_extended()
            
        task_id = task["id"]
        temp_path = os.path.join(QUEUE_DIR, f"task_{task_id}.tmp")
        final_path = os.path.join(QUEUE_DIR, f"task_{task_id}.json")
        
        # Write file atomically
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(task, f, indent=2)
            os.rename(temp_path, final_path)
            print(f"Generated task: {task_id} (Category: {task['category']})")
            count += 1
        except Exception as e:
            print(f"Error writing task {task_id}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
