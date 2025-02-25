import json
import re
import sys
from pathlib import Path

PATH_TO_JSON = "data/human-eval/human-eval-dataset.jsonl" # Needs to be executed from root directory

def process_json(file_path=PATH_TO_JSON):
    """Reads the JSON file, extracts the test node, and converts it to pytest format."""

    # Read the JSONL file line by line
    with open(file_path, "r") as f:
        for line_number, line in enumerate(f, start=1):
            try:
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
    
    # Extract assertions
    assertions = re.findall(r'assert candidate(.*?) == (.*?)\n', test_str)
    
    # Generate test function with parameterization)
    param_lines = [f"    {args.strip()}, {expected.strip()}" for args, expected in assertions]
    param_str = ",\n".join(param_lines)
    
    return f"""
import pytest
from {module_name} import {candidate_name}  # Replace with the actual module

@pytest.mark.parametrize("inputs, expected", [
{param_str}
])
def test_{candidate_name}(inputs, expected):
    assert {candidate_name}(*inputs) == expected
"""



if __name__ == "__main__":
    process_json()
