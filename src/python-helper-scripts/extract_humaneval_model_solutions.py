from human_eval.data import write_jsonl, read_problems
import os 
import json

def save_solutions_json(path):
    problems = read_problems()

    code_solutions = [
        dict(task_id=task_id, prompt=problems[task_id]["prompt"], solution=problems[task_id]["canonical_solution"], test=problems[task_id]["test"])
        for task_id in problems
    ]
    write_jsonl(path, code_solutions)


def save_problems_json(path):
    problems = read_problems()
    num_samples_per_task = 1
    samples = [
        dict(task_id=task_id, solution=problems[task_id]["canonical_solution"], prompt=problems[task_id]["prompt"], test=problems[task_id]["test"])
        for task_id in problems
        for _ in range(num_samples_per_task)
    ]
    write_jsonl(path, samples)


def create_python_files_from_json(jsonl_path, output_directory):
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Read the JSONL file line by line
    with open(jsonl_path, "r") as jsonl_file:
        for line_number, line in enumerate(jsonl_file, start=1):
            try:
                # Parse each line as a JSON object
                entry = json.loads(line.strip())
                
                # Extract task_id, prompt, and solution
                task_id = entry["task_id"].replace("/", "_")  # Replace slashes for valid filenames
                prompt = entry["prompt"]
                solution = entry["solution"]

                # Concatenate prompt and solution
                content = f"{prompt}\n{solution}"

                # Create the Python file
                file_path = os.path.join(output_directory, f"{task_id}.py")
                with open(file_path, "w") as python_file:
                    python_file.write(content)

                print(f"Created: {file_path}")

            except json.JSONDecodeError:
                print(f"Skipping invalid JSON on line {line_number}")
            except KeyError as e:
                print(f"Missing key {e} on line {line_number}")


if __name__ == "__main__":
    dataset_json_path = "data/human_eval/human-eval-dataset.jsonl"
    if not os.path.exists(dataset_json_path):
        save_problems_json(dataset_json_path)
    
    output_directory = "tmp/human_eval"
    create_python_files_from_json(dataset_json_path, output_directory)