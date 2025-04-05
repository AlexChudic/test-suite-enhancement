import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import src.utility_functions as uf
from src.batch_request import BatchRequest
import re

BATCH_REQUESTS_DIR="data/batch_requests/"

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

def get_batch_request(identifiers, batch_requests: list[BatchRequest]):
    """Get a batch request with the given identifiers."""
    for batch_request in batch_requests:
        if batch_request.identifiers == identifiers:
            return batch_request
    return None

def load_batch_requests(client, batch_file_path=BATCH_REQUESTS_DIR):
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


def continue_processing_batch_requests(client):
    """Continue processing the batch requests."""
    batch_requests = load_batch_requests(client=client)
    for batch_request in batch_requests:
        batch_request.continue_processing(submit_job=True)
    save_batch_requests(batch_requests)


if __name__ == "__main__":
    batch_requests = load_batch_requests(client=client)
    
    # identifiers = {
    #     "project_name": "human_eval",
    #     "job_type" : "fewshot_test_suite_enhancement",
    #     "test_source": "chatgpt",
    #     "test_selection_mode": "random_from_class_under_test",
    #     "num_test_cases": 2,
    #     "model_name": "gpt-4o-mini",
    #     "temperature": 0.1
    # }
    # if batch_exists(identifiers, batch_requests):
    #     print("Batch request already exists.")
    # else:
    #     new_batch_request = BatchRequest(
    #         "data/human_eval/tests/chatgpt/enhanced/",
    #         "data/human_eval/tests/chatgpt",
    #         None,
    #         client,
    #         identifiers)
    #     new_batch_request.print_batch_tasks_user_prompts()
    #     batch_requests.append(new_batch_request)

    # for batch_request in batch_requests:
    #     batch_request.check_status()
    #     batch_request.continue_processing()
    #     # batch_request.print_batch_tasks_user_prompts()
    #     # print(f"SYSTEM PROMPT= {batch_request.get_system_prompt()}\n\n")

    # save_batch_requests(batch_requests)
    pass