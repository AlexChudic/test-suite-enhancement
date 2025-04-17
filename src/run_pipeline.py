import src.evaluation as ev
import src.utility_functions as uf
import src.use_gpt_in_batches as use_gpt
from src.batch_request import BatchRequest
from src.evaluation_entry import EvaluationEntry
import tmp.correctness_evaluation as correctness_evaluation
import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

def ensure_initial_test_suite_correctness(project_name, test_source):
    """Ensure the initial test suite is correct - if not, apply rule-based repair"""
    uf.copy_python_files(f"data/{project_name}/tests/{test_source}", f"tmp/{project_name}/tests/{test_source}")

    test_suite_path = f"tmp/{project_name}/tests/{test_source}/"
    res = correctness_evaluation.evaluate_functional_correctness(test_suite_path)

    uf.copy_python_files(f"tmp/{project_name}/tests/{test_source}", f"data/{project_name}/tests/{test_source}")
    uf.delete_python_files(f"tmp/{project_name}/tests/{test_source}")
    uf.delete_repository(f"tmp/{project_name}/tests/{test_source}")

    with open(f"data/{project_name}/tests/{test_source}/correctness_evaluation.json", "w") as file:
        json.dump(res, file, indent=4)
    
    return res


def run_initial_project_evaluations(project_name, redo=False):
    print(f"Running initial evaluations for project: {project_name}\n")
    
    for test_source in ["human_written", "pynguin", "chatgpt"]:
        if EvaluationEntry.get_initial_eval_entry_by_test_source(test_source, project_name) and not redo:
            print(f"Evaluation entry already exists for {test_source}. Skipping initial evaluation.")
            continue

        eval_metrics = {}
        
        # Get the correctness metrics from the json file
        correctness_metrics_path = f"data/{project_name}/tests/{test_source}/correctness_evaluation.json" 
        
        if not os.path.exists(correctness_metrics_path):
            print(f"Correctness metrics file not found for {test_source}. Skipping initial evaluation.")
            continue
        
        with open(correctness_metrics_path, "r") as file:
            correctness_metrics = json.load(file)
            eval_metrics["correctness_evaluation"] = correctness_metrics

        # Perform the test suite evaluation
        print(f"Running initial evaluations for project: {project_name} with test source: {test_source}\n")
        uf.copy_python_files(f"data/{project_name}/tests/{test_source}", f"tmp/{project_name}/tests/{test_source}")

        # First evaluate the full project to get code coverage
        project_eval_metrics = ev.evaluate_project_directory(project_name)
        eval_metrics["enhanced_project_evaluation"] = project_eval_metrics
        print(f"Project evaluation metrics:\n{project_eval_metrics}")

        # Then evaluate the test directory to get code quality metrics
        test_eval_metrics = ev.evaluate_project_directory(project_name, directory_path=f"tests/{test_source}")
        eval_metrics["enhanced_test_evaluation"] = test_eval_metrics
        print(f"Test evaluation metrics:\n{test_eval_metrics}")
        
        uf.delete_python_files(f"tmp/{project_name}/tests/{test_source}")
        uf.delete_repository(f"tmp/{project_name}/tests/{test_source}")

        # Save the evaluation metrics to a EvaluationEntry
        identifiers = {
            "project_name": project_name,
            "job_type" : "initial_test_suite_evaluation",
            "test_source": test_source,
        }
        eval_entry = EvaluationEntry(
            batch_id="",
            type="initial",
            identifiers=identifiers,
            eval_data=eval_metrics,
            status="evaluated"
        )
        eval_entry.save()
        print(f"Initial evaluation for {test_source} completed.\n")


def rerun_enhanced_evaluation(project_name, eval_id=None):
    eval_entries = EvaluationEntry.load_all("enhanced", project_name)
    for eval_entry in eval_entries:
        if eval_id:
            if eval_entry.eval_id != eval_id:
                continue
            branch_coverage = float(eval_entry.eval_data["enhanced_project_evaluation"]["branch_coverage"])
            
            print(f"Rerunning enhanced evaluation for {eval_entry.eval_id}...")
            print(f"Branch coverage = {branch_coverage}")
            eval_entry.status = "corrected"
            eval_entry.run_enhanced_evaluation()
            eval_entry.run_test_suite_optimization()
            eval_entry.run_optimised_evaluation()
        else: # else rerun all without execution_duration
            if "enhanced_project_evaluation" in eval_entry.eval_data and "branch_coverage" in eval_entry.eval_data["enhanced_project_evaluation"]:
                branch_coverage = float(eval_entry.eval_data["enhanced_project_evaluation"]["branch_coverage"])
                if branch_coverage < 0.5:
                    # if eval_entry.eval_id != "4/human_written/random_from_class_under_test/3":
                    #     continue
                    print(f"Rerunning enhanced evaluation for {eval_entry.eval_id}...")
                    print(f"Branch coverage = {branch_coverage}")
                    eval_entry.status = "corrected"
                    eval_entry.run_enhanced_evaluation()
                    eval_entry.run_test_suite_optimization()
                    eval_entry.run_optimised_evaluation()


