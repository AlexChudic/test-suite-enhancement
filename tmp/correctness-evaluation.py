
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


def add_missing_functino_names(test_class_source_code):
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


def rule_based_repair(test_case_path):
    """Attempts to repair a test case using a rule-based approach."""

    with open(test_case_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    # RULE 1: Add missing function names - only asserts are present
    has_function = bool(re.search(r"^\s*def test_", test_class_source_code, re.MULTILINE))
    has_asserts = bool(re.search(r"^\s*(assert|with pytest\.raises)", test_class_source_code, re.MULTILINE))

    if not has_function and has_asserts:
        add_missing_functino_names(test_class_source_code, test_case_path)

    try :
        ast.parse(test_class_source_code)
    except SyntaxError:
        return "Syntax Error"

    function_name = extract_function_name(test_class_source_code)
    module_name = os.path.basename(test_case_path).replace(".py", "").removeprefix("test_")

    # RULE 2: Add missing pytest import
    pytest_import = "import pytest"
    if pytest_import not in test_class_source_code:
        print("Applying Rule 2: Adding missing pytest import...")
        test_class_source_code = pytest_import + "\n" + test_class_source_code

    # RULE 3: Add missing module import statement
    module_import = f"from {module_name} import {function_name}"
    if module_import not in test_class_source_code:
        print("Applying Rule 3: Adding missing module import statement...")
        test_class_source_code = module_import + "\n" + test_class_source_code

    # RULE 4: Remove module definition from test class
    if f"def {function_name}(" in test_class_source_code:
        print("Applying Rule 4: Removing module definition from test class...")

        test_class_source_code

    # RULE 5: Remove self argument from standalone test functions
    has_class = bool(re.search(r"class\s+\w+", test_class_source_code))
    has_self_parameter = bool(re.search(r"def\s+\w+\s*\(self", test_class_source_code))
    if not has_class and has_self_parameter:
        remove_self_from_standalone_functions(test_class_source_code, test_case_path)

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

    print(f"Removing failing tests from the test case... {test_case_path}")
    print(f"Result: {res}")
    print(f"Failing tests: {failing_tests}")

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
        if test_class not in ["test_HumanEval_107.py", "test_HumanEval_158.py"]:
            continue

        # Evaluate the test class correctness
        test_class_path = os.path.join(path, test_class)
        res = check_correctness(test_class_path)
        passed = add_correction_evaluation_stats(stats_pre_repair, res)

        # Attempt to repair the test class if failed
        if not passed:
            rule_based_repair(test_class_path)

            # Evaluate the test class correctness
            res = check_correctness(test_class_path)
            passed = add_correction_evaluation_stats(stats_post_repair, res)


            # Remove the tests that are still failing
            if not passed:
                print("REMOVING")
                print(print_file(test_class_path))
                remove_failing_tests(test_class_path, res)
                print("REMOVED")
                print(print_file(test_class_path))

                # Evaluate the test class correctness again
                res = check_correctness(test_class_path)
                add_correction_evaluation_stats(stats_post_removal, res)
                
    
    print("Functional Correctness Evaluation Results PRE:")
    print(json.dumps(stats_pre_repair, indent=4))

    print("Functional Correctness Evaluation Results POST REPAIR:")
    print(json.dumps(stats_post_repair, indent=4))

    print("Functional Correctness Evaluation Results POST REMOVAL:")
    print(json.dumps(stats_post_removal, indent=4))


def print_file(path):
    with open(path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()
        print(test_class_source_code)

if __name__ == "__main__":
    evaluate_functional_correctness("data/human-eval/tests/chatgpt/enhanced")