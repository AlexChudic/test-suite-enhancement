# Python helper scripts
The python helper scripts in this folder are used for a one-time executable actions. You can find the description of each of them and the run guide below.

## extract_humaneval_unit_tests.py
Extracts the asserts provided in the human-eval-dataset and converts them into pytest unit tests - one assert per test. Outputs the test to the directory `data/human_eval/tests/human_written`

Run from main directory by using command `python src/python-helper-scripts/extract_humaneval_unit_tests.py`

## generate-pynguin-tests.py
Python script for that makes use of the pynguin image running in docker to generate unit tests for python classes on path `project_path` and saves them to directory `output_path`.

Run from main directory simply by using command `python src/python-helper-scripts/generate_pynguin_tests.py`. Set parameters in the file before execution.
    - `project_path` - defines where the classes under test are stored
    - `output_path` - defines where the generated tests should be stored
