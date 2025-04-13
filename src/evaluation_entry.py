import json
import os
import pandas as pd
import src.utility_functions as uf
import src.evaluation as eval
import src.use_gpt_in_batches as use_gpt
import tmp.correctness_evaluation as correctness_evaluation
from datetime import datetime

EVALUATION_DIR="data/eval/"

class EvaluationEntry:

    def __init__(self, batch_id:str, type:str, identifiers={}, eval_data={}, eval_id=None, status="initial", timestamp=None, is_loaded_from_json=False):
        """Initialize the EvaluationEntry object."""

        self.batch_id = batch_id
        self.type = type
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
            print(f"NEW {type.capitalize()} evaluation entry created!")
            print(self.to_json())
            self.save(new=True)
        else:
            # print(f"Evaluation entry loaded from JSON! Eval ID: {self.eval_id}, Status: {self.get_status()}")
            pass
        

    @classmethod
    def from_dict(cls, eval_data: dict):
        """Alternative constructor for loading from a dictionary file."""
        return cls(
            eval_data["batch_id"],
            eval_data["type"],
            eval_data["identifiers"],
            eval_data["eval_data"],
            eval_data["eval_id"],
            eval_data["status"],
            eval_data["timestamp"],
            is_loaded_from_json=True
        )
    
    @classmethod
    def get_eval_entry(cls, batch_id, type, project_name):
        """Check if an evaluation entry exists."""
        path = cls.get_type_json_path(type, project_name)
        if not os.path.exists(path):
            return None
        
        eval_entries = cls.load_all(type, project_name)
        for entry in eval_entries:
            if entry.batch_id == batch_id:
                return entry
        else:
            return None
        
    @classmethod
    def get_eval_entry_by_eval_id(cls, eval_id, type, project_name):
        """Check if an evaluation entry exists."""
        path = cls.get_type_json_path(type, project_name)
        if not os.path.exists(path):
            return None
        
        eval_entries = cls.load_all(type, project_name)
        for entry in eval_entries:
            if entry.eval_id == eval_id:
                return entry
        else:
            return None
    
    @classmethod
    def load_all(cls, type, project_name):
        """Load all evaluation entries for a project."""
        json_path = cls.get_type_json_path(type, project_name)
        if not os.path.exists(json_path):
            return None
        
        with open(json_path, "r") as file:
            entries = []
            for line in file:
                entry_data = json.loads(line)
                entry = cls.from_dict(entry_data)
                entries.append(entry)
            return entries


    def run_correctness_evaluation(self):
        """Run the correctness evaluation on the enhanced test suite.
                - Ensure the tests are working correctly
                - Apply Rule-based repair if not passed
        """
        if self.get_status() == "initial":
            data_test_path = f"data/{ self.get_project_name() }/tests/{ self.get_test_source() }/enhanced/{ uf.generate_identifier_string(self.identifiers) }/"
            if os.path.exists(data_test_path):
                # Enhanced test suite has been generated from the batch request - continue with evaluation
                tmp_test_path = f"tmp/{ self.get_project_name() }/tests/{ self.get_test_source() }/"
                uf.copy_python_files(data_test_path, tmp_test_path)
                
                res = correctness_evaluation.evaluate_functional_correctness(tmp_test_path)
                self.eval_data["correctness_evaluation"] = res
                print(res)

                uf.copy_python_files(tmp_test_path, data_test_path)
                uf.delete_python_files(tmp_test_path)
                uf.delete_repository(tmp_test_path)

                self.status = "corrected"
                self.save()
            else:
                # Enhanced test suite has not been generated yet
                print(f"Skipping correctness evaluation - test suite path does not exist: {data_test_path}")
        else:
            print("Skipping correctness evaluation - not in state=initial")

    
    def run_enhanced_evaluation(self):
        """Run the enhanced evaluation on the enhanced test suite.
                - Evaluate full project to get code coverage
                - Evaluate test directory to get code quality metrics
        """
        if self.get_status() == "corrected":

            data_test_path = f"data/{ self.get_project_name() }/tests/{ self.get_test_source() }/enhanced/{ uf.generate_identifier_string(self.identifiers) }/"
            
            if os.path.exists(data_test_path):

                tmp_test_path = f"tmp/{ self.get_project_name() }/tests/{ self.get_test_source() }/"
                uf.copy_python_files(data_test_path, tmp_test_path)

                project_name = self.get_project_name()
                test_source = self.get_test_source()
                
                # # WTF: Why is the test_source not in the path? 
                # # Actually, what is this copy even for?
                # uf.copy_python_files(f"data/{project_name}/tests/", f"tmp/{project_name}/tests/{test_source}")
                
                # First evaluate the full project to get code coverage
                project_eval_metrics = eval.evaluate_project_directory(project_name)
                self.eval_data["enhanced_project_evaluation"] = project_eval_metrics
                print(project_eval_metrics)

                # Then evaluate the test directory to get code quality metrics
                test_eval_metrics = eval.evaluate_project_directory(project_name, directory_path=f"tests/{test_source}")
                self.eval_data["enhanced_test_evaluation"] = test_eval_metrics
                print(test_eval_metrics)
                            
                uf.delete_python_files(tmp_test_path)
                uf.delete_repository(tmp_test_path)

                self.status = "evaluated"
                self.save()

            else:
                print(f"Skipping enhanced evaluation - test suite path does not exist: {data_test_path}")
        else:
            print("Skipping enhanced evaluation - not in state=corrected")
            
    def run_test_suite_optimization(self):
        if self.status == "evaluated":
            initial_test_suite_path = f"data/{ self.get_project_name() }/tests/{ self.get_test_source() }/"
            enhanced_test_suite_path = f"data/{ self.get_project_name() }/tests/{ self.get_test_source() }/enhanced/{ uf.generate_identifier_string(self.identifiers) }/"
            if os.path.exists(enhanced_test_suite_path):
                tmp_test_path = f"tmp/{ self.get_project_name() }/tests/{ self.get_test_source() }/"
                uf.copy_python_files(initial_test_suite_path, tmp_test_path)

                # Run the test suite optimization
                optimised_test_suite_stats = correctness_evaluation.optimise_test_suite_effectiveness(tmp_test_path, enhanced_test_suite_path)
                print(optimised_test_suite_stats)

                uf.delete_python_files(tmp_test_path)
                uf.delete_repository(tmp_test_path)

                # Save the optimised test suite stats
                self.eval_data["optimised_test_suite_stats"] = optimised_test_suite_stats

                # Perform optimised test suite evaluation
                data_test_path = f"data/{ self.get_project_name() }/tests/{ self.get_test_source() }/optimised/{ uf.generate_identifier_string(self.identifiers) }/"
                if os.path.exists(data_test_path):
                    # Enhanced test suite has been generated from the batch request - continue with evaluation
                    tmp_test_path = f"tmp/{ self.get_project_name() }/tests/{ self.get_test_source() }/"
                    uf.copy_python_files(data_test_path, tmp_test_path)

                    # First evaluate the full project to get code coverage
                    optimised_project_eval_metrics = eval.evaluate_project_directory(self.get_project_name())
                    self.eval_data["optimised_project_evaluation"] = optimised_project_eval_metrics
                    print(optimised_project_eval_metrics)

                    # Then evaluate the test directory to get code quality metrics
                    optimised_test_eval_metrics = eval.evaluate_project_directory(self.get_project_name())
                    self.eval_data["optimised_test_evaluation"] = optimised_test_eval_metrics
                    print(optimised_test_eval_metrics)

                    uf.delete_python_files(tmp_test_path)
                    uf.delete_repository(tmp_test_path)
                else:
                    print(f"Skipping optimised evaluation - test suite path does not exist: {data_test_path}")

                self.status = "optimized"
                self.save()
            else:
                print(f"Skipping test suite optimization - enhanced test suite path does not exist: {enhanced_test_suite_path}")
        else:
            print(f"Skipping test suite optimization {self.eval_id} - not in state=evaluated")

    def generate_eval_id(self):
        """Generate a unique evaluation ID."""
        eval_id = ""
        if self.type == "initial":
            eval_id = "/".join([
                str(self.get_evalId_number(True)),
                self.get_test_source()
            ]).lower()
        else:
            eval_id = "/".join([
                str(self.get_evalId_number(True)),
                self.get_test_source(),
                self.identifiers["test_selection_mode"],
                str(self.identifiers["num_test_cases"])
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
            return int(self.eval_id.split("/")[0])
            
    def get_project_name(self):
        return self.identifiers["project_name"]
    
    def get_test_source(self):
        return self.identifiers["test_source"]


    def save(self, new=False):
        """Save the evaluation entry to a JSON file."""
        if not os.path.exists(EVALUATION_DIR):
            os.makedirs(EVALUATION_DIR)

        if not new:
            id = self.get_evalId_number()
            lines = []
            with open(self.get_json_path(), "r") as file:
                lines = file.read().split("\n")
                
            lines[id] = json.dumps(self.to_json())

            with open(self.get_json_path(), "w") as file:
                file.write("\n".join(lines))
            print(f"Evaluation entry updated! Eval ID: {self.eval_id}, Status {self.get_status()}")
        else:
            with open(self.get_json_path(), "a") as file:
                file.write(json.dumps(self.to_json()) + "\n")
            print(f"Evaluation entry saved! Eval ID: {self.eval_id}, Status: {self.get_status()}")


    def to_json(self):
        """Convert the object to a JSON dictionary."""
        return {
            "eval_id": self.eval_id,
            "type": self.type,
            "status": self.status,
            "batch_id": self.batch_id,
            "identifiers": self.identifiers,
            "eval_data": self.eval_data,
            "timestamp": self.timestamp
        }    

    def get_status(self):
        """Check the status of the evaluation."""
        return self.status
    
    @classmethod
    def get_type_json_path(cls, type, project_name):
        if type == "enhanced":
            return os.path.join(EVALUATION_DIR, f"{project_name}.jsonl")
        else:
            return os.path.join(EVALUATION_DIR, f"{project_name}_{type}.jsonl")
        
    def get_json_path(self):
        return EvaluationEntry.get_type_json_path(self.type, self.get_project_name())
    
    def get_eval_entry_csv(self):
        correctnes_data = self.eval_data["correctness_evaluation"]
        eval_data_project = self.eval_data["enhanced_project_evaluation"]
        eval_data_test = self.eval_data["enhanced_test_evaluation"]
        total_tests = correctnes_data["correctness_eval_counts"]["stats_post_removal"]["passed_tests"] + correctnes_data["correctness_eval_counts"]["stats_post_repair"]["failed_tests"]
        test_source_data = {
            "eval_id" : self.eval_id,
            "test_source": self.identifiers["test_source"],
            "num_test_cases" : self.identifiers["num_test_cases"] if "num_test_cases" in self.identifiers else None,
            "test_selection_mode" : self.identifiers["test_selection_mode"] if "test_selection_mode" in self.identifiers else None,
            "total_classes" : correctnes_data["correctness_eval_counts"]["stats_pre_repair"]["total_classes"],
            "total_tests" : total_tests,

            # Correctness stats
            "passed" : correctnes_data["correctness_eval_counts"]["stats_pre_repair"]["passed_tests"],
            "passed_after_repair" : correctnes_data["correctness_eval_counts"]["stats_post_removal"]["passed_tests"],
            "syntax_errors" : correctnes_data["correctness_eval_counts"]["stats_pre_repair"]["syntax_errors"],
            "syntax_errors_after_repair" : correctnes_data["correctness_eval_counts"]["stats_post_removal"]["syntax_errors"],
            "compilation_errors" : correctnes_data["correctness_eval_counts"]["stats_pre_repair"]["compilation_errors"],
            "compilation_errors_after_repair" : correctnes_data["correctness_eval_counts"]["stats_post_removal"]["compilation_errors"],
            "no_test_classes_after_repair" : correctnes_data["correctness_eval_counts"]["stats_post_removal"]["no_tests_classes"],
            
            # Repair stats
            "rule_1_repair_count": total_tests,
            "rule_2_repair_count": 0,
            "rule_3_repair_count": len(correctnes_data["repair_stats"]["rule_2"]),
            "rule_3_repaired_tests": correctnes_data["repair_stats"]["rule_2"],
            "rule_4_repair_count": len(correctnes_data["repair_stats"]["rule_3"]),
            "rule_4_repaired_tests": correctnes_data["repair_stats"]["rule_3"],
            "rule_5_repair_count": len(correctnes_data["repair_stats"]["rule_5"]),
            "rule_5_repaired_tests": correctnes_data["repair_stats"]["rule_5"],
            "rule_6_repair_count": len(correctnes_data["repair_stats"]["rule_4"]),
            "rule_6_repaired_tests": correctnes_data["repair_stats"]["rule_4"],
            "rule_7_repair_count": len(correctnes_data["repair_stats"]["rule_0"]),
            "rule_7_repaired_tests": correctnes_data["repair_stats"]["rule_0"],
            "rule_8_repair_count": len(correctnes_data["repair_stats"]["rule_1"]),
            "rule_8_repaired_tests": correctnes_data["repair_stats"]["rule_1"],
            "rule_9_repair_count": len(correctnes_data["repair_stats"]["rule_6"]),
            "rule_9_repaired_tests": correctnes_data["repair_stats"]["rule_6"],
            "rule_10_repair_count": len(correctnes_data["repair_stats"]["rule_7"]),
            "rule_10_repaired_tests": correctnes_data["repair_stats"]["rule_7"],

            # Coverage stats
            "coverage" : eval_data_project["coverage"],
            "branch_coverage" : eval_data_project["branch_coverage"],
            "line_coverage" : eval_data_project["line_coverage"],
            "lines_to_cover" : eval_data_project["lines_to_cover"],
            "uncovered_lines" : eval_data_project["uncovered_lines"],
            "execution_time" : eval_data_project["execution_time"],

            # Test quality stats
            "lines" : eval_data_test["lines"],
            "non_comment_lines" : eval_data_test["ncloc"],
            "comment_lines" : eval_data_test["comment_lines"],
            "cognitive_complexity" : eval_data_test["cognitive_complexity"],
            "cyclomatic_complexity" : eval_data_test["complexity"],
            "squale_index" : eval_data_test["sqale_index"],
            "code_smells" : eval_data_test["code_smells"],
            "bugs" : eval_data_test["bugs"],
            "vulnerabilities" : eval_data_test["vulnerabilities"],
        }

        # Calculate additional metrics
        test_source_data["syntactically_correct"] = test_source_data["total_classes"] - test_source_data["syntax_errors"]
        test_source_data["syntactically_correct_after_repair"] = test_source_data["total_classes"] - test_source_data["syntax_errors_after_repair"]
        test_source_data["compilable"] = test_source_data["total_classes"] - test_source_data["compilation_errors"]
        test_source_data["compilable_after_repair"] = test_source_data["total_classes"] - test_source_data["compilation_errors_after_repair"]
        
        # Insert the corruption_data into rule_2
        if "corruption_data" in self.eval_data:
            test_source_data["rule_2_repair_count"] = self.eval_data["corruption_data"]["corrupted_output"]
        
        # Convert the lists into a string
        for key in test_source_data:
            if isinstance(test_source_data[key], list):
                test_source_data[key] = ';'.join(map(str, test_source_data[key]))
        
        # print(test_source_data)
        df = pd.DataFrame(test_source_data, index=[0])
        return df
    

    def redo_evaluation(self):
        """Redo the evaluation"""
        self.status = "redo_evaluation"
        self.save()
        
        # Change the status to completed -> so that the evaluation can be redone
        batch_requests = use_gpt.load_batch_requests(client=None)
        for batch_request in batch_requests:
            if batch_request.batch_id == self.batch_id:
                batch_request.status = "completed"
                print(f"Batch request status changed to completed: {self.batch_id}")
                print(batch_request.status)
        use_gpt.save_batch_requests(batch_requests)


    def __str__(self):
        return json.dumps(self.to_json())

if __name__ == "__main__":
    eval_id = "36/chatgpt/random_from_all/1"
    eval_entry = EvaluationEntry.get_eval_entry_by_eval_id(eval_id, "enhanced", "human_eval")
    eval_entry.run_test_suite_optimization()
