import requests
import time
import json
import subprocess
import os
import base64
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

def evaluate_repository():
    """Evaluates a repository using the SonarQube API."""
    
    # SonarQube API endpoint
    task_url = execute_script()

    # Wait for the task to finish
    wait_for_task_to_finish(task_url)

    # TODO: Add further evaluation logic


def execute_script():
    """Executes a script to evaluate a repository."""

    # Command to execute
    command = ["/bin/bash", "tmp/evaluate-repository.sh", "human-eval/", "sqp_b1741b6c1c9829f4acb358b78273e95ae35b58a9"]

    try:
        # Run the command and capture the output
        print("Running the evaluation script...")
        result = subprocess.run(command, check=True, text=True, capture_output=True)

        # Print the output of the command
        print("Evaluation script executed successfully!")
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


if __name__ == "__main__":
    evaluate_repository()
