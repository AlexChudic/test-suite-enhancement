import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import utility_functions as uf

# Setting up the variables
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

def get_initial_test_cases(class_unter_test):
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0.1,
    # response_format="json_object",
    messages=[
        {
            "role": "system",
            "content": generate_initial_unit_tests_system_prompt
        },
        {
            "role": "user",
            "content": class_unter_test
        }
    ],
    )
    return response.choices[0].message.content


def save_chatgpt_output_to_file(output, output_path, file_name):
    """
    Saves the Python code from a ChatGPT output to a .py file
    Dynamically finds the start and end of the code block marked by ```python and ```
    """
    try:
        # Find the start and end indices of the Python code block
        start_index = output.index("```python") + len("```python")
        end_index = output.index("```", start_index)
        
        cleaned_output = output[start_index:end_index].strip()
        
        # Error handling
        if not cleaned_output:
            raise ValueError("Invalid structure: No valid Python code found in the output.")
        
        if not file_name.endswith(".py"):
            raise ValueError("File name must end with .py extension.")
        
        if not os.path.isdir(output_path):
            raise ValueError(f"Invalid output path: {output_path} does not exist or is not a directory.")
        
        full_file_path = os.path.join(output_path, file_name)

        # Save the cleaned output to the file
        with open(full_file_path, "w") as file:
            file.write(cleaned_output)
        
        print(f"Output successfully saved to {file_name}")
    
    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"An error occurred while saving the file: {e}")


def get_initial_test_cases_batch(dataset_path, output_path=BATCH_OUTPUT_DIR):
    python_files = [f for f in os.listdir(dataset_path) if f.endswith(".py")]
    for file in python_files[:1]:
        file_path = os.path.join(dataset_path, file)
        print(f"Processing file: {file_path}")
        file_content = uf.file_to_multiline_string(file_path)
        response = get_initial_test_cases(file_content)
        print(f"File {file_path} response:")
        print(response)
        save_chatgpt_output_to_file(response, output_path, f"test_{file.split('.')[0]}.py")
    return response


def create_batch_jsonl_file(dataset_path, batch_json_path, model_name=MODEL_NAME, temperature=TEMPERATURE):
    """Generate a batch JSONL file with prompts from the input dataset."""
    python_files = [f for f in os.listdir(dataset_path) if f.endswith(".py")]
    tasks = []

    for file in python_files:
        custom_id = file.split('.')[0]
        file_path = os.path.join(dataset_path, file)
        file_content = uf.file_to_multiline_string(file_path)
        
        request = {
            "custom_id" : custom_id,
            "method" : "POST",
            "url" : "/v1/chat/completions",
            "body" : {
                "messages": [
                    {"role": "system", "content": generate_initial_unit_tests_system_prompt},
                    {"role": "user", "content": file_content}
                ],
                "model": model_name,
                "temperature": temperature
            }
        }
        tasks.append(request)

    with open(batch_json_path, "w") as file:
        for task in tasks:
            file.write(json.dumps(task) + "\n")
    print("The batch JSONL file has been successfully created.")


def submit_batch_job(batch_file_path):
    """Submits the batch job to OpenAI"""
    batch_file = client.files.create(
        file=open(batch_file_path, "rb"),
        purpose="batch"
    )
    print(f"Batch file uploaded with id: {batch_file.id}")
    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    return batch_job.id


def save_batch_id_to_file(batch_id, output_path):
    """Save the batch ID to a file for future reference"""
    with open(os.path.join(output_path, "batch_id.txt"), "w") as file:
        file.write(batch_id)
        print(f"Batch ID ({batch_id}) saved to {output_path}/batch_id.txt")


def load_batch_id_from_file(output_path):
    """Load the batch ID from the file"""
    if not os.path.exists(os.path.join(output_path, "batch_id.txt")):
        return None
    else:
        with open(os.path.join(output_path, "batch_id.txt"), "r") as file:
            return file.read().strip()


def process_batch_results(batch_job, batch_output_dir):
    """Fetches and processes batch results"""
    
    result_json_path = os.path.join(batch_output_dir, "batch_results.jsonl")

    # Download the results if they don't exist
    if not os.path.exists(result_json_path):
        result = client.files.content(batch_job.output_file_id).content
        with open(result_json_path, "w") as file:
            file.write(result)
        print(f"Batch results saved to {result_json_path}")

    else:
        print ("Results already exist, skipping download")

    results = []
    with open(result_json_path, "r") as file:
        for line in file:
            json_object = json.load(line.strip())
            results.append(json_object)
    
    print(results[0])

    # for item in result.data:
    #     response_content = item["choices"][0]["message"]["content"]
    #     file_name = f"test_{item['id']}.py"  # Naming based on request ID
    #     save_chatgpt_output_to_file(response_content, batch_output_dir, file_name)


def get_initial_test_cases_batch(dataset_path):
    """Main function to execute batch processing workflow"""

    batch_id = load_batch_id_from_file(BATCH_OUTPUT_DIR)
    batch_json_path = os.path.join(BATCH_OUTPUT_DIR, BATCH_JSON_NAME)
    if batch_id:
        print(f"A batch job is already in progress with batch_id={batch_id}. Checking for results...")

    else:
        print("Creating JSONL file for batch processing...")
        create_batch_jsonl_file(dataset_path, batch_json_path)
    
        print(f"Submitting batch job at {batch_json_path}...")
        batch_id = submit_batch_job(batch_json_path)
        print(f"Batch job submitted with ID: {batch_id}")

        save_batch_id_to_file(batch_id, BATCH_OUTPUT_DIR)
    
    batch_job = client.batches.retrieve(batch_id)
    
    if batch_job.status == "completed":
        print("Batch job completed. Processing results...")
        process_batch_results(batch_job, BATCH_OUTPUT_DIR)
    elif batch_job.status == "cancelled" or batch_job.status == "failed":
        print(f"Batch job failed with status: {batch_job.status}")

    else:
        print("Batch job is still in progress. Please check back later.")
        print(f"Requests completed: {batch_job.request_counts.completed}/{batch_job.request_counts.total}")
        print(f"Requests failed: {batch_job.request_counts.failed}")



if __name__ == "__main__":
    get_initial_test_cases_batch(INPUT_DATASET_PATH)