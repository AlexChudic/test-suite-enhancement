import requests
import time
import json
import re
import subprocess
import os
import base64
from dotenv import load_dotenv

def evaluate_project_directory(project_name, directory_path=None):
    """Evaluates a repository using the SonarQube API."""
    
    sonar_project_name = os.getenv("SONAR_PROJECT_NAME")
    if not sonar_project_name:
        raise ValueError("SONAR_PROJECT_NAME is not set in environment variables.")

    # Run test suite evaluation
    evaluate_test_suite(project_name)

    # Run SonarQube evaluation
    task_url = execute_sonarqube_evaluation(project_name)

    # Wait for the task to finish
    wait_for_task_to_finish(task_url)

    # Retrieve the measures from SonarQube
    if directory_path:
        directory = "%3A" + directory_path.replace("/", "%2F")
    else:
        directory = ""
    sonar_qube_url = (f"http://localhost:9000/api/measures/component?component={sonar_project_name}{directory}" 
                      "&metricKeys=code_smells%2Cnew_code_smells%2Clines%2Cnew_lines%2Cncloc%2Cbugs%2Cnew_bugs%2C"
                      "vulnerabilities%2Cnew_vulnerabilities%2Cbranch_coverage%2Csqale_index%2Ccomplexity%2C"
                      "cognitive_complexity%2Ccomment_lines%2Clines_to_cover%2Cuncovered_lines%2Ccoverage%2Cline_coverage")
    sonar_qube_result = make_get_request(sonar_qube_url)
    
    formated_results = format_sonarqube_results(sonar_qube_result)

    if not formated_results:
        print("Error retrieving SonarQube results.")
        return None
    else:
        print("SonarQube Result:")
        print(json.dumps(formated_results, indent=4))
        return formated_results


def execute_sonarqube_evaluation(project_name):
    """Executes a script to evaluate a repository."""

    sonar_token = os.getenv("SONAR_TOKEN")
    if not sonar_token:
        raise ValueError("SONAR_TOKEN is not set in environment variables.")

    # Command to execute
    command = ["/bin/bash", "src/bash-scripts/evaluate-repository.sh", "tmp/" + project_name + "/" , sonar_token]

    try:
        # Run the command and capture the output
        print("Running the src/bash-scripts/evaluate-repository.sh script...")
        result = subprocess.run(command, check=True, text=True, capture_output=True)

        # Print the output of the command
        print("Repository evaluation script executed successfully!")
        print("Analysis URL: ", result.stdout)

    except subprocess.CalledProcessError as e:
        # Print error details if the command fails
        print("Error executing command.")
        print("Exit Code:", e.returncode)
        print("Error Output:\n", e.stderr)

    return result.stdout[:-1]


def wait_for_task_to_finish(analysis_url):
    """Waits for a task at the given URL to complete by polling its status."""

    try:
        while True:
            # Make GET request using the helper function
            analysis_task_details = make_get_request(analysis_url)
            if not analysis_task_details:
                print("Failed to retrieve task details.")
                break

            # Extract the analysis state
            analysis_task_details = json.loads(analysis_task_details)
            analysis_state = analysis_task_details.get("task", {}).get("status", "")

            if analysis_state == "FAILED":
                print("Task failed. Details:", json.dumps(analysis_task_details, indent=4))
                break

            if analysis_state not in {"PENDING", "IN_PROGRESS"}:
                print(f"Analysis State: {analysis_state}")
                break

            # If still pending or in progress, wait before polling again
            print(f"Waiting; Analysis State: {analysis_state}")
            time.sleep(1)

    except Exception as e:
        print("Unexpected error:", e)


def make_get_request(url):
    """Makes a GET request to the sonarqube URL with Basic Authentication."""
    try:
        # Load credentials from environment variables
        sonar_user = os.getenv("SONAR_USER")
        sonar_password = os.getenv("SONAR_PASSWORD")

        if not sonar_user or not sonar_password:
            raise ValueError("SONAR_USER or SONAR_PASSWORD not set in environment variables.")

        # Create Basic Authentication header
        credentials = f"{sonar_user}:{sonar_password}"
        basic_auth_header = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {basic_auth_header}"
        }
        
        # Make the GET request
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        return response.text

    except requests.RequestException as e:
        print(f"Error making GET request: {e}")
        return None


def format_sonarqube_results(results):
    """Formats the SonarQube results into a more readable format."""
    
    try:
        data = json.loads(results)
        metrics = {}
        for measure in sorted(data["component"]["measures"], key=lambda m: m["metric"]):
            if "value" in measure:
                metrics[measure["metric"]] = measure["value"]
            elif "period" in measure:
                metrics[measure["metric"]] = measure["period"]["value"]

        # Add the execution duration
        execution_duration = get_execution_duration()
        metrics["execution_duration"] = execution_duration

        return metrics
    except Exception as e:
        print("Error formatting SonarQube results:", e)
        return None


def save_sonarqube_results(results, path):
    """Saves the SonarQube results to a file."""
    # Append to existing file if it exists
    if not os.path.exists(path):
        with open(path, "w") as file:
            json.dump([], file, indent=4)

    with open(path, "r+") as file:
        existing_results = json.load(file)
        existing_results.append(json.loads(results))
        file.seek(0)
        json.dump(existing_results, file, indent=4)

    print("The sonarqube results have been saved to ", path)


def evaluate_test_suite(project_name):
    """Evaluates the test suite of a repository."""

    # Command to execute
    command = ["/bin/bash", "src/bash-scripts/evaluate-test-suite.sh", project_name ]

    try:
        # Run the command and capture the output
        print("Running the evaluate-test-suite.sh script...")
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        # print(result.stdout)

        # Print the output of the command
        print("Test suite evaluation script executed successfully!")

    except subprocess.CalledProcessError as e:
        # Print error details if the command fails
        print("Error executing command.")
        print("Exit Code:", e.returncode)
        print("Error Output:\n", e.stderr)

        
def get_execution_duration():
    """Retrieves the execution duration from tox_output.log file"""
    with open("tmp/tox_output.log", "r") as file:
        lines = file.readlines()
        line = lines[-1]

    # Extract the execution duration from the line
    time = re.search(r"\((\d+\.\d+) seconds\)", line)
    if time:
        execution_duration = time.group(1)
        print("Execution duration:", execution_duration)
        execution_duration = float(execution_duration)
    else:
        print("Execution duration not found in the log file.")
        execution_duration = None
    
    return execution_duration


if __name__ == "__main__":
    evaluate_project_directory("classeval")
