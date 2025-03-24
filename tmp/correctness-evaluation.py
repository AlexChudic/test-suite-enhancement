
import json
import subprocess
import re
import os
import ast
import compileall

def check_correctness(test_case_path):
    """Evaluates the correctness of a test case."""

    with open(test_case_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    # Check for syntax errors
    try :
        ast.parse(test_class_source_code)
    except SyntaxError:
        return "Syntax Error"
    
    # Check for compilation errors
    compiled = compileall.compile_file(test_case_path, force=True, quiet=1)
    if not compiled:
        return "Compilation Error"
    
    print("Running the test case...")
    result = subprocess.run(
        ["pytest", "--timeout=5", "--json-report", "--json-report-file=report.json", test_case_path]
    )

    if os.path.exists("report.json"):
        with open("report.json", "r") as file:
            report = json.load(file)
            
        passed = sum(1 for test in report.get("tests", []) if test["outcome"] == "passed")
        failed = sum(1 for test in report.get("tests", []) if test["outcome"] == "failed")
        errored = sum(1 for test in report.get("tests", []) if test["outcome"] == "error")
        return f"{passed} tests passed, {failed} tests failed, {errored} tests errored"

    else:
        print("[✘] Could not parse test results.")
        return None
        

def extract_function_name(cleaned_output):
        match = re.search(r"assert\s+(\w+)\s*\(", cleaned_output)
        return match.group(1) if match else None


def rule_based_repair(test_case_path):
    """Attempts to repair a test case using a rule-based approach."""

    with open(test_case_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    function_name = extract_function_name(test_class_source_code)
    module_name = os.path.basename(test_case_path).replace(".py", "").removeprefix("test_")
    module_import = f"from {module_name} import {function_name}"
    if module_import not in test_class_source_code:
        test_class_source_code = module_import + "\n" + test_class_source_code

    with open(test_case_path, "w", encoding="utf-8") as f:
        f.write(test_class_source_code)


def get_failing_tests(report_path):
    """Extracts the names of the failing tests from a pytest report."""
    
    with open(report_path, "r") as f:
        report = json.load(f)

    failed_tests = [
        test["nodeid"].split("::")[-1]  # Extract function name from nodeid
        for test in report.get("tests", [])
        if test.get("outcome") == "failed"
    ]

    return failed_tests


def remove_failing_tests(test_case_path, res):
    failing_tests = get_failing_tests("report.json")

    with open(test_case_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"Removing failing tests from the test case... {test_case_path}")
    print(f"Result: {res}")
    print(f"Failing tests: {failing_tests}")
    print(f"Original test case:")
    print(lines)

    new_lines = []
    skip = False
    inside_function = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if the line starts a failed function
        if any(f"def {fn}(" in line for fn in failing_tests):
            skip = True
            inside_function = True 
            continue 

        # If we're skipping, check if we reached the end of the function
        if skip:
            if not inside_function and not stripped.startswith("@"):  # Found a non-decorator, stop skipping
                skip = False
                continue

            if inside_function and not stripped:  # Empty line means function might be ending
                skip = False
                continue

            if inside_function and not line.startswith(" ") and not stripped.startswith("@"): # Function ended (non-indented, non-decorator line)
                skip = False
                continue

            continue

        # If not skipping, keep the line
        new_lines.append(line)

    # Write back cleaned file
    with open(test_case_path, "w") as f:
        f.writelines(new_lines)
    

def add_correction_evaluation_stats(stats, res):    
    stats["total_classes"] += 1
    if res == "Syntax Error":
        stats["syntax_errors"] += 1
        return False
    elif res == "Compilation Error":
        stats["compilation_errors"] += 1
        return False
    elif res == "Passed":
        stats["passed"] += 1
        return True
    else:
        parse_res = re.match(r"(\d+) tests passed, (\d+) tests failed, (\d+) tests errored", res)
        if parse_res:
            stats["passed_tests"] += int(parse_res.group(1))
            stats["failed_tests"] += int(parse_res.group(2))
            stats["error_tests"] += int(parse_res.group(3))
            stats["total_tests"] += int(parse_res.group(1)) + int(parse_res.group(2)) + int(parse_res.group(3))
            if int(parse_res.group(2)) == 0 and int(parse_res.group(3)) == 0:
                return True
            else:
                return False
        else:
            return False

            


def evaluate_functional_correctness(path):
    test_classes = [f for f in os.listdir(path) if f.endswith(".py")]
    stats_pre_repair = {
        "total_classes": 0,
        "total_tests": 0,
        "syntax_errors": 0,
        "passed": 0,
        "compilation_errors": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "error_tests": 0,
    }
    stats_post_repair = stats_pre_repair.copy()
    stats_post_removal = stats_pre_repair.copy()
    
    for test_class in test_classes:
        # Evaluate the test class correctness
        test_class_path = os.path.join(path, test_class)
        res = check_correctness(test_class_path)
        add_correction_evaluation_stats(stats_pre_repair, res)

        # Attempt to repair the test class if failed
        if res != "Passed":
            rule_based_repair(test_class_path)

            # Evaluate the test class correctness
            res = check_correctness(test_class_path)
            passed = add_correction_evaluation_stats(stats_post_repair, res)

            # Remove the tests that are still failing
            if not passed:
                remove_failing_tests(test_class_path, res)

                # Evaluate the test class correctness again
                res = check_correctness(test_class_path)
                add_correction_evaluation_stats(stats_post_removal, res)
                
    
    print("Functional Correctness Evaluation Results PRE:")
    print(json.dumps(stats_pre_repair, indent=4))

    print("Functional Correctness Evaluation Results POST REPAIR:")
    print(json.dumps(stats_post_repair, indent=4))

    print("Functional Correctness Evaluation Results POST REMOVAL:")
    print(json.dumps(stats_post_removal, indent=4))

if __name__ == "__main__":
    evaluate_functional_correctness("data/human-eval/tests/chatgpt/enhanced")