import json
import re
import ast
import sys
from pathlib import Path
from typing import List, Tuple

PATH_TO_JSON = "data/human-eval/human-eval-dataset.jsonl" # Needs to be executed from root directory

def process_json(file_path=PATH_TO_JSON):
    """Reads the JSON file, extracts the test node, and converts it to pytest format."""

    # Read the JSONL file line by line
    with open(file_path, "r") as f:
        for line_number, line in enumerate(f, start=1):
            try:
                # if line_number not in [152, 73, 114]:
                #     continue
                
                # Parse each line as a JSON object
                data = json.loads(line.strip())
                
                # Extract task_id, prompt, and solution
                task_id = data["task_id"].replace("/", "_")  # Replace slashes for valid filenames                
                candidate_name = extract_candidate_function(data['prompt'])
                test_code = data['test']
                pytest_code = convert_to_pytest(test_code, candidate_name, task_id)
                
                # Craft the output path
                output_path = file_path.split("/")[:-1]
                output_path.append("tests")
                output_path.append("human-written")
                output_path.append("test_" + task_id + ".py")
                output_path = "/".join(output_path)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(pytest_code)
                
                print(f"Converted test saved to {output_path}")

            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_number}")
            except KeyError as e:
                print(f"Missing key {e} on line {line_number}")


def extract_candidate_function(prompt_str):
    """Extracts the function name from the prompt string."""
    match = re.search(r'def (\w+)\(', prompt_str)
    return match.group(1) if match else 'candidate'

def convert_to_pytest(test_str, candidate_name, module_name):
    """Converts the given test string to a pytest-compatible format."""
    
    lines = test_str.split('\n')
    start_idx = next((i for i, line in enumerate(lines) if line.strip() == 'def check(candidate):'), -1)
    
    if start_idx == -1:
        raise ValueError("No 'def check(candidate):' found in the input string.")
    
    test_lines = lines[start_idx + 1:]
    modified_test_lines = [ re.sub(r'\bcandidate\b', candidate_name, line) for line in test_lines]
    
    new_test_function = ['import pytest', f'from {module_name} import {candidate_name}', '',f'def test_{candidate_name}():'] + modified_test_lines
    
    final_test_class = create_function_for_each_assert('\n'.join(new_test_function))

    print("TEST STRING=\n" + test_str + "\n")
    print("NEW TEST FUNCTION=\n" + '\n'.join(new_test_function) + "\n")
    print("FINAL TEST CLASS =\n" + final_test_class  + "\n")

    return final_test_class


def extract_asserts(test_str):
    """Returns the asserts for the specified class."""
    
    tree = ast.parse(test_str)
    asserts = []
    lines = test_str.splitlines()

    def get_source_segment(node, prev_end):
        """Extract source code of a assert including any previous lines."""
        start_lineno = prev_end if prev_end else node.lineno - 1
        end_lineno = node.end_lineno

        # Include decorator lines if present
        while start_lineno > 0 and lines[start_lineno-1].strip().startswith("@"):
            start_lineno -= 1

        return "\n".join(lines[start_lineno:end_lineno])

    prev_end = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            asserts.append(get_source_segment(node, prev_end))
            prev_end = node.end_lineno


    return asserts

def create_function_for_each_assert(test_str):
    # Find all test functions
    test_func_pattern = re.compile(
        r'def\s+(test_\w+)\(\):\s*(?:""".*?""")?\s*(.*?)(?=\n\s*def\s+test_|\n\s*$)', 
        re.DOTALL
    )
    test_functions = test_func_pattern.finditer(test_str)
    
    new_content = []
    last_pos = 0
    
    for match in test_functions:
        # Add everything before this test function
        new_content.append(test_str[last_pos:match.start()])
        last_pos = match.end()
        
        func_name = match.group(1)
        func_body = match.group(2)
        full_func = f"def {func_name}():\n    {func_body}"

        try:
            asserts = extract_asserts(full_func)
            for i, assert_str in enumerate(asserts, 1):
                # Split the assert string into a new function
                assert_func = f"def {func_name}_{i}():\n{assert_str}"
                new_content.append(assert_func)
                new_content.append("\n\n")
            
        except ValueError as e:
            new_content.append(full_func)
            new_content.append("\n\n")
    
    # Add remaining content
    new_content.append(test_str[last_pos:])
    out = "".join(new_content)
    return out


if __name__ == "__main__":
    process_json()
