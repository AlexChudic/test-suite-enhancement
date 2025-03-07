import evaluation as ev
import utility_functions as uf
import os


def run_pipeline(project_name):
    # Get the project evaluation metrics
    ev.evaluate_project_directory(project_name)


def run_initial_project_evaluations(project_name):
    print(f"Running initial evaluations for project: {project_name}\n")
    ev.evaluate_project_directory(project_name, identifiers={"settings": "initial"})
    
    for test_source in ["human-written", "pynguin", "chatgpt"]:
        print(f"Running initial evaluations for project: {project_name} with test source: {test_source}\n")
        uf.copy_python_files(f"data/{project_name}/tests/{test_source}", f"tmp/{project_name}/tests/{test_source}")
        ev.evaluate_project_directory(project_name, identifiers={"settings": "initial", "test_source": test_source, "target": "full_repository"})
        ev.evaluate_project_directory(project_name, identifiers={"settings": "initial", "test_source": test_source, "target": "tests"}, directory_path=f"tests/{test_source}")
        uf.delete_python_files(f"tmp/{project_name}/tests/{test_source}")
        uf.delete_repository(f"tmp/{project_name}/tests/{test_source}")
        
        
def run_specific_project_evaluation(project_name, settings):
    print(f"Running specific evaluations for project: {project_name}\n")

    if settings["test_source"]:
        uf.copy_python_files(f"data/{project_name}/tests/{settings['test_source']}", f"tmp/{project_name}/tests/{settings['test_source']}")

    if settings["target"] == "tests":
        ev.evaluate_project_directory(project_name, identifiers=settings, directory_path=f"tests/{settings['test_source']}")
    else:  
        ev.evaluate_project_directory(project_name, identifiers=settings)

    if settings["test_source"]:
        uf.delete_python_files(f"tmp/{project_name}/tests/{settings['test_source']}")
        uf.delete_repository(f"tmp/{project_name}/tests/{settings['test_source']}")


if __name__ == "__main__":
    run_specific_project_evaluation("human-eval", {"settings": "initial", "test_source": "human-written", "target": "full_repository"})
