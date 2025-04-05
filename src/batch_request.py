import json
import os
import re
from openai import OpenAI
import src.utility_functions as uf

BATCH_REQUESTS_DIR="data/batch_requests/"

generate_new_test_cases_system_prompt_final = '''
You are an expert in Python test generation using pytest. Your goal is to generate new high-quality unit tests for a given Python class. You will be provided with the class definition and your output should be a list of new unit tests.
The prompt will include EXAMPLES of similar test cases to help you generate well-structured test cases.
Make sure to keep the tests maintainable and easy to understand, while aiming for high code coverage. The output should only include the test classes.
'''

generate_new_test_cases_system_prompt_final_same_class_examples = '''
You are an expert in Python test generation using pytest. Your goal is to generate new high-quality unit tests for a given Python class. You will be provided with the class definition and your output should be a list of new unit tests.
The prompt will include EXAMPLES of existing test classes to help you expand the test suite with well-structured test cases. 
Make sure to keep the tests maintainable and easy to understand, while aiming for high code coverage. The output should only include the test classes.
'''

class BatchRequest:

    def __init__(self, output_path, dataset_path, system_prompt=None, client=None, identifiers={}, batch_id=None, status="initial",
                result_json=None, task_json=None, submit_job=False, is_loaded_form_json=False, corrupted_tests=[], fixed_corrupted_tests=[]):
        """
        Primary constructor
        
        Args:
            client (OpenAI): The OpenAI client object
            identifiers (dict): The identifiers for the batch request
                - project_name (str): The name of the project
                - job_type (str): The type of job to be performed [fewshot_test_suite_enhancement]
                - test_source (str): The source of the test cases [chatgpt/human-written/pynguin]
                - test_selection_mode (str): The mode for selecting test cases [random/class_similarity]
                - num_test_cases (int): The number of test cases to generat
                - model_name (str): The name of the ChatGPT model
                - temperature (float): The temperature parameter for the model [0.0 - 1.0]
            output_path (str): The directory to save the new test cases
            dataset_path (str): The directory containing the initial test suite
            batch_id (str): The ID of the batch job
            status (str): The status of the batch job [initial/submitted/completed/processed]
            submit_job (bool): Whether to submit the batch job
            system_prompt (str): The system prompt for the ChatGPT model
            task_json (str): The path to the task JSONL file
            result_json (str): The path to the result JSONL
            is_loaded_form_json (bool): Whether the batch request is loaded from a JSON file or not
        """
        self.client = client
        self.identifiers = identifiers
        self.output_path = output_path
        self.dataset_path = dataset_path
        self.batch_id = batch_id
        self.status = status
        self.submit_job = submit_job
        self.system_prompt = system_prompt
        self.task_json = task_json
        self.result_json = result_json
        self.corrupted_tests = corrupted_tests
        self.fixed_corrupted_tests = fixed_corrupted_tests
        if not is_loaded_form_json:
            print("NEW Batch request created!")
            print(self.to_json())
        else:
            print(f"Batch request loaded from JSON! Batch ID: {self.batch_id}, Status: {self.check_status()}")
        

    @classmethod
    def from_dict(cls, batch_data: dict, client=None):
        """Alternative constructor for loading from a dictionary file."""
        return cls(
            output_path=batch_data["output_path"],
            dataset_path=batch_data["dataset_path"],
            system_prompt=batch_data["system_prompt"],
            batch_id=batch_data["batch_id"],
            status=batch_data["status"],
            client=client,
            identifiers=batch_data["identifiers"],
            task_json=batch_data["task_json"],
            result_json=batch_data["result_json"],
            submit_job=batch_data["submit_job"],
            corrupted_tests=batch_data["corrupted_tests"],
            fixed_corrupted_tests=batch_data["fixed_corrupted_tests"] if "fixed_corrupted_tests" in batch_data else [],
            is_loaded_form_json=True
        )


    def continue_processing(self, submit_job=False):
        """Check the status of the batch and continue processing it."""
        if self.status == "processed":
            print(f"Batch {self.batch_id} has already been processed.")
        if self.status == "submitted":
            print(f"Batch {self.batch_id} is in state submitted.. Checking the status.")
            self.check_status()

        if self.status == "completed":
            print(f"Batch {self.batch_id} is in state completed.. Processing the results.")
            if not self.result_json:
                print("Downloading the results..")
                self.download_results()
            print("Processing the results..")
            self.process_batch_results()
            print("Results processed.")

        if self.status == "initial":
            if not self.task_json:
                print("Creating the task JSON..")
                self.create_batch_jsonl_file()
            
            if submit_job == True:
                self.submit_job = True
            if self.submit_job:
                print("Submitting the batch job..")
                self.submit_batch_job()
                print("Batch job submitted.")
                self.status = "submitted"

        if self.status == "failed" and self.submit_job:
            print(f"Batch {self.batch_id} has failed. Resubmitting the job.")
            self.submit_batch_job()
            self.status = "submitted"
            print("Batch job submitted.")
            return False
        
    

    def construct_user_prompt(self, file_name):
        """Construct the user prompt for the ChatGPT model."""

        # IF fewshot_test_suite_enhancement, use the class under test in the prompt
        if self.identifiers["job_type"] == "fewshot_test_suite_enhancement":
            mut_name = file_name.removeprefix("test_")
            mut_dir = os.path.join("tmp", self.identifiers["project_name"])
            mut_path = os.path.join(mut_dir, mut_name) 
            mut_content = uf.file_to_multiline_string(mut_path)
            fewshot_example_test_cases = uf.choose_fewshot_example_test_cases(
                self.identifiers["test_selection_mode"],
                self.dataset_path,
                mut_name,
                self.identifiers["num_test_cases"]
            )
            test_cases_content = []
            for test_case in fewshot_example_test_cases:
                if os.path.exists(test_case):
                    test_cases_content.append(uf.get_python_file_content(test_case))
                else:
                    test_cases_content.append(test_case)
            test_cases_content = "\n\n".join(test_cases_content)
            user_prompt = f'''
# CLASS UNDER TEST: {mut_name}
{mut_content}
\n# EXAMPLES:
{test_cases_content}
'''
            return user_prompt
        
        # ELSE use the file content as the prompt - for initial test suite generation
        else:
            file_path = os.path.join(self.dataset_path, file_name)
            file_content = uf.file_to_multiline_string(file_path)
            return file_content


    def create_batch_jsonl_file(self, batch_requests_dir=BATCH_REQUESTS_DIR):
        """Generate a batch JSONL file with prompts from the input dataset."""
        python_files = [f for f in os.listdir(self.dataset_path) if f.endswith(".py")]
        tasks = []

        system_prompt = self.get_system_prompt()

        for file in python_files:
            custom_id = file.split('.')[0]
            user_prompt = self.construct_user_prompt(file)
            
            request = {
                "custom_id" : custom_id,
                "method" : "POST",
                "url" : "/v1/chat/completions",
                "body" : {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "model": self.identifiers["model_name"],
                    "temperature": self.identifiers["temperature"]
                }
            }
            tasks.append(request)

        num_files = len(os.listdir(os.path.join(batch_requests_dir, "batch_task_jsons"))) + 1
        batch_json_path = os.path.join(batch_requests_dir, "batch_task_jsons", f"batch_tasks_{num_files}.jsonl")
        with open(batch_json_path, "w") as file:
            for task in tasks:
                file.write(json.dumps(task) + "\n")
        self.task_json = batch_json_path
        print("The batch JSONL file has been successfully created.")


    def submit_batch_job(self):
        """Submits the batch job to OpenAI."""
        if not self.task_json:
            print("Task JSON has not been created yet.")

        if not self.client:
            print("OpenAI client has not been initialized.")

        if not self.submit_job:
            print("Batch job has not been set to submit.")

        else:
            batch_file = self.client.files.create(
                file=open(self.task_json, "rb"),
                purpose="batch"
            )
            batch_job = self.client.batches.create(
                input_file_id=batch_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            self.batch_id = batch_job.id
            self.status = "submitted"
    

    def check_status(self):
        """Check the status of the batch job."""
        if self.status == "processed":
            return self.status
        if not self.batch_id:
            return self.status
        
        if not self.client:
            print("ERROR: OpenAI client has not been initialized.")
            return self.status
        
        batch_job = self.client.batches.retrieve(self.batch_id)
        self.status = batch_job.status

        if batch_job.status == "in_progress":
            print("Batch job is still in progress. Please check back later.")
            print(f"Requests completed: {batch_job.request_counts.completed}/{batch_job.request_counts.total}")
            print(f"Requests failed: {batch_job.request_counts.failed}")

        return self.status
    

    def get_batch_job(self):
        if not self.status != "initial":
            print("Batch job has not been submitted yet.")
            return None
        
        if not self.client:
            print("OpenAI client has not been initialized.")
            return None
        
        else:        
            return self.client.batches.retrieve(self.batch_id)


    def download_results(self, batch_requests_dir=BATCH_REQUESTS_DIR):
        """Download the batch job results."""
        if self.status != "completed":
            print("Batch job is not yet completed.")

        result_json_path = os.path.join(batch_requests_dir, "batch_result_jsons", f"{self.batch_id}_results.jsonl")
        result = self.client.files.content(self.get_batch_job().output_file_id).content
        with open(result_json_path, "wb") as file:
            file.write(result)

        self.result_json = result_json_path
        print(f"Batch results saved to {result_json_path}")
    

    def process_batch_results(self):
        """Process the batch job results."""
        if self.status != "completed":
            print("Batch job is not yet completed.")

        if not self.result_json:
            print("Batch results have not been downloaded yet.")

        results = []
        with open(self.result_json, "r") as file:
            for line in file:
                json_object = json.loads(line.strip())
                results.append(json_object)
        
        for res in results:
            response_content = res['response']['body']["choices"][0]["message"]["content"]
            self.save_chatgpt_output_to_file(response_content, res['custom_id'])
        
        self.status = "processed"


    def extract_function_name(self, cleaned_output):
        match = re.search(r"assert\s+(\w+)\s*\(", cleaned_output)
        return match.group(1) if match else None


    def save_chatgpt_output_to_file(self, output, module_name):
        """
        Saves the Python code from a ChatGPT output to a .py file
        Dynamically finds the start and end of the code block marked by ```python and ```

        Args:
            output (str): The ChatGPT output containing Python code
            module_name (str): The name of the module under test
        """
        try:
            if module_name.startswith("test_"):
                module_name = module_name.removeprefix("test_")

            # Find the start and end indices of the Python code block
            start_index = output.index("```python") + len("```python")
            if "```" in output[start_index:]:
                end_index = output.index("```", start_index)
                file_name = f"test_{module_name}.py"
                cleaned_output = output[start_index:end_index].strip()
                
                # Error handling
                if not cleaned_output:
                    raise ValueError("Invalid structure: No valid Python code found in the output.")
                
                if not file_name.endswith(".py"):
                    raise ValueError("File name must end with .py extension.")
                
                if not os.path.isdir(self.output_path):
                    os.makedirs(self.output_path)
                
                full_file_path = os.path.join(self.output_path, file_name)

                # Save the cleaned output to the file
                with open(full_file_path, "w") as file:
                    file.write(cleaned_output)
                
                # print(f"Output successfully saved to {file_name}")

            # In case of corrupted LLM output, try fixing it
            else:
                # print("ERROR output:\n" + output[start_index:])
                fixed = self.fix_corrupted_output(output[start_index:], module_name)   
                if not fixed:
                    self.corrupted_tests.append(module_name)
                else:
                    self.fixed_corrupted_tests.append(module_name)
                    # print(f"Output successfully saved to {module_name}.py")
                
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            print(f"An error occurred while saving the file: {e}")


    def fix_corrupted_output(self, output, module_name):
        """Fixes corrupted output by removing the unfinished test case and keeping the rest"""

        fixed_output = uf.remove_last_test_case(output)
        
        if not fixed_output:
            return False
        else:
            file_name = f"test_{module_name}.py"
            full_file_path = os.path.join(self.output_path, file_name)

            # Save the cleaned output to the file
            with open(full_file_path, "w") as file:
                file.write(fixed_output)
            return True


    def get_system_prompt(self):
        if self.system_prompt:
            return self.system_prompt
        elif "test_selection_mode" in self.identifiers and self.identifiers["test_selection_mode"] == "random_from_class_under_test":
            return generate_new_test_cases_system_prompt_final_same_class_examples
        else:
            return generate_new_test_cases_system_prompt_final


    def print_batch_tasks_user_prompts(self):
        """Prints the user prompts for the batch tasks."""
        if not self.task_json:
            print("Task JSON has not been created yet.")
        else:
            with open(self.task_json, "r") as file:
                for line in file:
                    task = json.loads(line)
                    print(task["body"]["messages"][1]["content"])
                    print("\n\n")

    def get_corrupted_output_data(self):
        return {
            "corrupted_output" : len(self.corrupted_tests),
            "fixed_corrupted_output" : len(self.fixed_corrupted_tests)
        }

    def to_json(self):
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "identifiers": self.identifiers,
            "task_json": self.task_json,
            "result_json": self.result_json,
            "output_path": self.output_path,
            "dataset_path": self.dataset_path,
            "system_prompt": self.system_prompt,
            "submit_job": self.submit_job,
            "corrupted_tests": self.corrupted_tests,
            "fixed_corrupted_tests": self.fixed_corrupted_tests
        }
    
    def __str__(self):
        return json.dumps(self.to_json())




