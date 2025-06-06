import os
import shutil
import random
import ast
import shutil
from Levenshtein import distance
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
        shutil.rmtree(target_path)


def generate_identifier_string(identifiers):
    """Generates a string representation of the identifiers dictionary."""
    identifier_string = "_".join([
        identifiers["test_source"],
        str(identifiers["test_selection_mode"]),
        str(identifiers["num_test_cases"])
    ]).lower()
    
    return identifier_string


### File Reading and Test Case Extraction Functions ###

def file_to_multiline_string(file_path):
    """Reads a Python file and converts its content into a multiline string."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        multiline_string = content
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
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
            tree = ast.parse(source_code, filename=file_path)
    except SyntaxError as e:
        print(f"Syntax error in file {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []
    
    test_cases = []
    lines = source_code.splitlines()

    def get_source_segment(node):
        """Extract source code of a function including decorators."""
        start_lineno = node.lineno - 1
        end_lineno = node.end_lineno

        # Include multi-line decorator if present
        if start_lineno > 0 and lines[start_lineno-1].strip().startswith("])"):
            new_start_lineno = start_lineno - 1
            while new_start_lineno > 0 and not lines[new_start_lineno].strip().startswith("@"):
                new_start_lineno -= 1
            start_lineno = new_start_lineno

        # Include decorator if present
        if start_lineno < 0 and lines[start_lineno-1].strip().startswith("@"):
            start_lineno -= 1

        return "\n".join(lines[start_lineno:end_lineno])

    for node in ast.walk(tree):
        # Extract standalone test functions
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_cases.append(get_source_segment(node))

    # if the test case is tabulated, remove the tabs
    untabulated_test_cases = []
    for test_case in test_cases:
        test_case_lines = test_case.split("\n")
        if test_case_lines[0].startswith("    "):
            untabulated_test_cases.append("\n".join([line[4:] for line in test_case_lines]))
        else:
            untabulated_test_cases.append(test_case)

    return untabulated_test_cases


def remove_last_test_case(source_code):
    """Returns the test cases for the specified class."""
    lines = source_code.split('\n')
    i = len(lines) - 1

    # Go backwards to find the end of the last test case
    while i >= 0:
        if lines[i].strip().startswith('def test_'):

            if i-1 >= 0 and lines[i-1].strip().startswith(('@', '#')):
                print("Removing decorator..")
                i = i-1

            elif i-1 >= 0 and lines[i-1].strip().startswith('])'):
                print("Removing parameterize decorator..")
                while i >= 0 and not lines[i].strip() == '' and not lines[i].strip().startswith('@'):
                    print(f"Removing line {i}: {lines[i]}")
                    i -= 1

            return '\n'.join(lines[:i])
        i -= 1
    
    return None
        
        
### Utility functions for Few-shot Example Selection ###

def get_test_without_problem_definition(file_path):
    file = get_python_file_content(file_path)
    parsed_ast = ast.parse(file)
    for node in ast.walk(parsed_ast):
        if isinstance(node, ast.FunctionDef):
            if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
                node.body.pop(0)  # Remove the first node if it's a docstring
    return ast.unparse(parsed_ast)


def extract_problem_definition_from_string(file):
    parsed_ast = ast.parse(file)
    for node in ast.walk(parsed_ast):
        if isinstance(node, ast.FunctionDef):
            return ast.get_docstring(node)
    return None


def calculate_cosine_similarity(text1, text2):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])

    # Compute cosine similarity
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return 1-similarity[0][0] # Return 1-cossimilarity to get distance


def choose_fewshot_example_test_cases(selection_mode, test_dir, class_under_test, num_test_cases=1):
    test_files = [f for f in os.listdir(test_dir) if f.endswith(".py")]
    selected_test_cases = []

    # CASE 1: Choose test classes randomly
    if selection_mode == "random_from_all":
        def choose_random_test_case(test_files):
            random_test_file = random.choice(test_files)
            test_cases = extract_test_cases_from_file(os.path.join(test_dir, random_test_file))
            if len(test_cases) == 0:
                return choose_random_test_case(test_files)
            return random.choice(test_cases)

        for i in range(num_test_cases):
            random_test_case = choose_random_test_case(test_files)
            selected_test_cases.append( random_test_case )
    
    # CASE 2: Choose random unit tests from the class under test
    if selection_mode == "random_from_class_under_test":
        test_file_path = os.path.join(test_dir, f"test_{class_under_test}")
        test_cases = extract_test_cases_from_file(test_file_path)
        n = min(num_test_cases, len(test_cases))
        selected_test_cases = random.sample(test_cases, k=n)
    
    # CASE 3: Choose test cases based on problem similarity
    if selection_mode == "problem_similarity":
        class_dir = "/".join(test_dir.split("/")[:-2])
        class_files = [f for f in os.listdir(class_dir) if f.endswith(".py")]
        class_similarity_scores = []
        class_under_test_string = get_python_file_content(os.path.join(class_dir, class_under_test))
        problem_definition = extract_problem_definition_from_string(class_under_test_string)
        
        # Calculate similarity scores between the class under test and all other classes
        for class_file in class_files:
            class_file_string = get_python_file_content(os.path.join(class_dir, class_file))
            class_file_problem_definition = extract_problem_definition_from_string(class_file_string)
            try:
                class_similarity_scores.append(calculate_cosine_similarity(class_file_problem_definition, problem_definition))
            except Exception as e:
                class_similarity_scores.append(1000)
                
        # Get indexes of the most similar classes
        most_similar_classes_indexes = sorted(range(len(class_similarity_scores)), key=lambda i: class_similarity_scores[i])[1:num_test_cases+1]
        most_similar_classes = [os.path.join(test_dir, "test_" + class_files[i]) for i in most_similar_classes_indexes]
        
        # Extract test cases from the most similar classes
        test_cases = []
        for class_file in most_similar_classes:
            test_cases.extend(extract_test_cases_from_file(class_file))

        n = min(num_test_cases, len(test_cases))
        selected_test_cases = random.sample(test_cases, k=n)

    # CASE 4: Choose test cases based on code similarity - without problem definition
    if selection_mode == "class_similarity_no_definition":
        class_dir = "/".join(test_dir.split("/")[:-2])
        class_files = [f for f in os.listdir(class_dir) if f.endswith(".py")]
        class_similarity_scores = []
        class_under_test_string = get_test_without_problem_definition(os.path.join(class_dir, class_under_test))
        
        # Calculate similarity scores between the class under test and all other classes
        for class_file in class_files:
            class_file_string = get_test_without_problem_definition(os.path.join(class_dir, class_file))
            try:
                class_similarity_scores.append(calculate_cosine_similarity(class_file_string, class_under_test_string))
            except Exception as e:
                class_similarity_scores.append(1000)
                
        # Get indexes of the most similar classes
        most_similar_classes_indexes = sorted(range(len(class_similarity_scores)), key=lambda i: class_similarity_scores[i])[1:num_test_cases+1]
        most_similar_classes = [os.path.join(test_dir, "test_" + class_files[i]) for i in most_similar_classes_indexes]
        
        # Extract test cases from the most similar classes
        test_cases = []
        for class_file in most_similar_classes:
            test_cases.extend(extract_test_cases_from_file(class_file))

        n = min(num_test_cases, len(test_cases))
        selected_test_cases = random.sample(test_cases, k=n)

    # CASE 5: Choose test cases based on code similarity with problem definition
    if selection_mode == "class_similarity_with_definition":
        class_dir = "/".join(test_dir.split("/")[:-2])
        class_files = [f for f in os.listdir(class_dir) if f.endswith(".py")]
        class_similarity_scores = []
        class_under_test_string = get_python_file_content(os.path.join(class_dir, class_under_test))

        # Calculate similarity scores between the class under test and all other classes
        for class_file in class_files:
            class_file_string = get_python_file_content(os.path.join(class_dir, class_file))
            class_similarity_scores.append(calculate_cosine_similarity(class_file_string, class_under_test_string))

        # Get indexes of the most similar classes
        most_similar_classes_indexes = sorted(range(len(class_similarity_scores)), key=lambda i: class_similarity_scores[i])[1:num_test_cases+1]
        most_similar_classes = [os.path.join(test_dir, "test_" + class_files[i]) for i in most_similar_classes_indexes]

        # Extract test cases from the most similar classes
        test_cases = []
        for class_file in most_similar_classes:
            test_cases.extend(extract_test_cases_from_file(class_file))

        n = min(num_test_cases, len(test_cases))
        selected_test_cases = random.sample(test_cases, k=n)
        
    # CASE 6: Choose test cases based on similarity of the classes
    if selection_mode == "problem_and_class_similarity":
        class_dir = "/".join(test_dir.split("/")[:-2])
        class_files = [f for f in os.listdir(class_dir) if f.endswith(".py")]
        class_similarity_scores = []
        class_under_test_string = get_python_file_content(os.path.join(class_dir, class_under_test))
        problem_definition = extract_problem_definition_from_string(class_under_test_string)
        class_under_test_string = get_test_without_problem_definition(os.path.join(class_dir, class_under_test))
        
        # Calculate similarity scores between the class under test and all other classes
        for class_file in class_files:
            class_file_string = get_python_file_content(os.path.join(class_dir, class_file))
            class_file_problem_definition = extract_problem_definition_from_string(class_file_string)
            class_file_string = get_test_without_problem_definition(os.path.join(class_dir, class_file))
            score = 0
            try:
                score += calculate_cosine_similarity(class_file_problem_definition, problem_definition)
                score += calculate_cosine_similarity(class_file_string, class_under_test_string)
            except Exception as e:
                score = 10000
            class_similarity_scores.append(score)
                
        # Get indexes of the most similar classes
        most_similar_classes_indexes = sorted(range(len(class_similarity_scores)), key=lambda i: class_similarity_scores[i])[1:num_test_cases+1]
        most_similar_classes = [os.path.join(test_dir, "test_" + class_files[i]) for i in most_similar_classes_indexes]
        
        # Extract test cases from the most similar classes
        test_cases = []
        for class_file in most_similar_classes:
            test_cases.extend(extract_test_cases_from_file(class_file))

        n = min(num_test_cases, len(test_cases))
        selected_test_cases = random.sample(test_cases, k=n)

    return selected_test_cases


if __name__ == "__main__":
    # delete_python_files("tmp/human-eval/tests/human-written")
    copy_python_files("data/human_eval/tests/pynguin/enhanced/pynguin_random_from_all_5", "tmp/human_eval/tests/pynguin")
    # chosen_test_cases = choose_fewshot_example_test_cases("class_similarity_with_definition", "tmp/human_eval/tests/human_written", "HumanEval_5.py", 2)
    # for test_case in chosen_test_cases:
    #     print(test_case)
    pass

