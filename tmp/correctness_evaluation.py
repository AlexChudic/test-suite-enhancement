
import json
import subprocess
import re
import os
import ast
import compileall
import importlib.util
from pathlib import Path

def check_correctness(test_case_path):
    """Evaluates the correctness of a test case."""

    with open(test_case_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    # Check for syntax errors
    try :
        ast.parse(test_class_source_code)
    except SyntaxError as se:
        return ("Syntax Error", se)
    
    # Check for compilation errors
    compiled = compileall.compile_file(test_case_path, force=True, quiet=1)
    if not compiled:
        return ("Compilation Error", None)
    
    # Run the test case with pytest
    result = subprocess.run(
        ["pytest", "--timeout=5", "--json-report", "--json-report-file=report.json", test_case_path]
    )

    if os.path.exists("report.json"):
        with open("report.json", "r") as file:
            report = json.load(file)
        
        if report.get("tests", []) != []:
            passed = sum(1 for test in report.get("tests", []) if test["outcome"] == "passed")
            failed = sum(1 for test in report.get("tests", []) if test["outcome"] == "failed")
            errored = sum(1 for test in report.get("tests", []) if test["outcome"] == "error")
            return (f"{passed} tests passed, {failed} tests failed, {errored} tests errored", None)
        else:
            msg = [it["longrepr"] for it in report.get("collectors") if it["outcome"] == "failed"]
            if msg:
                msg = "\n".join(msg)
                return ("Compilation Error", msg)
            else:
                print("No tests found in the report. " + test_case_path)
                return ("No Test Error", "No tests found in the report.")

    else:
        return ("Unknown Error", "Could not parse test results.")
        

def extract_function_name(cleaned_output):
        match = re.search(r"assert\s+(\w+)\s*\(", cleaned_output)
        return match.group(1) if match else None


def add_missing_function_names(test_class_source_code):
    print("Applying Rule 1: Adding missing function names...")
    print("BEFORE")
    print(test_class_source_code)
    lines = test_class_source_code.split("\n")
    imports = "\n".join(line for line in lines if line.startswith("import") or line.startswith("from"))
    non_imports = [line for line in lines if not (line.startswith("import") or line.startswith("from"))]

    test_functions = []
    test_counter = 1
    current_test_lines = []
    python_raised = False
    
    for line in non_imports:
        stripped_line = line.strip()

        if python_raised:
            current_test_lines.append(f"    {line}" if not line.startswith("        ") else line)
            test_functions.append(f"def test_auto_generated_{test_counter}():\n" + "\n".join(current_test_lines) + "\n")
            test_counter += 1
            current_test_lines = []
            python_raised = False

        elif stripped_line.startswith(("assert")):
            current_test_lines.append(f"    {line}" if not line.startswith("    ") else line)
            test_functions.append(f"def test_auto_generated_{test_counter}():\n" + "\n".join(current_test_lines) + "\n")
            test_counter += 1
            current_test_lines = []

        elif stripped_line.startswith(("with pytest.raises")):
            python_raised = True
            current_test_lines.append(f"    {line}" if not line.startswith("    ") else line)

        elif stripped_line:  # Non-empty line (e.g., a comment), keep it in the current test
            current_test_lines.append(f"    {line}" if not line.startswith("    ") else line)

    # Add the last test function if there's one pending
    if current_test_lines:
        test_functions.append(f"def test_auto_generated_{test_counter}():\n" + "\n".join(current_test_lines) + "\n")

    # Create new formatted content
    test_class_source_code = f"{imports}\n\n" + "\n\n".join(test_functions)
    print("AFTER")
    print(test_class_source_code)


def remove_self_from_standalone_functions(test_class_source_code, file):
    lines = test_class_source_code.split('\n')
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        # Look for function definitions that might have self parameter
        if line.lstrip().startswith('def ') and '(self' in line:
            # Handle multi-line function definitions
            while '):' not in line and i < len(lines) - 1:
                i += 1
                line += '\n' + lines[i]
            
            # Check if first argument is self
            if re.match(r'def\s+\w+\s*\(self\b', line):
                print("Applying Rule 5: Removing self argument from standalone test functions...")
                print("File: ", file)
                func_name = re.search(r'def\s+(\w+)', line).group(1)
                print("Function: ", func_name)
                
                # Remove self parameter
                line = re.sub(r'def\s+(\w+)\s*\(self\s*(?:,\s*)?', r'def \1(', line)
                line = re.sub(r'def\s+(\w+)\s*\(self\s*\)', r'def \1()', line)
        
        new_lines.append(line)
        i += 1
    test_class_source_code = '\n'.join(new_lines)


def rule_based_repair(test_case_path, error_msg, test_class, output):
    """Attempts to repair a test case using a rule-based approach."""

    with open(test_case_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    # RULE 5: Remove module definition from test class
    if error_msg and "ModuleNotFoundError" in error_msg:
        print("Applying Rule 5: Removing module definition from test class...")
        new_lines = []
        missing_module = re.search(r"ModuleNotFoundError: No module named '(\w+)'", error_msg).group(1)
        for line in test_class_source_code.split("\n"):
            if missing_module in line:
                continue
            new_lines.append(line)
        test_class_source_code = "\n".join(new_lines)
        output["repair_stats"]["rule_5"].append(test_class)

    # RULE 1: Add missing function names - only asserts are present
    has_function = bool(re.search(r"^\s*def test_", test_class_source_code, re.MULTILINE))
    has_asserts = bool(re.search(r"^\s*(assert|with pytest\.raises)", test_class_source_code, re.MULTILINE))

    if not has_function and has_asserts:
        add_missing_function_names(test_class_source_code, test_case_path)
        output["repair_stats"]["rule_1"].append(test_class)

    try :
        ast.parse(test_class_source_code)
    except SyntaxError:
        output["repair_stats"]["syntax_errors"].append(test_class)
        return "Syntax Error"

    function_name = extract_function_name(test_class_source_code)
    module_name = os.path.basename(test_case_path).replace(".py", "").removeprefix("test_")

    # RULE 2: Add missing pytest import
    pytest_import = "import pytest"
    if pytest_import not in test_class_source_code:
        print("Applying Rule 2: Adding missing pytest import...")
        test_class_source_code = pytest_import + "\n" + test_class_source_code
        output["repair_stats"]["rule_2"].append(test_class)

    # RULE 3: Add missing module import statement
    module_import = f"from {module_name} import {function_name}"
    if module_import not in test_class_source_code and function_name != None:
        print("Applying Rule 3: Adding missing module import statement...")
        test_class_source_code = module_import + "\n" + test_class_source_code
        output["repair_stats"]["rule_3"].append(test_class)

    # RULE 4: Remove self argument from standalone test functions
    has_class = bool(re.search(r"class\s+\w+", test_class_source_code))
    has_self_parameter = bool(re.search(r"def\s+\w+\s*\(self", test_class_source_code))
    if not has_class and has_self_parameter:
        remove_self_from_standalone_functions(test_class_source_code, test_case_path)
        output["repair_stats"]["rule_4"].append(test_class)

    with open(test_case_path, "w", encoding="utf-8") as f:
        f.write(test_class_source_code)


def get_failing_tests(report_path):
    """Extracts the names of the failing tests from a pytest report."""
    
    with open(report_path, "r") as f:
        report = json.load(f)

    failed_tests = [
        test["nodeid"].split("::")[-1]
        for test in report.get("tests", [])
        if test.get("outcome") == "failed"
    ]

    return failed_tests

def get_error_tests(report_path):
    """Extracts the names of the error tests from a pytest report."""
    
    with open(report_path, "r") as f:
        report = json.load(f)

    error_tests = [
        test["nodeid"].split("::")[-1]
        for test in report.get("tests", [])
        if test.get("outcome") == "error"
    ]

    print(error_tests)

    return error_tests


def remove_failing_tests(test_case_path, res, test_class, output):
    failing_tests = get_failing_tests("report.json")
    error_tests = get_error_tests("report.json")

    if len(failing_tests) > 0:
        output["repair_stats"]["removed_tests_failing"].append((test_class, len(failing_tests)))
    if len(error_tests) > 0:
        output["repair_stats"]["removed_tests_error"].append((test_class, len(error_tests)))

    failing_tests += error_tests
    remove_functions(test_case_path, failing_tests)
    
    
def remove_functions(test_case_path, functions_to_remove):
    with open(test_case_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    leading_spaces = 0
    i = -1
    while i < len(lines)-1:
        i += 1
        stripped = lines[i].strip()

        # Check if the line starts a failed function
        if any(f"def {fn}(" in stripped for fn in functions_to_remove):
            skip = True
            leading_spaces = lines[i].index(stripped)
            continue 

        # If we're skipping, check if a new function is starting
        if skip:
            if stripped.startswith(("def ", "class ")) and lines[i].index(stripped) == leading_spaces:
                # Check for function decorator
                if lines[i-1].strip().startswith(("@", "#")):
                    new_lines.append(lines[i-1])
                skip = False
            else:
                continue

        # If not skipping, keep the line
        new_lines.append(lines[i])

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
    elif res == "No Test Error":
        stats["no_tests_classes"] += 1
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


def get_class_under_test_coverage(test_case_path):
    """Returns the class under test coverage."""

    module_under_test_name = test_case_path.split("/")[-1].replace("test_", "").replace(".py", "")
    tests_dir = "/".join(test_case_path.split("/")[:-1])

    print(tests_dir)
    print(module_under_test_name)
    
    # Verify paths exist
    if not importlib.util.find_spec(module_under_test_name):
        raise FileNotFoundError(f"Target file not found: {module_under_test_name}")
    if not os.path.exists(tests_dir):
        raise FileNotFoundError(f"Tests directory not found: {tests_dir}")
    
    # Build the command
    cmd = [
        "pytest",
        f"--cov={module_under_test_name}",
        "--cov-report=term",
        "--timeout=5",
        str(tests_dir)
    ]
    
    try:
        # Run the command and capture output
        print("Running pytest to get coverage...")
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True
        )
        print(result.stdout)
        return result.stdout
    
    except subprocess.CalledProcessError as e:
        return f"Error running pytest:\n{e.stdout}\n{e.stderr}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def optimise_test_suite_effectiveness(test_case_path, enhanced_test_case_path, test_class, output):
    """Optimises the test suite effectiveness by removing tests that do not improve coverage."""
    # First, get the class under test coverage

    # Next, add the enhance tests one at a time and check if the coverage improves

    pass # TODO: implement this function!!


def evaluate_functional_correctness(path, effectiveness_optimization=False, enhanced_test_suite_path=None):
    test_classes = [f for f in os.listdir(path) if f.endswith(".py")]
    stats_pre_repair = {
        "total_classes": 0,
        "syntax_errors": 0,
        "compilation_errors": 0,
        "no_tests_classes" : 0,
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "error_tests": 0,
    }
    stats_post_repair = stats_pre_repair.copy()
    stats_post_removal = stats_pre_repair.copy()
    output = {
        "repair_stats": {
            "rule_0": [],
            "rule_1": [],
            "rule_2": [],
            "rule_3": [],
            "rule_4": [],
            "rule_5": [],
            "removed_tests_failing": [],
            "removed_tests_error": [],
            "removed_tests_not_improved_coverage": [],
            "syntax_errors": [],
        }
    }

    for test_class in test_classes:
        # if test_class not in ["test_HumanEval_20.py", "test_HumanEval_158.py"]:
        #     continue

        # Ensure the test function is not implemented in the test class
        remove_test_function_implementation(path, test_class, output)

        # Evaluate the test class correctness
        test_class_path = os.path.join(path, test_class)
        res = check_correctness(test_class_path)
        passed = add_correction_evaluation_stats(stats_pre_repair, res[0])

        # Attempt to repair the test class if failed
        if not passed:
            error_msg = res[1]
            rule_based_repair(test_class_path, error_msg, test_class, output)

            # Evaluate the test class correctness
            res = check_correctness(test_class_path)
            passed = add_correction_evaluation_stats(stats_post_repair, res[0])

            # Remove the tests that are still failing
            if not passed:
                remove_failing_tests(test_class_path, res, test_class, output)

        # Evaluate the test class correctness again
        res = check_correctness(test_class_path)
        add_correction_evaluation_stats(stats_post_removal, res[0])
        
        # Optimize the test suite effectiveness - ONLY works in tmp directory
        if effectiveness_optimization and enhanced_test_suite_path:
            enhanced_test_case_path = os.path.join(enhanced_test_suite_path, test_class) 
            optimise_test_suite_effectiveness(test_class_path, enhanced_test_case_path, test_class, output)
    

    print("Functional Correctness Evaluation Results PRE:")
    print(json.dumps(stats_pre_repair, indent=4))

    print("Functional Correctness Evaluation Results POST REPAIR:")
    print(json.dumps(stats_post_repair, indent=4))

    print("Functional Correctness Evaluation Results POST REMOVAL:")
    print(json.dumps(stats_post_removal, indent=4))

    if effectiveness_optimization:
        print("Effectiveness Optimization Results:")
        # TODO: Print effectiveness optimization results

    output["correctness_eval_counts"] = {
        "stats_pre_repair" : stats_pre_repair,
        "stats_post_repair" : stats_post_repair, 
        "stats_post_removal" : stats_post_removal,
        # TODO: Add effectiveness optimization results
    }

    return output


def remove_test_function_implementation(path, test_class, output):
    """Removes the test function implementation from the test class."""
    test_class_path = os.path.join(path, test_class)
    with open(test_class_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    function_name = extract_function_name(test_class_source_code)

    # RULE 0: Remove module definition from test class
    if f"def {function_name}(" in test_class_source_code:
        print("Applying Rule 0: Removing module definition from test class...")
        remove_functions(test_class_path, [function_name])
        output["repair_stats"]["rule_0"].append(test_class)


def print_file(path):
    with open(path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()
        print(test_class_source_code)

if __name__ == "__main__":
    # print("CORRECTNESS EVALUATION RESULTS:")
    # print(evaluate_functional_correctness("data/human-eval/tests/chatgpt/enhanced") )

    get_class_under_test_coverage("tmp/human_eval/tests/chatgpt/test_HumanEval_107.py")