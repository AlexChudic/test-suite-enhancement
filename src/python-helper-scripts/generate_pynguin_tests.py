import os
import subprocess
import sys

def generate_pynguin_files(project_path, output_path, package_path):
    # Make sure the output directory exists
    os.makedirs(output_path, exist_ok=True)

    # Get all Python files in the project path
    python_files = [f for f in os.listdir(project_path) if f.endswith(".py")]

    # Check the files in output dir 
    output_files = [f.replace("test_", "") for f in os.listdir(output_path) if f.endswith(".py")]

    # Loop through each Python file and run the Docker command
    for python_file in python_files:
        if python_file in output_files:
            print(f"Skipping {python_file} as it already has tests generated.")
            continue
        
        module_name = os.path.splitext(python_file)[0]  # Get the file name without the .py extension
        print(module_name)
        command = [
            "docker", "run", "--rm",
            "--platform", "linux/amd64",
            "-v", f"{os.getcwd()}/{project_path}:/input:ro",
            "-v", f"{os.getcwd()}/{output_path}:/output",
            "-v", f"{os.getcwd()}/{package_path}:/package/package.txt:ro",
            "pynguin/pynguin:0.31.0",
            "--project-path", "/input",
            "--module-name", module_name,
            "--output-path", "/output"
        ]
        
        # Run the command and capture the output
        print(f"Running Pynguin for module: {module_name}")
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Log the result
        print(result)
        if result.returncode == 0:
            print(f"Successfully generated tests for {module_name}")
        else:
            print(f"Error generating tests for {module_name}")
            print(result.stderr)

if __name__ == "__main__":
    package_path = "tmp/package.txt"

    if len(sys.argv) == 3:
        print("Usage: python script.py <project_path> <output_path>")
        
        project_path = sys.argv[1]
        output_path = sys.argv[2]

        # Run the function with the provided paths
        generate_pynguin_files(project_path, output_path, package_path)

    elif len(sys.argv) == 1:
        print("No arguments provided. Using default paths.")

        # Define paths
        project_path = "tmp/classeval"
        output_path = "data/classeval/tests/pynguin"

        # Run the function with the default paths
        generate_pynguin_files(project_path, output_path, package_path)
    else:
        print("Usage: python script.py <project_path> <output_path>")
        sys.exit(1)

    