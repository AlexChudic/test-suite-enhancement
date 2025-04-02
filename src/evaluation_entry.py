import json
import os
import src.utility_functions as uf
import tmp.correctness_evaluation as correctness_evaluation
from datetime import datetime

EVALUATION_DIR="data/eval/"

class EvaluationEntry:

    def __init__(self, batch_id, identifiers={}, eval_data={}, eval_id=None, status="initial", timestamp=None, is_loaded_from_json=False):
        """Initialize the EvaluationEntry object."""

        self.batch_id = batch_id
        self.identifiers = identifiers
        self.eval_data = eval_data
        self.status = status
        self.timestamp = timestamp if timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.is_loaded_from_json = is_loaded_from_json

        if eval_id is None:
            self.eval_id = self.generate_eval_id()
        else:
            self.eval_id = eval_id

        if not is_loaded_from_json:
            print("NEW Evaluation entry created!")
            print(self.to_json())
        else:
            # print(f"Evaluation entry loaded from JSON! Eval ID: {self.eval_id}, Status: {self.get_status()}")
            pass
        

    @classmethod
    def from_dict(cls, eval_data: dict):
        """Alternative constructor for loading from a dictionary file."""
        return cls(
            eval_data["batch_id"],
            eval_data["identifiers"],
            eval_data["eval_data"],
            eval_data["eval_id"],
            eval_data["status"],
            eval_data["timestamp"],
            is_loaded_from_json=True
        )
    
    @classmethod
    def get_eval_entry(cls, batch_id, project_name):
        """Check if an evaluation entry exists."""
        if not os.path.exists(os.path.join(EVALUATION_DIR, f"{project_name}.jsonl")):
            return None
        
        eval_entries = cls.load_all(project_name)
        for entry in eval_entries:
            if entry.batch_id == batch_id:
                return entry
        else:
            return None
    
    @classmethod
    def load_all(cls, project_name):
        """Load all evaluation entries for a project."""
        if not os.path.exists(os.path.join(EVALUATION_DIR, f"{project_name}.jsonl")):
            return []
        
        with open(os.path.join(EVALUATION_DIR, f"{project_name}.jsonl"), "r") as file:
            entries = []
            for line in file:
                entry_data = json.loads(line)
                entry = cls.from_dict(entry_data)
                entries.append(entry)
            return entries

    def run_evaluation(self):
        if self.get_status() != "initial":
            print("Skipping evaluation, not in state=initial")

        else:
            # STEP 1: Run the test correctness evaluation
                # Ensure the tests are working correctly
                # Apply Rule-based repair if not
                # Ensure the tests improve the coverage

            test_suite_path = f"data/{ self.get_project_name() }/tests/{ self.get_test_source() }"
            print(test_suite_path)
            # res = correctness_evaluation.evaluate_functional_correctness(test_suite_path)



            # STEP 2: Run the initial project evaluations - using the example tests only
                # Evaluate full project to get code coverage
                # Evaluate test directory to get code quality metrics
            # STEP 3: Run the specific project evaluation - with the enhanced test suite
                # Evaluate full project to get code coverage
                # Evaluate test directory to get code quality metrics
            # STEP 4: Save the eval_entry to the JSON file


    def generate_eval_id(self):
        """Generate a unique evaluation ID."""

        eval_id = "_".join([
            str(self.get_evalId_number(True)),
            self.get_test_source(),
            self.identifiers["test_selection_mode"],
            str(self.identifiers["num_test_cases"]),
            self.identifiers["model_name"].replace("-", "_"),
            str(self.identifiers["temperature"]).replace(".", "_")
        ]).lower()

        return eval_id
    

    def get_evalId_number(self, generate_new=False):
        """Get the evaluation ID number"""
        if generate_new:
            json_path = self.get_json_path()
            if not os.path.exists(json_path):
                with open(json_path, "w") as f:
                    f.write('')

            with open(json_path, "r") as f:
                lines = f.readlines()
                return len(lines)
        else:
            return self.eval_id.split("_")[1]
            
    def get_project_name(self):
        return self.identifiers["project_name"]
    
    def get_test_source(self):
        return self.identifiers["test_source"]

    def save(self):
        """Save the evaluation entry to a JSON file."""
        if not os.path.exists(EVALUATION_DIR):
            os.makedirs(EVALUATION_DIR)

        if self.is_loaded_from_json:
            id = self.get_evalId_number()
            with open(self.get_json_path(), "rw") as file:
                lines = file.readlines()
                print(lines)
            print(f"Evaluation entry updated! Eval ID: {self.eval_id}, Status {self.get_status()}")
        else:
            with open(self.get_json_path(), "a") as file:
                file.write(json.dumps(self.to_json()) + "\n")
            print(f"Evaluation entry saved! Eval ID: {self.eval_id}, Status: {self.get_status()}")

    def to_json(self):
        """Convert the object to a JSON dictionary."""
        return {
            "eval_id": self.eval_id,
            "batch_id": self.batch_id,
            "identifiers": self.identifiers,
            "eval_data": self.eval_data,
            "status": self.status,
            "timestamp": self.timestamp
        }    

    def get_status(self):
        """Check the status of the evaluation."""
        return self.status
    
    def get_json_path(self):
        return os.path.join(EVALUATION_DIR, f"{self.identifiers['project_name']}.jsonl")
    
    def __str__(self):
        return json.dumps(self.to_json())




