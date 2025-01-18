import json
from openai import OpenAI
import pandas as pd
from dotenv import load_dotenv
import os

dataset_path = 'tmp/human-eval'
test_path = 'tmp/human-eval-tests/chatgpt'

# Load the environment variables
load_dotenv(override=True)

# Initialize a connection to the OpenAI API
client = OpenAI()

# Define the prompt for generating initial unit test cases
generate_initial_unit_tests_system_prompt = '''
Your goal is to generate unit tests for a python class. You will be provided with the class definition, and you will output a list of unit test.
The unit tests should cover the most important methods of the class, reaching a minimum of 80% code coverage.
Make sure to keep the tests simple and easy to understand. The output should only include the test classes.
'''

def file_to_multiline_string(file_path):
    """Reads a Python file and converts its content into a multiline string."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        multiline_string = '"""\n' + content + '\n"""'
        return multiline_string
    except FileNotFoundError:
        return f"Error: The file at {file_path} was not found."
    except Exception as e:
        return f"An error occurred: {e}"


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


def save_chatgpt_output_to_file(output: str, output_path: str, file_name: str):
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


def get_initial_test_cases_batch(dataset_path):
    python_files = [f for f in os.listdir(dataset_path) if f.endswith(".py")]
    for file in python_files[:1]:
        file_path = os.path.join(dataset_path, file)
        print(f"Processing file: {file_path}")
        file_content = file_to_multiline_string(file_path)
        response = get_initial_test_cases(file_content)
        print(f"File {file_path} response:")
        print(response)
        save_chatgpt_output_to_file(response, test_path, f"test_{file.split('.')[0]}.py")
    return response

get_initial_test_cases_batch(dataset_path)