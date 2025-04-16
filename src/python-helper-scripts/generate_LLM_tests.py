import os
import subprocess
import sys
from openai import OpenAI
import src.use_gpt_in_batches as use_gpt
from src.batch_request import BatchRequest
from dotenv import load_dotenv

# Define the prompt for generating initial unit test cases
generate_initial_unit_tests_system_prompt = '''
Your goal is to generate unit tests for a python class using the pytest framework. You will be provided with the class definition, and you will output a list of unit test.
The unit tests should cover the most important methods of the class, reaching a minimum of 80% code coverage.
Make sure to keep the tests simple and easy to understand. The output should only include the test classes.
'''

def generate_LLM_files(project_name):
    project_class_directory = f"tmp/{project_name}"
    output_path = f"data/{project_name}/tests/chatgpt"
    client = OpenAI()

    identifiers = {
        "project_name": project_name,
        "job_type" : "initial_test_suite_generation",
        "test_source": "chatgpt",
        "model_name": "gpt-4o-mini",
        "temperature": 0
    }

    # Check if the batch request already exists 
    batch_requests = use_gpt.load_batch_requests(client)
    batch_request = use_gpt.get_batch_request(identifiers, batch_requests)
    if batch_request:
        print(f"Batch request already exists, status={batch_request.status}")
        print(f"Continue processing the batch request..")
        batch_request.continue_processing(submit_job=True)
        use_gpt.save_batch_requests(batch_requests)
    else:
        # Create a new batch request
        new_batch_request = BatchRequest(
            output_path,
            f"tmp/{project_name}",
            generate_initial_unit_tests_system_prompt,
            client,
            identifiers
        )
        new_batch_request.continue_processing(submit_job=True)
        batch_requests.append(new_batch_request)
        use_gpt.save_batch_requests(batch_requests)

if __name__ == "__main__":
    package_path = "tmp/package.txt"

    if len(sys.argv) == 2:        
        project_name = sys.argv[1]

        # Run the function with the provided paths
        generate_LLM_files(project_name)

    elif len(sys.argv) == 1:
        print("No arguments provided. Using default paths.")

        # Define paths
        project_name = "classeval"

        # Run the function with the default paths
        generate_LLM_files(project_name)
    else:
        print("Usage: python script.py <project_name>")
        sys.exit(1)

    