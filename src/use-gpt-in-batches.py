import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import utility_functions as uf
from batch_request import BatchRequest
import batch_request as br
import re

BATCH_REQUESTS_DIR="data/batch_requests/"

# Setting up the variables
BATCH_REQUESTS_JSON="data/batch_requests.jsonl"
INPUT_DATASET_PATH = 'tmp/human-eval'

BATCH_JOB_NAME = "unit_test_generation"
BATCH_OUTPUT_DIR = 'data/human-eval/tests/chatgpt'
BATCH_JSON_NAME = "batch_requests.jsonl"
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.1

# Load the environment variables
load_dotenv(override=True)

# Initialize a connection to the OpenAI API
client = OpenAI()

# Define the prompt for generating initial unit test cases
generate_initial_unit_tests_system_prompt = '''
Your goal is to generate unit tests for a python class using the pytest framework. You will be provided with the class definition, and you will output a list of unit test.
The unit tests should cover the most important methods of the class, reaching a minimum of 80% code coverage.
Make sure to keep the tests simple and easy to understand. The output should only include the test classes.
'''

generate_new_test_cases_system_prompt = '''
Your goal is to generate new unit tests for a python class using the pytest framework. You will be provided with the class definition, example unit tests, and you will output a list of new unit test.
Try to draw inspiration from the example unit tests and create new test cases that cover different aspects of the class functionality.
Make sure to keep the tests simple and easy to understand. The output should only include the test classes.
'''


def batch_exists(identifiers, batch_requests: list[BatchRequest]):
    """Check if a batch request with the given identifiers exists."""
    for batch_request in batch_requests:
        if batch_request.identifiers == identifiers:
            return True
    return False


def load_batch_requests(batch_file_path=BATCH_REQUESTS_DIR, client=None):
    """Load the batch requests from a JSON file."""
    batch_requests = []
    request_json_path = os.path.join(batch_file_path, "batch_requests.jsonl")
    if os.path.exists(request_json_path):
        with open(request_json_path, "r") as file:
            for line in file:
                batch_data = json.loads(line)
                batch_request = BatchRequest.from_dict(batch_data, client=client)
                batch_requests.append(batch_request)
    return batch_requests


def save_batch_requests(batch_requests, batch_file_path=BATCH_REQUESTS_DIR):
    """Save the batch requests to a JSON file."""
    if not os.path.exists(batch_file_path):
        os.makedirs(batch_file_path)

    out_path = os.path.join(batch_file_path, "batch_requests.jsonl")
    with open(out_path, "w") as file:
        for batch_request in batch_requests:
            file.write(json.dumps(batch_request.to_json()) + "\n")


if __name__ == "__main__":
    # get_initial_test_cases_batch(INPUT_DATASET_PATH)
    batch_requests = load_batch_requests(client=client)
    identifiers = {
        "project_name": "human-eval",
        "job_type" : "fewshot_test_suite_enhancement",
        "test_source": "human-written",
        "test_selection_mode": "random",
        "num_test_cases": 1,
        "model_name": "gpt-4o-mini",
        "temperature": 0.1
    }

    if batch_exists(identifiers, batch_requests):
        print("Batch request already exists.")
        
    else:
        new_batch_request = BatchRequest(
            "data/human-eval/tests/human-written/enhanced/",
            "data/human-eval/tests/human-written",
            generate_new_test_cases_system_prompt,
            client,
            identifiers)
        new_batch_request.print_batch_tasks_user_prompts()
        batch_requests.append(new_batch_request)

    save_batch_requests(batch_requests)
    pass