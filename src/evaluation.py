import requests
import time
import json
import subprocess
import os
import base64
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

def evaluate_directory(directory_path=None):
    """Evaluates a repository using the SonarQube API."""
    
    sonar_project_name = os.getenv("SONAR_PROJECT_NAME")
    if not sonar_project_name:
        raise ValueError("SONAR_PROJECT_NAME is not set in environment variables.")

    # Run test suite evaluation
    evaluate_test_suite()

    # Run SonarQube evaluation
    task_url = execute_sonarqube_evaluation()

    # Wait for the task to finish
    wait_for_task_to_finish(task_url)

    # Retrieve the measures from SonarQube
    if directory_path:
        directory = "%3A" + directory_path.replace("/", "%2F")
    else:
        directory = ""
    sonar_qube_url = (f"http://localhost:9000/api/measures/component?component={sonar_project_name}{directory}" 
                      "&metricKeys=code_smells%2Cnew_code_smells%2Clines%2Cnew_lines%2Cncloc%2Cbugs%2Cnew_bugs%2C"
                      "vulnerabilities%2Cnew_vulnerabilities%2Cnew_maintainability_rating%2Csqale_index%2Ccomplexity%2C"
                      "cognitive_complexity%2Ccomment_lines")
    sonar_qube_result = make_get_request(sonar_qube_url)
    
    # Print and return the result
    print("SonarQube Result:\n" + sonar_qube_result)
    return sonar_qube_result


def execute_sonarqube_evaluation():
    """Executes a script to evaluate a repository."""

    sonar_token = os.getenv("SONAR_TOKEN")
    if not sonar_token:
        raise ValueError("SONAR_TOKEN is not set in environment variables.")

    print(sonar_token)
    # Command to execute
    command = ["/bin/bash", "src/bash-scripts/evaluate-repository.sh", "tmp/human-eval/", sonar_token]
    
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


def evaluate_test_suite():
    """Evaluates the test suite of a repository."""

    # Command to execute
    command = ["/bin/bash", "src/bash-scripts/evaluate-test-suite.sh" ]

    try:
        # Run the command and capture the output
        print("Running the evaluate-test-suite.sh script...")
        result = subprocess.run(command, check=True, text=True, capture_output=True)

        # Print the output of the command
        print("Test suite evaluation script executed successfully!")

    except subprocess.CalledProcessError as e:
        # Print error details if the command fails
        print("Error executing command.")
        print("Exit Code:", e.returncode)
        print("Error Output:\n", e.stderr)


if __name__ == "__main__":
    evaluate_directory()
