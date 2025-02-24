# Bash scripts
The Bash helper scripts in this folder help with running different parts of the pipeline. You can find the description of each of them and the run guide below.

## evaluate-repository.sh
This Bash script runs the Sonarqube evalution using the sonar_token provided. The script is used in the evaluation.py to trigger the evaluation of the evaluated folder.

Can be run in command line from root using command `/bin/bash ./evaluate-repository.sh <path-to-project> <sonar_token>`
    - <path-to-project> - takes the path to evaluated folder tmp/ which we want to evaluate
    - <sonar_token> - takes the sonarqube token from our project


## evaluate-test-suite.sh
This Bash script automates the execution of tests using tox, verifies the generation of a coverage.xml report, and archives it for reference.

Can be run in command line from root using command `/bin/bash src/bash-scripts/evaluate-test-suite.sh`


## generate-pynguin-tests.sh
This Bash script runs the pynguin version in docker to generate unit tests for python files on path `INPUT_DIR`
