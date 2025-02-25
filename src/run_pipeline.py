import evaluation as ev
import utility_functions as uf
import os

def run_pipeline(project_name):
    # Get the project evaluation metrics
    ev.evaluate_project_directory(project_name)




if __name__ == "__main__":
    run_pipeline("human-eval")
