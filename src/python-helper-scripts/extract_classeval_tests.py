import re
import ast
import os
import sys
from typing import List
import src.utility_functions as uf
from pathlib import Path
import subprocess

def find_definition_imports(path):
    """Find all import statements in a Python file"""
    with open(path, 'r') as f:
        content = f.read()

    # Use regex to find all import statements
    imports = re.findall(r'^\s*(?:import|from)\s+.*', content, re.MULTILINE)
    
    # Filter out any non-import lines
    imports = [line.strip() for line in imports if line.strip() and not line.startswith('#')]
    
    return imports


def finalize_pytest_conversion(directory):
    """Complete the pytest conversion for all test files"""
    for test_file in Path(directory).glob('test_*.py'):
        # if test_file.stem[5:] not in ["ArgumentParser", "DocFileHandler"]:
        #     continue

        with open(test_file, 'r+') as f:
            content = f.read()
            
        # 1. Replace unittest imports with pytest
        content = content.replace('import unittest', 'import pytest')
        
        # 2. Process test classes
        def replace_class(match):
            class_name = ensure_test_class_prefix(match.group(1))
            base_class = match.group(2)

            # Only remove unittest.TestCase while preserving other potential base classes
            base_class = '' if base_class == 'unittest.TestCase' or base_class == None or base_class == 'None' else base_class
            return f'class {class_name}({base_class}):'
        
        content = re.sub(
            r'class +(\w+)(?:\(([^)]*)\))?:',
            replace_class,
            content
        )

        # 3. Convert the setUp method to a pytest fixture
        def replace_setUp_class(match):
            setup_str = match.group(1)
            setup_line = setup_str.split('\n')[-1]
            indent = setup_line[:setup_line.index('def')]
            return f'{indent}@pytest.fixture(autouse=True)\n{indent}def setup(self):'

        content = re.sub(
            r'(^\s*def setUp\(self\):)',
            replace_setUp_class,
            content,
            flags=re.MULTILINE
        )

        # 4. Include the import statments from problem definition in the test file
        class_under_test_path = os.path.join("/".join(directory.split("/")[:-2]), test_file.stem[5:] + ".py")
        problem_imports = find_definition_imports(class_under_test_path)
        if problem_imports:
            for import_statement in problem_imports:
                if import_statement not in content:
                    content = f"{import_statement}\n{content}"

        # Write changes back to file
        with open(test_file, 'w') as f:
            f.write(content)

        print(f'Updated: {test_file.name}')


def ensure_test_class_prefix(class_name):
    """Ensure class name starts with Test"""
    if not class_name.startswith('Test'):
        # Handle cases where class might end with Test (like MyTest -> TestMy)
        if class_name.endswith('Test'):
            return 'Test' + class_name[:-4]
        return 'Test' + class_name
    return class_name


def rename_test_files(directory):
    """Add test_ prefix to all Python test files in directory"""
    for filename in os.listdir(directory):
        if filename.endswith('.py') and not filename.startswith('test_'):
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, f'test_{filename}')
            os.rename(old_path, new_path)
            print(f'Renamed {filename} to test_{filename}')


def convert_test_files(directory):
    """Complete conversion workflow"""
    print("1. Renaming test files...")
    rename_test_files(directory)
    
    print("\n2. Finalizing pytest conversion...")
    finalize_pytest_conversion(directory)
    
    print(f"Convertion completed!!!")


def delete_backup_files(directory):
    """Delete all backup files in the directory"""
    for filename in os.listdir(directory):
        if filename.endswith('.bak'):
            os.remove(os.path.join(directory, filename))
            print(f'Deleted backup file: {filename}')

if __name__ == "__main__":

    input_directory = "ClassEval/data/benchmark_test_code"
    tmp_directory = "tmp/classeval/tests/human_written2"
    output_directory = "data/classeval/tests/human_written2"

    # Copy the Python files from the input directory to the output directory
    os.makedirs(tmp_directory, exist_ok=True)
    uf.copy_python_files(input_directory, tmp_directory)

    # Remove the DocFileHandler.py file from the output directory -> the import it uses is not available
    os.remove(f"{tmp_directory}/DocFileHandler.py")
    
    try:
        subprocess.run(
            ["unittest2pytest", "-w", str(tmp_directory)],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Successfully converted unittest files in: {tmp_directory}")

    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error:\n{e.stderr}")
        raise
    except FileNotFoundError:
        raise RuntimeError(
            "unittest2pytest not found. Install it with: pip install unittest2pytest"
        )
    
    # Delete backup files created by unittest2pytest
    delete_backup_files(tmp_directory)

    # Convert the test files into pytest format
    convert_test_files(tmp_directory)

    # Move the converted test files to the output directory and cleanup
    os.makedirs(output_directory, exist_ok=True)
    uf.copy_python_files(tmp_directory, output_directory)
    uf.delete_repository(tmp_directory)

    # uf.copy_python_files(output_directory, tmp_directory)

