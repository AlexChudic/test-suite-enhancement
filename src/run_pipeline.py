import src.evaluation as ev
import src.utility_functions as utility
import src.use_gpt_in_batches as use_gpt
from src.batch_request import BatchRequest
from src.evaluation_entry import EvaluationEntry
import tmp.correctness_evaluation as correctness_evaluation
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
        utility.copy_python_files(f"data/{project_name}/tests/{test_source}", f"tmp/{project_name}/tests/{test_source}")
        ev.evaluate_project_directory(project_name, identifiers={"ctx": "initial", "test_source": test_source, "target": "full_repository"})
        ev.evaluate_project_directory(project_name, identifiers={"ctx": "initial", "test_source": test_source, "target": "tests"}, directory_path=f"tests/{test_source}")
        utility.delete_python_files(f"tmp/{project_name}/tests/{test_source}")
        utility.delete_repository(f"tmp/{project_name}/tests/{test_source}")
        
        
def run_specific_project_evaluation(project_name, ctx):
    print(f"Running specific evaluations for project: {project_name}\n")

    if ctx["test_source"]:
        utility.copy_python_files(f"data/{project_name}/tests/{ctx['test_source']}", f"tmp/{project_name}/tests/{ctx['test_source']}")

    if ctx["target"] == "tests":
        ev.evaluate_project_directory(project_name, identifiers=ctx, directory_path=f"tests/{ctx['test_source']}")
    else:  
        ev.evaluate_project_directory(project_name, identifiers=ctx)

    if ctx["test_source"]:
        utility.delete_python_files(f"tmp/{project_name}/tests/{ctx['test_source']}")
        utility.delete_repository(f"tmp/{project_name}/tests/{ctx['test_source']}")


def ensure_initial_test_suite_correctness(project_name, test_source):
    """Ensure the initial test suite is correct - if not, apply rule-based repair"""
    test_suite_path = f"data/{project_name}/tests/{test_source}"
    res = correctness_evaluation.evaluate_functional_correctness(test_suite_path)

    with open(f"data/{project_name}/tests/{test_source}/correctness_evaluation.json", "w") as file:
        json.dump(res, file, indent=4)
    
    return res


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

    sources = ["human_written"]#, "pynguin", "chatgpt"]
    example_selection_modes = ["random_from_all"]#, "random_from_class_under_test", "problem_similarity", "class_similarity_no_definition", 
                               #"class_similarity_with_definition", "problem_and_class_similarity"]
    num_test_cases = [1, 3, 5]

    for test_source in sources:
        # Copy the test files to a temporary directory
        utility.copy_python_files(f"data/{project_name}/tests/{test_source}", f"tmp/{project_name}/tests/{test_source}")

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
                        f"tmp/{project_name}/tests/{test_source}",
                        None,
                        client,
                        identifiers
                    )
                    new_batch_request.continue_processing(submit_job=False) # Change to True when everything is ready!
                    batch_requests.append(new_batch_request)
                    use_gpt.save_batch_requests(batch_requests)
                else:
                    batch.continue_processing(submit_job=True)
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
                    use_gpt.save_batch_requests(batch_requests)

                # If batch is processed, run the specific project evaluation
                if processed:
                    print("Evaluating the batch request... " + str(batch.batch_id))
                    eval_entry = EvaluationEntry.get_eval_entry(batch.batch_id, project_name)
                    if eval_entry:
                        eval_entry.run_evaluation()
                        eval_entry.save()
                    else:
                        eval_data = {
                            "corruption_data" : batch.get_corrupted_output_data()
                        }
                        eval_entry = EvaluationEntry(
                            batch.batch_id,
                            identifiers,
                            eval_data
                        )
                        eval_entry.run_evaluation()
                        eval_entry.save()
        
        # Clear the temporary directory
        utility.delete_python_files(f"tmp/{project_name}/tests/{test_source}")
        utility.delete_repository(f"tmp/{project_name}/tests/{test_source}")
                        

if __name__ == "__main__":
    # run_specific_project_evaluation("human-eval", {"ctx": "initial", "test_source": "human-written", "target": "full_repository"})

    # ensure_initial_test_suite_correctness("human-eval", "pynguin")

    run_full_pipeline("human_eval")
