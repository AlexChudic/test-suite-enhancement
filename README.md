# test-suite-enhancement
Level 5 Project on Test Suite Enhancement using LLMs

### Supervisor: Handan Gul Calikli

### Abstract

TODO: add abstract

## Configuration
To setup the environment and install the dependencies follow the steps below:

### Setup virtual environment (optional)

1. Create a virtual environment (only run once) `python -m venv venv`
2. Activate the environment - `source venv/bin/activate`

### Install packages

To be able to run the Python scripts, make sure to download the required dependencies stored in requirements.txt:

1. Install third party dependencies - `pip install -r requirements.txt`

### Sonarqube and SonarScanner setup

NOTE: JDK 17 is necessary to run sonarqube. The guide on how to download it is provided [here](https://www3.cs.stonybrook.edu/~amione/CSE114_Course/materials/resources/InstallingJava17.pdf)

1. [Download](https://docs.sonarsource.com/sonarqube/latest/try-out-sonarqube/#installing-a-local-instance-of-sonarqube) and install a local instance of Sonarqube
2. Run Sonarqube in terminal - `<PATH_TO_SONARQUBE>/bin` 
3. Log in, and create a new local project
4. Choose to analyse the project "Locally", generate a token
5. Add the token, project name, and login details to the project's `.env` file
6. [Download](https://docs.sonarsource.com/sonarcloud/advanced-setup/ci-based-analysis/sonarscanner-cli/) and install SonarScanner locally
7. Set the SonarQube envoronment Variable - add these lines to the `~/.zshrc` file
   - `export SONAR_HOME=<PATH_TO_SONNARSCANNER>/{version}/libexec`
   - `export SONAR=$SONAR_HOME/bin export PATH=$SONAR:$PATH`

For Mac, it's possible to use [Homebrew](https://techblost.com/how-to-setup-sonarqube-locally-on-mac/) for easier installation process (steps 1-6 are sufficient)



## Data benchmarks
The project uses the HumanEval and ClassEval benchmarks. If you want to run the code, you'll need to clone them first and run the pre-processing steps used to get them into the format that is used for evaluation. The desciption on how to clone and pre-process each benchmark is below:

### HumanEval
This bechmark can be cloned from GitHub using `git clone https://github.com/openai/human-eval.git`

The pre-processing steps that need to be run (from project root directory):
1. Import human_eval from the local folder - `pip install -e human-eval`
2. Extracting the model solutions - `python -m src.python-helper-scripts.extract_humaneval_model_solutions`
3. Extracting the test suite - `python -m src.python-helper-scripts.extract_humaneval_tests`
4. Generating the SBST-generate test suite using pynguin
    - Start the docker with the pynguin image
    - Generate the test suite using command - `python src/python-helper-scripts/generate_pynguin_tests.py tmp/human_eval data/human_eval/tests/pynguin`
5. Generating the LLM-based test suite
    - Submit the batch request using command - `python -m src.python-helper-scripts.generate_LLM_tests human_eval`
    - Wait until the batch is processed
    - Collect the results using the same command


### ClassEval
This bechmark can be cloned from GitHub using `git clone https://github.com/FudanSELab/ClassEval.git`

The pre-processing steps that need to be run (from project root directory):
1. Extracting the model solutions - `python -m src.python-helper-scripts.extract_classeval_model_solutions`
2. Extracting the test suite - `python -m src.python-helper-scripts.extract_classeval_tests`
3. Generating the SBST-generate test suite using pynguin
    - Start the docker with the pynguin image
    - Generate the test suite using command - `python src/python-helper-scripts/generate_pynguin_tests.py tmp/classeval data/classeval/tests/pynguin`
4. Generating the LLM-based test suite
    - Submit the batch request using command - `python -m src.python-helper-scripts.generate_LLM_tests classeval`
    - Wait until the batch is processed
    - Collect the results using the same command


## Other useful commands

### `python src/evaluation.py`
Command for running the evaluation part of the pipeline. It first evaluates the test suite coverage and then the repository code quality. It saves the results from the sonarqube scanner to a json on predefined path `data/<project_name>/eval/sonarqube_results.json`.
- Make sure to extend the PYTHONPATH with the directory where the project is stored. It should be in the form of: `export PYTHONPATH=<path_to_dir>/test-suite-endancement/tmp/<project_name>`
- The command can then simply be run from root directory as such `python src/evaluation.py`



