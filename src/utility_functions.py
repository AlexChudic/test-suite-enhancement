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


# if __name__ == "__main__":
#     copy_python_files("data/human-eval/tests/human-written", "tmp/human-eval/tests/pynguin")

