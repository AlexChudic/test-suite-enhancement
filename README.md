# test-suite-enhancement
Level 5 Project on Test Suite Enhancement using LLMs

### Data benchmarks
The project uses the HumanEval, ClassEval and REPOCOD benchmarks. They are store in the /data folder. If you want to run the code, you'll need to clone first!

### Static generation tools
In this project, we use a static unit test generation tool Pynguin to compare the test quality based on where they come from.

## Configuration
TODO add the comands that need to be run

### `python src/evaluation.py`
Command for running the evaluation part of the pipeline. It first evaluates the test suite coverage and then the repository code quality. It saves the results from the sonarqube scanner to a json on predefined path `data/<project_name>/eval/sonarqube_results.json`.
- Make sure to extend the PYTHONPATH with the directory where the project is stored. It should be in the form of: `export PYTHONPATH=<path_to_dir>/test-suite-endancement/tmp/<project_name>`
- The command can then simply be run from root directory as such `python src/evaluation.py`