def redo_evaluation(project_name, eval_id):
    eval_entry = EvaluationEntry.get_eval_entry_by_eval_id(eval_id, "enhanced", "human_eval")
    eval_entry.redo_evaluation()

    # Rerun the evaluation with the settings
    settings = {
        "test_source": eval_entry.identifiers["test_source"],
        "example_selection_mode": eval_entry.identifiers["test_selection_mode"],
        "num_test_cases": eval_entry.identifiers["num_test_cases"]
    }
    run_full_pipeline(project_name, test_settings=settings)


def run_full_pipeline(project_name, test_settings=None):
    client = OpenAI()
    batch_requests = use_gpt.load_batch_requests(client)

    if test_settings:
        sources = [ test_settings["test_source"] ]
        example_selection_modes = [ test_settings["example_selection_mode"] ]
        num_test_cases = [ test_settings["num_test_cases"] ]
    else:
        sources = ["human_written", "pynguin", "chatgpt"]
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
                    identifier_string = uf.generate_identifier_string(identifiers)
                    new_batch_request = BatchRequest(
                        f"data/{project_name}/tests/{test_source}/enhanced/{identifier_string}",
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
                        print(f"INFO: Batch request is not processed yet. Status: {batch_status}")
                    use_gpt.save_batch_requests(batch_requests)

                # If batch is processed, run the specific project evaluation
                if processed:
                    print("Evaluating the batch request... " + str(batch.batch_id))
                    eval_entry = EvaluationEntry.get_eval_entry(batch.batch_id, "enhanced", project_name)
                    if eval_entry:
                        # initial means that the batch request is not evaluated yet
                        if eval_entry.status == "initial":
                            eval_entry.run_correctness_evaluation()
                            eval_entry.run_enhanced_evaluation()
                            eval_entry.run_test_suite_optimization()
                            eval_entry.run_optimised_evaluation()
                        
                        # redo_evaluation is used when we want to re-evaluate the batch request
                        elif eval_entry.status == "redo_evaluation":
                            eval_entry.eval_data["corruption_data"] = batch.get_corrupted_output_data()
                            eval_entry.status = "initial"
                            eval_entry.run_correctness_evaluation()
                            eval_entry.run_enhanced_evaluation()
                            eval_entry.status = "finalised"
                            eval_entry.save()
                        
                        # corrected means that run_correctness_evaluation has been run, but we need to evaluate the enhanced test suite
                        elif eval_entry.status == "corrected":
                            eval_entry.run_enhanced_evaluation()
                            eval_entry.run_test_suite_optimization()
                            eval_entry.run_optimised_evaluation()
                            
                        elif eval_entry.status == "evaluated":
                            eval_entry.run_test_suite_optimization()
                            eval_entry.run_optimised_evaluation()
                        elif eval_entry.status == "optimized":
                            eval_entry.run_optimised_evaluation()
                        else: # eval_entry.status == "finalised":  
                            pass
                    else:
                        eval_data = {
                            "corruption_data" : batch.get_corrupted_output_data()
                        }
                        eval_entry = EvaluationEntry(
                            batch.batch_id,
                            "enhanced",
                            identifiers,
                            eval_data
                        )
                        eval_entry.run_correctness_evaluation()
                        eval_entry.run_enhanced_evaluation()
                        

if __name__ == "__main__":

    if len(sys.argv) == 3:
        project_name = sys.argv[1]
        command = sys.argv[2]

        if command not in ["initial_evaluation", "run_full_pipeline"]:
            print("Invalid command. Use 'initial_correctness' or 'run_full_pipeline'.")
            sys.exit(1)

        elif command == "initial_evaluation":
            for test_source in ["human_written", "pynguin"]:#, "chatgpt"]:
                if not os.path.exists(f"data/{project_name}/tests/{test_source}/correctness_evaluation.json"):
                    print(f"Correctness metrics file not found for {test_source}. Running initial correctness evaluation..")
                    ensure_initial_test_suite_correctness(project_name, test_source)

            # Run the initial project evaluations
            run_initial_project_evaluations(project_name)

        elif command == "run_full_pipeline":
            # Ensure the initial test suite is correct - if not, apply rule-based repair
            for test_source in ["human_written", "pynguin", "chatgpt"]:
                if not os.path.exists(f"data/{project_name}/tests/{test_source}/correctness_evaluation.json"):
                    print(f"Correctness metrics file not found for {test_source}. Running initial correctness evaluation..")
                    ensure_initial_test_suite_correctness(project_name, test_source)

            # Run the initial project evaluations
            run_initial_project_evaluations(project_name)

            # Run the full pipeline for the project
            run_full_pipeline(project_name)

    elif len(sys.argv) != 1:
        print("Usage: python script.py <project_name> <command>")
        print("Commands: initial_correctness, run_full_pipeline")
        sys.exit(1)

    else:
        run_full_pipeline("human_eval")

        # data_test_path = f"data/human_eval/tests/human_written/enhanced/human_written_random_from_all_5/"
        # tmp_test_path = f"tmp/human_eval/tests/human_written/"
        # uf.copy_python_files(data_test_path, tmp_test_path)

        eval_ids = [
            "23/pynguin/random_from_class_under_test/5",
        ]
        # for eval_id in eval_ids:
        #     redo_evaluation('human_eval', eval_id)
            # continue_evaluation(eval_id)

        # rerun_enhanced_evaluation("human_eval")
