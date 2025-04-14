# test-suite-enhancement
Level 5 Project on Test Suite Enhancement using LLMs

## Data benchmarks
The project uses the HumanEval and ClassEval benchmarks. If you want to run the code, you'll need to clone them first and run the pre-processing steps used to get them into the format that is used for evaluation.

### HumanEval
This 


### ClassEval
This bechmark can be cloned from GitHub using `git clone https://github.com/FudanSELab/ClassEval.git`

The pre-processing steps that need to be run (from project root directory):
1. Extracting the model solutions - `python -m src.python-helper-scripts.extract_classeval_model_solutions`
2. Extracting the test suite - `python -m src.python-helper-scripts.extract_classeval_tests`


## Configuration
TODO add the comands that need to be run

### `python src/evaluation.py`
Command for running the evaluation part of the pipeline. It first evaluates the test suite coverage and then the repository code quality. It saves the results from the sonarqube scanner to a json on predefined path `data/<project_name>/eval/sonarqube_results.json`.
- Make sure to extend the PYTHONPATH with the directory where the project is stored. It should be in the form of: `export PYTHONPATH=<path_to_dir>/test-suite-endancement/tmp/<project_name>`
- The command can then simply be run from root directory as such `python src/evaluation.py`

