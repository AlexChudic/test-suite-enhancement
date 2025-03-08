import os
import shutil
import random
import ast
from Levenshtein import distance

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

def get_python_file_content(file_path):
    """Reads a Python file and returns its content as a string."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return f"Error: The file at {file_path} was not found."
    except Exception as e:
        return f"An error occurred: {e}"

def extract_test_cases_from_file(file_path):
    """Returns the test cases for the specified class."""
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
        tree = ast.parse(source_code, filename=file_path)

    test_cases = []
    lines = source_code.splitlines()

    def get_source_segment(node):
        """Extract source code of a function including decorators."""
        start_lineno = node.lineno - 1
        end_lineno = node.end_lineno

        # Include decorator lines if present
        while start_lineno > 0 and lines[start_lineno-1].strip().startswith("@"):
            start_lineno -= 1

        return "\n".join(lines[start_lineno:end_lineno])

    for node in ast.walk(tree):
        # Extract standalone test functions
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_cases.append(get_source_segment(node))

        # Extract test methods inside classes
        elif isinstance(node, ast.ClassDef):
            for sub_node in node.body:
                if isinstance(sub_node, ast.FunctionDef) and sub_node.name.startswith("test_"):
                    test_cases.append(get_source_segment(sub_node))

    return test_cases
        

def choose_fewshot_example_test_cases(selection_mode, test_dir, class_under_test, num_test_cases=1):
    test_files = [f for f in os.listdir(test_dir) if f.endswith(".py")]

    # CASE 1: Choose test classes randomly
    if selection_mode == "random_class":
        random_test_cases = []
        for i in range(num_test_cases):
            random_test_cases.append(os.path.join(test_dir, random.choice(test_files)))
        return random_test_cases
    
    # CASE 2: Choose test cases based on similarity of the classes
    if selection_mode == "random_from_class_under_test":
        random_test_cases = []
        test_file_path = os.path.join(test_dir, f"test_{class_under_test}")
        test_cases = extract_test_cases_from_file(test_file_path)
        for i in range(min(num_test_cases, len(test_cases))):
            random_test_cases.append(random.choice(test_cases))
        return random_test_cases
    
    # CASE 3: Choose test cases based on similarity of the classes
    elif selection_mode == "class_similarity":
        class_dir = "/".join(test_dir.split("/")[:-2])
        class_files = [f for f in os.listdir(class_dir) if f.endswith(".py")]
        class_similarity_scores = []
        class_under_test_string = get_python_file_content(os.path.join(class_dir, class_under_test))

        # Calculate similarity scores between the class under test and all other classes
        for class_file in class_files:
            class_file_string = get_python_file_content(os.path.join(class_dir, class_file))
            class_similarity_scores.append(distance(class_file_string, class_under_test_string))

        # Get indexes of the most similar classes
        most_similar_classes_indexes = sorted(range(len(class_similarity_scores)), key=lambda i: class_similarity_scores[i])[1:num_test_cases+1]
        most_similar_classes = [os.path.join(test_dir, "test_" + class_files[i]) for i in most_similar_classes_indexes]
        return most_similar_classes


if __name__ == "__main__":
    # delete_python_files("tmp/human-eval/tests/human-written")
    # copy_python_files("data/human-eval/tests/human-written", "tmp/human-eval/tests/human-written")
    chosen_test_cases = choose_fewshot_example_test_cases("random_from_class_under_test", "data/human-eval/tests/human-written", "HumanEval_6.py", 2)
    pass

