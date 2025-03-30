import os
import subprocess

# Define paths
project_path = "tmp/human_eval"
output_path = "data/human_eval/tests/pynguin"
package_path = "tmp/package.txt"

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
