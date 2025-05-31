# Automated Test Suite Enhancement Using Large Language Models With Few-shot Prompting

This is the artifacts package for the paper "Automated Test Suite Enhancement Using Large Language Models With Few-shot Prompting".

## Environment Configuration

### Virtual Environment Setup (Optional)

1. Create a virtual environment (only run once) `python -m venv venv`
2. Activate the environment
    - Linux/Mac: `source venv/bin/activate`
    - Windows: `.\venv\Scripts\activate`

### Dependency installation

1. Install third party dependencies - `pip install -r requirements.txt`

## SonarQube & SonarScanner Setup

### Prerequisites

- JDK 17 ([Instalation Guide](https://www3.cs.stonybrook.edu/~amione/CSE114_Course/materials/resources/InstallingJava17.pdf))

### Installation Steps

1. Donwload and install [SonarQube](https://docs.sonarsource.com/sonarqube/latest/try-out-sonarqube/#installing-a-local-instance-of-sonarqube) locally
2. Run Sonarqube in terminal - `<PATH_TO_SONARQUBE>/bin` 
3. Create a new local project through the web interface
4. Generate a token during "Local" analysis setup
5. Configure the `.env` file with:
    - SonarQube token
    - Project name
    - Login credentials
6. Install [SonarScanner](https://docs.sonarsource.com/sonarcloud/advanced-setup/ci-based-analysis/sonarscanner-cli/) locally
7. Set the SonarQube environment variable - add these lines to the `~/.zshrc` file
   - `export SONAR_HOME=<PATH_TO_SONNARSCANNER>/{version}/libexec`
   - `export SONAR=$SONAR_HOME/bin export PATH=$SONAR:$PATH`

For Mac, it's possible to use [Homebrew](https://techblost.com/how-to-setup-sonarqube-locally-on-mac/) for easier installation process (steps 1-6 are sufficient)

## Pynguin setup

We employ pynguin from docker, to be able to generate tests using our scripts, you will need to follow these steps:

1. Install [Docker Desktop](https://docs.docker.com/desktop/)
2. Run Pynguin container - from `pynguin/pynguin:0.31.0` image

## Data benchmarks
The project uses the HumanEval and ClassEval benchmarks. If you want to run the code, you'll need to clone them first and run the pre-processing steps used to get them into the format that is used for evaluation. The desciption on how to clone and pre-process each benchmark is below:

### HumanEval
This bechmark can be cloned from GitHub using `git clone https://github.com/openai/human-eval.git`

Run the pre-processing steps  (from project root directory):
1. Import human_eval from the local folder - `pip install -e human-eval`
2. Extracting the model solutions - `python -m src.python-helper-scripts.extract_humaneval_model_solutions`
3. Extracting the test suite - `python -m src.python-helper-scripts.extract_humaneval_tests`
4. Generating the SBST-generate test suite using pynguin
    - Start the docker with the Pynguin container
    - Generate the test suite using command - `python src/python-helper-scripts/generate_pynguin_tests.py tmp/human_eval data/human_eval/tests/pynguin`
5. Generating the LLM-based test suite
    - Populate `.env` file with your OPENAI credentials
    - Submit the batch request using command - `python -m src.python-helper-scripts.generate_LLM_tests human_eval`
    - Wait until the batch is processed
    - Collect the results using the same command

### ClassEval
This bechmark can be cloned from GitHub using `git clone https://github.com/FudanSELab/ClassEval.git`

Run the pre-processing steps (from project root directory):
1. Extracting the model solutions - `python -m src.python-helper-scripts.extract_classeval_model_solutions`
2. Extracting the test suite - `python -m src.python-helper-scripts.extract_classeval_tests`
3. Generating the SBST-generate test suite using pynguin
    - Start the docker with the Pynguin container
    - Generate the test suite using command - `python src/python-helper-scripts/generate_pynguin_tests.py tmp/classeval data/classeval/tests/pynguin`
4. Generating the LLM-based test suite
    - Populate `.env` file with your OPENAI credentials
    - Submit the batch request using command - `python -m src.python-helper-scripts.generate_LLM_tests classeval`
    - Wait until the batch is processed
    - Collect the results using the same command

## Running the evaluation

To run the evaluation on the project, follow these steps:

1. Extend the PYTHONPATH with the directory where the project is stored for import test import statements to run properly: `export PYTHONPATH=<path_to_dir>/test-suite-endancement/tmp/<project_name>` 
    - Project name should be one of the following: `human_eval` `classeval`
2. - Populate `.env` file with your OPENAI and SONARQUBE credentials
3. Run the evaluation of the initial test suite - `python -m src.run_pipeline <project_name> initial_evaluation`
    - Project name should be one of the following: `human_eval` `classeval`
4. Run the full evaluation pipeline - `python -m src.run_pipeline <project_name> run_full_pipeline`
    - Project name should be one of the following: `human_eval` `classeval`
5. The evaluation figures will be available in `src/evaluation_figures.ipynb` python notebook

## Other useful commands

### `python src/evaluation.py`
Command for running the evaluation part of the pipeline. It first evaluates the test suite coverage and then the repository code quality. It saves the results from the sonarqube scanner to a json on predefined path `data/<project_name>/eval/sonarqube_results.json`.
- Make sure to extend the PYTHONPATH with the directory where the project is stored. It should be in the form of: `export PYTHONPATH=<path_to_dir>/test-suite-endancement/tmp/<project_name>`
- The command can then simply be run from root directory as such `python src/evaluation.py`



