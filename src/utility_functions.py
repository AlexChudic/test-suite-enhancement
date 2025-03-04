import os
import shutil

def copy_python_files(input_path: str, copy_path: str):
    """
    Copies all .py files from the input_path directory to the copy_path directory.
    
    :param input_path: Source directory containing .py files.
    :param copy_path: Destination directory where .py files will be copied.
    """
    if not os.path.exists(copy_path):
        os.makedirs(copy_path)
    
    for file in os.listdir(input_path):
        full_file_path = os.path.join(input_path, file)
        if os.path.isfile(full_file_path) and file.endswith(".py"):
            shutil.copy(full_file_path, copy_path)


def delete_python_files(target_path: str):
    """
    Deletes all .py files in the specified directory.
    
    :param target_path: Directory from which .py files will be deleted.
    """
    for file in os.listdir(target_path):
        full_file_path = os.path.join(target_path, file)
        if os.path.isfile(full_file_path) and file.endswith(".py"):
            os.remove(full_file_path)

def delete_repository(target_path):
    """Deletes the specified directory if it exists"""
    if os.path.exists(target_path):
        os.rmdir(target_path)

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

def choose_fewshot_example_test_cases(selection_mode, test_dir, num_test_cases=1):
    if selection_mode == "random":
        return choose_random_test_cases(test_dir, num_test_cases)
    elif selection_mode == "problem_similarity":
        return choose_similar_test_cases(test_dir, num_test_cases)
    elif selection_mode == "diversity":
        return choose_diverse_test_cases(test_dir, num_test_cases)
        
def choose_random_test_cases():
    pass

def choose_similar_test_cases():
    pass

def choose_diverse_test_cases():
    pass

if __name__ == "__main__":
    copy_python_files("data/human-eval/tests/chatgpt", "tmp/human-eval/tests/chatgpt")

