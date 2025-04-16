
import json
import subprocess
import re
import os
import ast
import shutil
import math
import compileall
import importlib.util
from pathlib import Path
import src.utility_functions as uf

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
            failed = sum(1 for test in report.get("tests", []) if test["outcome"] == "failed" or test["outcome"] == "xfailed")
            errored = sum(1 for test in report.get("tests", []) if test["outcome"] == "error")
            return (f"{passed} tests passed, {failed} tests failed, {errored} tests errored", None)
        else:
            msg = [it["longrepr"] for it in report.get("collectors") if it["outcome"] == "failed" or it["outcome"] == "xfailed"]
            if msg:
                msg = "\n".join(msg)
                return ("Compilation Error", msg)
            else:
                print("No tests found in the report. " + test_case_path)
                return ("No Test Error", "No tests found in the report.")

    else:
        return ("Unknown Error", "Could not parse test results.")
        

def extract_function_name(test_path, module_name):
    module_path = "/".join(test_path.split("/")[:-3]) + "/" + module_name + ".py"
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"Target file not found: {module_path}")
    else:
        with open(module_path, "r", encoding="utf-8") as f:
            module_source_code = f.read()
        
        pattern = r'^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, module_source_code, re.MULTILINE)
        return matches


def add_missing_function_names(test_class_source_code):
    print("Applying Rule 1: Adding missing function names...")
    # print("BEFORE")
    # print(test_class_source_code)
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
    # print("AFTER")
    # print(test_class_source_code)


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
                print("Applying Rule 4: Removing self argument from standalone test functions...")
                # print("File: ", file)
                # func_name = re.search(r'def\s+(\w+)', line).group(1)
                # print("Function: ", func_name)
                
                # Remove self parameter
                line = re.sub(r'def\s+(\w+)\s*\(self\s*(?:,\s*)?', r'def \1(', line)
                line = re.sub(r'def\s+(\w+)\s*\(self\s*\)', r'def \1()', line)
        
        new_lines.append(line)
        i += 1
    test_class_source_code = '\n'.join(new_lines)


