import evaluation as ev
import utility_functions as uf
import use_gpt_in_batches as use_gpt
from batch_request import BatchRequest
from evaluation_entry import EvaluationEntry
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

def run_pipeline(project_name):
    # Get the project evaluation metrics
    ev.evaluate_project_directory(project_name)


def run_initial_project_evaluations(project_name):
    print(f"Running initial evaluations for project: {project_name}\n")
    ev.evaluate_project_directory(project_name, identifiers={"ctx": "initial"})
    
    for test_source in ["human-written", "pynguin", "chatgpt"]:
        print(f"Running initial evaluations for project: {project_name} with test source: {test_source}\n")
        uf.copy_python_files(f"data/{project_name}/tests/{test_source}", f"tmp/{project_name}/tests/{test_source}")
        ev.evaluate_project_directory(project_name, identifiers={"ctx": "initial", "test_source": test_source, "target": "full_repository"})
        ev.evaluate_project_directory(project_name, identifiers={"ctx": "initial", "test_source": test_source, "target": "tests"}, directory_path=f"tests/{test_source}")
        uf.delete_python_files(f"tmp/{project_name}/tests/{test_source}")
        uf.delete_repository(f"tmp/{project_name}/tests/{test_source}")
        
        
def run_specific_project_evaluation(project_name, ctx):
    print(f"Running specific evaluations for project: {project_name}\n")

    if ctx["test_source"]:
        uf.copy_python_files(f"data/{project_name}/tests/{ctx['test_source']}", f"tmp/{project_name}/tests/{ctx['test_source']}")

    if ctx["target"] == "tests":
        ev.evaluate_project_directory(project_name, identifiers=ctx, directory_path=f"tests/{ctx['test_source']}")
    else:  
        ev.evaluate_project_directory(project_name, identifiers=ctx)

    if ctx["test_source"]:
        uf.delete_python_files(f"tmp/{project_name}/tests/{ctx['test_source']}")
        uf.delete_repository(f"tmp/{project_name}/tests/{ctx['test_source']}")


def run_single_eval_setting():
    # STEP 1: Run the test correctness evaluation
        # Ensure the tests are working correctly
        # Apply Rule-based repair if not
        # Ensure the tests improve the coverage
    # STEP 2: Run the initial project evaluations - using the example tests only
        # Evaluate full project to get code coverage
        # Evaluate test directory to get code quality metrics
    # STEP 3: Run the specific project evaluation - with the enhanced test suite
        # Evaluate full project to get code coverage
        # Evaluate test directory to get code quality metrics
    # STEP 4: Save the eval_entry to the JSON file
    pass


def run_full_pipeline(project_name):
    client = OpenAI()
    batch_requests = use_gpt.load_batch_requests(client)

    sources = ["human-written", "pynguin", "chatgpt"]
    example_selection_modes = ["random_from_all", "random_from_class_under_test", "problem_similarity", "class_similarity_no_definition", 
                               "class_similarity_with_definition", "problem_and_class_similarity"]
    num_test_cases = [1, 3, 5]

    for test_source in sources:
        for example_selection_mode in example_selection_modes:
            for num_test_case in num_test_cases:
                identifiers = {
                    "project_name": project_name,
                    "job_type" : "fewshot_test_suite_enhancement",
                    "test_source":test_source,
                    "test_selection_mode": example_selection_mode,
                    "num_test_cases": num_test_case,
                    "model_name": "gpt-4o-mini",
                    "temperature": 0
                }

                # Check if the batch request is processed - if not, continue processing
                processed = False
                batch = use_gpt.get_batch_request(identifiers, batch_requests)
                if not batch:
                    # If batch does not exist, create a new one
                    new_batch_request = BatchRequest(
                        f"data/{project_name}/tests/{test_source}/enhanced/",
                        f"data/{project_name}/tests/{test_source}",
                        None,
                        client,
                        identifiers
                    )

                    batch_requests.continue_processing(submit_job=False) # Change to True when everything is ready!
                    batch_requests.append(new_batch_request)
                    use_gpt.save_batch_requests(batch_requests)
                else:
                    batch_status = batch.check_status()
                    
                    # If the batch is completed, continue processing - extract the results
                    if batch_status == "completed":
                        batch.continue_processing()
                        batch_status = batch.check_status()

                    # If the batch is processed, we can continue with evaluation
                    if batch_status == "processed":
                        processed = True

                    else:
                        print(f"Batch request is not processed yet. Status: {batch_status}")

                # If batch is processed, run the specific project evaluation
                if processed:
                    eval_entry = EvaluationEntry.get_eval_entry(batch.batch_id, project_name)
                    if eval_entry:
                        continue
                    else:
                        pass
                        

if __name__ == "__main__":
    run_specific_project_evaluation("human-eval", {"ctx": "initial", "test_source": "human-written", "target": "full_repository"})
