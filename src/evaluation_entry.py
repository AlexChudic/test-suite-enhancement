import json
import os
import src.utility_functions as uf
from datetime import datetime

EVALUATION_DIR="data/eval/"

class EvaluationEntry:

    def __init__(self, batch_id, identifiers={}, eval_data={}, eval_id=None, status="initial", timestamp=None, is_loaded_form_json=False):
        """Initialize the EvaluationEntry object."""
        if eval_id is None:
            eval_id = self.generate_eval_id()
        else:
            self.eval_id = eval_id

        self.batch_id = batch_id
        self.identifiers = identifiers
        self.eval_data = eval_data
        self.status = status
        self.timestamp = timestamp if timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not is_loaded_form_json:
            print("NEW Evaluation entry created!")
            print(self.to_json())
        else:
            print(f"Evaluation entry loaded from JSON! Batch ID: {self.batch_id}, Status: {self.check_status()}")
        

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
            is_loaded_form_json=True
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

    def generate_eval_id(self):
        """Generate a unique evaluation ID."""

        eval_id = "_".join([
            self.identifiers["test_source"],
            self.identifiers["test_selection_mode"],
            str(self.identifiers["num_test_cases"]),
            self.identifiers["model_name"].replace("-", "_"),
            str(self.identifiers["temperature"]).replace(".", "_")
        ]).lower()

        return eval_id
    

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

    def check_status(self):
        """Check the status of the evaluation."""
        return self.status
    
    
    def __str__(self):
        return json.dumps(self.to_json())