def remove_empty_class_definition(test_class_path):
    with open(test_class_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        class_match = re.match(r'^(\s*)class\s+\w+\s*(\(.*\))?\s*:\s*$', line)
        if class_match:
            indent = class_match.group(1)
            class_block = [line]
            i += 1

            # Collect class body
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip() == "":
                    class_block.append(next_line)
                    i += 1
                    continue
                if next_line.startswith(indent + "    ") or next_line.startswith(indent + "\t"):
                    class_block.append(next_line)
                    i += 1
                else:
                    print("Class block = " + "".join(class_block))
                    break

            # If there are no functions, remove the class block
            has_function = any(re.match(r'^\s*def\s+\w+\s*\(', l) for l in class_block)
            if not has_function: 
                continue
            else:
                output_lines.extend(class_block)
        else:
            output_lines.append(line)
            i += 1

    with open(test_class_path, "w", encoding="utf-8") as f:
        f.write(''.join(output_lines))


def get_test_case_by_line(source_code, line_number):
    lines = source_code.splitlines()
    function_positions = []

    for idx, line in enumerate(lines):
        match = re.match(r'^\s*def\s+(test_\w+)\s*', line)
        if match:
            function_name = match.group(1)
            function_positions.append((idx + 1, function_name))  # Line numbers are 1-based

    current_function = None
    for i, (start_line, name) in enumerate(function_positions):
        end_line = function_positions[i + 1][0] - 1 if i + 1 < len(function_positions) else len(lines)
        if start_line <= line_number <= end_line:
            current_function = name
            break

    return current_function


def rule_based_repair(test_case_path, error_msg, test_class, output):
    """Attempts to repair a test case using a rule-based approach."""

    with open(test_case_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    # RULE 5: Remove module definition from test class
    if error_msg and type(error_msg) == str and "ModuleNotFoundError" in error_msg:
        print("Applying Rule 5: Removing module definition from test class...")
        new_lines = []
        missing_module = re.search(r"ModuleNotFoundError: No module named '(\w+)'", error_msg).group(1)
        for line in test_class_source_code.split("\n"):
            if f"import {missing_module}" in line or f"from {missing_module}" in line:
                if missing_module == "module_0":
                    class_under_test = test_class.replace(".py", "").removeprefix("test_")
                    new_lines.append(f"import {class_under_test} as module_0")
                continue
            new_lines.append(line)
        test_class_source_code = "\n".join(new_lines)
        output["repair_stats"]["rule_5"].append(test_class)

    # RULE 6: Removing test cases with SyntaxErrors
    if error_msg and type(error_msg) == SyntaxError:
        print("Applying Rule 6: Removing test causing SyntaxError...")
        syntax_error_line = error_msg.lineno
        syntax_error_test_case = get_test_case_by_line(test_class_source_code, syntax_error_line)
        print("Removing test case: ", syntax_error_test_case)

        test_class_source_code = remove_functions(test_case_path, [syntax_error_test_case])
        output["repair_stats"]["rule_6"].append(test_class)
        
    # RULE7: Remove test cases with no compilable code - they are causing IndentationError
    if error_msg and type(error_msg) == IndentationError:
        print("Applying Rule 7: Removing test causing IndentationError...")
        # The error in on the line of next function => just find the previous function by lineno-1
        error_line = error_msg.lineno - 1
        error_test_case = get_test_case_by_line(test_class_source_code, error_line)
        test_class_source_code = remove_functions(test_case_path, [error_test_case])
        output["repair_stats"]["rule_7"].append(test_class)

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

    # RULE 2: Add missing pytest import
    pytest_import = "import pytest"
    if pytest_import not in test_class_source_code:
        print("Applying Rule 2: Adding missing pytest import...")
        test_class_source_code = pytest_import + "\n" + test_class_source_code
        output["repair_stats"]["rule_2"].append(test_class)

    module_name = os.path.basename(test_case_path).replace(".py", "").removeprefix("test_")
    function_names = extract_function_name(test_case_path, module_name)

    # RULE 3: Add missing module import statement
    module_import = f"from {module_name} import {', '.join(function_names)}"
    pynguin_import = f"import {module_name} as module_0"
    print("Module import: ", module_import)
    if module_import not in test_class_source_code and function_names != [] and pynguin_import not in test_class_source_code:
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
        if test.get("outcome") == "failed" or test.get("outcome") == "xfailed"
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

    return error_tests


def remove_failing_tests(test_case_path, res, test_class, output):
    failing_tests = get_failing_tests("report.json")
    error_tests = get_error_tests("report.json")

    if len(failing_tests) > 0:
        output["repair_stats"]["removed_tests_failing"].append((test_class, len(failing_tests)))
    if len(error_tests) > 0:
        output["repair_stats"]["removed_tests_error"].append((test_class, len(error_tests)))

    failing_tests += error_tests
    print(failing_tests)
    remove_functions(test_case_path, failing_tests)
    

def get_function_definition_count(source_code, function_name):
    """Counts the number of times a function is defined in the source code."""
    pattern = rf"^\s*def\s+{function_name}\s*\("
    return len(re.findall(pattern, source_code, re.MULTILINE))


def remove_functions(test_case_path, functions_to_remove, removeLast=False):
    with open(test_case_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    functions_count = {}
    functions_occurance = { function_name:0 for function_name in functions_to_remove }
    if removeLast: 
        for function_name in functions_to_remove:
            function_count = get_function_definition_count("".join(lines), function_name)
            functions_count[function_name] = function_count
              
    new_lines = []
    skip = False
    leading_spaces = 0
    i = -1
    while i < len(lines)-1:
        i += 1
        stripped = lines[i].strip()

        # Check if the line starts a failed function
        if any(f"def {fn}" in stripped for fn in functions_to_remove):
            fn = re.search(r"def\s+(\w+)\s*", stripped).group(1)
            functions_occurance[fn] += 1

            # if removeLast -> only remove the last occurance of the function
            if removeLast and functions_occurance[fn] < functions_count[fn]:
                if lines[i-1].strip().startswith(("@", "#")):
                    new_lines.append(lines[i-1])
                skip = False
                new_lines.append(lines[i])
                continue
                
            skip = True
            leading_spaces = lines[i].index(stripped)

            # Remove the function decorator if it exists and is added to new_lines
            if len(new_lines) > 0 and new_lines[len(new_lines)-1].strip().startswith(("@", "#")):
                new_lines.pop()

            # Remove the parametrize decorator if it exists and is added to new_lines
            if len(new_lines) > 0 and new_lines[len(new_lines)-1].strip().startswith("])"):
                print("Removing the parametrize decorator...")
                new_lines.pop()
                while len(new_lines) > 0 and not new_lines[len(new_lines)-1].strip().startswith("@") and not new_lines[len(new_lines)-1].strip() == '':
                    print(f"Removing the line: {new_lines[len(new_lines)-1]}")
                    new_lines.pop()
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
    return "".join(new_lines)


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
        return False
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


def cleanup_no_unit_test_class(test_class_path):
    with open(test_class_path, "r", encoding="utf-8") as f:
        source_code = f.read()
    if "class" in source_code:
        # CLEANUP: Remove the class definition
        source_code = re.sub(r"class\s+\w+\s*:\s*", "", source_code)

    with open(test_class_path, "w", encoding="utf-8") as f:
        f.write(source_code)
    

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
            "rule_6": [],
            "rule_7": [],
            "removed_tests_failing": [],
            "removed_tests_error": [],
            "removed_tests_not_improved_coverage": [],
            "syntax_errors": [],
        }
    }

    for test_class in test_classes:
        # if test_class not in ["test_HumanEval_91.py"]:
        #     continue

        # Evaluate the test class correctness
        test_class_path = os.path.join(path, test_class)
        print("INFO: Evaluating correctness of the test class: ", test_class_path)

        # Ensure the test function is not implemented in the test class
        remove_test_function_implementation(path, test_class, output)
        
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
                remove_empty_class_definition(test_class_path)

                # class_test_cases = uf.extract_test_cases_from_file(test_class_path)
                # if len(class_test_cases) == 0:
                #     cleanup_no_unit_test_class(class_test_cases)

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
    """Removes the class under test function implementation from the test class."""
    test_class_path = os.path.join(path, test_class)
    with open(test_class_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    module_name = test_class.replace(".py", "").removeprefix("test_")
    function_names = extract_function_name(path, module_name)

    # RULE 0: Remove module definition from test class
    for function_name in function_names:
        if f"def {function_name}(" in test_class_source_code:
            print("Applying Rule 0: Removing module definition from test class...")
            remove_functions(test_class_path, [function_name])
            output["repair_stats"]["rule_0"].append(test_class)


def print_file(path):
    with open(path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()
        print(test_class_source_code)
    return test_class_source_code

### Effectiveness Optimization

def remove_new_test_case(new_test_case, test_class_path):
    with open(test_class_path, "r", encoding="utf-8") as f:
        test_class_source_code = f.read()

    # Remove the new test case from the test class source code
    test_class_source_code = test_class_source_code.replace(f"\n"+new_test_case+"\n", "", 1)
    
    with open(test_class_path, "w", encoding="utf-8") as f:
        f.write(test_class_source_code)

def adjust_new_test_case(new_test_case, test_class_path):
    """Adjusts the new test case to match the existing test case format."""
    
    with open(test_class_path, "r", encoding="utf-8") as f:
        test_class = f.read()

    # Handle class-based test cases
    if "class " in test_class:
        # If unit tests are in a class, add the self argument if not present
        if not re.search(r'def\s+\w+\s*\(\s*self\b', new_test_case):
            new_test_case = re.sub(r"def\s+(\w+)\s*\(", r"def \1(self, ", new_test_case)

        new_lines = []
        lines = new_test_case.split("\n")
        for line in lines:
            new_lines.append(f"    {line}")
        new_test_case = "\n".join(new_lines)
    else:
        # If unit tests are standalone, remove the self argument if present
        match = r'(def\s+\w+\s*\()([^)]*)\)(:)'

        def replacer(match):
            args = match.group(2).split(',')
            args = [arg.strip() for arg in args if arg.strip() != 'self']
            return match.group(1) + ', '.join(args) + ')' + match.group(3)
        
        new_test_case = re.sub(match, replacer, new_test_case, count=1)

    # Handle pynguin imports (module_0)
    module_name = os.path.basename(test_class_path).replace(".py", "").removeprefix("test_")
    pynguin_import = f"import {module_name} as module_0"
    if pynguin_import in test_class:
        # Add the module_0. prefix to everywhere the function from module_0 is used
        print("Adding module_0 prefix to function names if needed")
        function_names = extract_function_name(test_class_path, module_name)
        pattern = r'(?<!module_0\.)\b(' + '|'.join(map(re.escape, function_names)) + r')\b'

        def add_module_prefix(match):
            return f'module_0.{match.group(1)}'
        
        new_test_case = re.sub(pattern, add_module_prefix, new_test_case)

    return new_test_case

def get_class_under_test_coverage_metrics(test_case_path):
    """Returns the class under test coverage."""

    module_under_test_name = test_case_path.split("/")[-1].replace("test_", "").replace(".py", "")
    tests_dir = "/".join(test_case_path.split("/")[:-1])
    
    if not importlib.util.find_spec(module_under_test_name):
        raise FileNotFoundError(f"Target file not found: {module_under_test_name}")
    if not os.path.exists(tests_dir):
        raise FileNotFoundError(f"Tests directory not found: {tests_dir}")
    
    cmd = [
        "pytest",
        f"--cov={module_under_test_name}",
        "--cov-branch",
        "--cov-report=json",
        "--timeout=5",
        str(tests_dir)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True
        )
        
        # Get the coverage metrics from the json report
        if not os.path.exists("coverage.json"):
            raise FileNotFoundError("Coverage report not found: coverage.json")
        
        with open("coverage.json", "r") as f:
            coverage_report = json.load(f)
        
        file_path = list(coverage_report["files"].keys())[0]
        file_metrics = coverage_report["files"][file_path]
        print("File metrics summary:")
        print(json.dumps(file_metrics['summary'], indent=4))
        coverage_metrics = {
            "covered_lines": file_metrics["summary"]["covered_lines"],
            "num_statements": file_metrics["summary"]["num_statements"],
            "percent_covered": file_metrics["summary"]["percent_covered"],
            "missing_lines": file_metrics["summary"]["missing_lines"],
            "covered_branches": file_metrics["summary"]["covered_branches"],
            "num_branches": file_metrics["summary"]["num_branches"],
        }
        if "num_branches" in file_metrics["summary"] and float(file_metrics["summary"]["num_branches"]) > 0:
            coverage_metrics["percent_covered_branches"] = float(file_metrics["summary"]["covered_branches"]) / float(file_metrics["summary"]["num_branches"]) * 100
        else:
            coverage_metrics["percent_covered_branches"] = 100
        
        print("Coverage metrics:")
        print(json.dumps(coverage_metrics, indent=4))
        return coverage_metrics
    
    except subprocess.CalledProcessError as e:
        return f"Error running pytest:\n{e.stdout}\n{e.stderr}"
    except Exception as e:
        return f"Unexpected error: {e}"


def optimise_test_suite_effectiveness(exising_test_suite_path, enhanced_test_suite_path):
    """Optimises the test suite effectiveness by removing tests that do not improve coverage."""
    
    test_classes = [ f for f in os.listdir(exising_test_suite_path) if f.endswith(".py")]
    optimisation_statistics = {
        "total_test_classes": len(test_classes),
        "classes": {},
    }
    for test_class in test_classes:
        # if test_class not in ["test_HumanEval_108.py", "test_HumanEval_112.py"]:
        #     continue
        # Get existing coverage metrics
        test_class_path = os.path.join(exising_test_suite_path, test_class)
        print("INFO: Optimising the test class: ", test_class_path)
        
        existing_coverage = get_class_under_test_coverage_metrics(test_class_path)
        if "percent_covered" not in existing_coverage:
            print("ERROR: No coverage metrics found in the report.")
            print(existing_coverage)

            existing_coverage = {
                "percent_covered": 0,
                "percent_covered_branches": 0,
            }
             
        print("Existing coverage: ", existing_coverage["percent_covered"])
        print("Existing branch coverage: ", existing_coverage["percent_covered_branches"])

        # Add the new tests one at a time to see if they improve coverage
        new_test_cases_path = os.path.join(enhanced_test_suite_path, test_class)
        new_test_cases = uf.extract_test_cases_from_file(new_test_cases_path)
        print("New test cases: ", new_test_cases)
        print(len(new_test_cases))
        class_stats = {
            "total_test_cases": len(new_test_cases),
            "kept_test_cases": 0,
            "removed_test_cases": 0,
            "skipped_test_cases": 0,
            "faulty_test_cases": 0,
            "initial_coverage": existing_coverage,
            "final_coverage": None,
        }
        for new_test_case in new_test_cases:
            if math.isclose( float(existing_coverage["percent_covered"]), 100.0 ) and math.isclose( float(existing_coverage["percent_covered_branches"]), 100.0 ):
                print("Skipping test case: ", new_test_case)
                class_stats["skipped_test_cases"] += 1
                continue

            # Remove or add the self argument to the test case if needed
            new_test_case = adjust_new_test_case(new_test_case, test_class_path)

            print("Evaluating the new test case: ")
            print(new_test_case)

            # Temporarily add the new test case to the existing test case
            with open(test_class_path, "a", encoding="utf-8") as f:
                f.write("\n"+new_test_case+"\n")

            new_coverage = get_class_under_test_coverage_metrics(test_class_path)

            if "percent_covered" in new_coverage:
                print("NEW coverage: ", new_coverage["percent_covered"])
                print("NEW branch coverage: ", new_coverage["percent_covered_branches"])

                if float(new_coverage["percent_covered"]) > float(existing_coverage["percent_covered"]) or float(new_coverage["percent_covered_branches"]) > float(existing_coverage["percent_covered_branches"]):
                    # If the new test case improves coverage, keep it
                    print(f"Keeping test case:\n {new_test_case}")
                    class_stats["kept_test_cases"] += 1
                    existing_coverage = new_coverage
                else:
                    # If the new test case does not improve coverage, remove it
                    print(f"Removing test case:\n {new_test_case}")
                    class_stats["removed_test_cases"] += 1
                    remove_new_test_case(new_test_case, test_class_path)

            else:
                print("ERROR: No coverage metrics found in the report.")
                print(new_coverage)
                class_stats["faulty_test_cases"] += 1
                
                # Remove the function definition from the test class
                print(f"Removing test case: ") 
                print(new_test_case)              
                remove_new_test_case(new_test_case, test_class_path)

        class_stats["final_coverage"] = existing_coverage
        optimisation_statistics["classes"][test_class] = class_stats

        print(f"Class statistics: {test_class}")
        print(json.dumps(class_stats, indent=4))

        # Save the optimised test class
        optimised_path = enhanced_test_suite_path.replace("enhanced", "optimised")
        if not os.path.exists(optimised_path):
            os.makedirs(optimised_path)
        shutil.copy(test_class_path, os.path.join(optimised_path, test_class))

    return optimisation_statistics


if __name__ == "__main__":
    # print("CORRECTNESS EVALUATION RESULTS:")
    # print(evaluate_functional_correctness("tmp/human_eval/tests/human_written/") )

    # get_class_under_test_coverage_metrics("tmp/human_eval/tests/chatgpt/test_HumanEval_107.py")
    uf.copy_python_files("data/human_eval/tests/chatgpt/enhanced/chatgpt_problem_similarity_5", "tmp/human_eval/tests/chatgpt")
    pass