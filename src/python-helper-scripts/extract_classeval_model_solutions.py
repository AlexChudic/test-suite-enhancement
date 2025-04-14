import src.utility_functions as uf
import os

input_directory = "ClassEval/data/benchmark_solution_code"
output_directory = "tmp/classeval/"

# Copy the ClassEval benchmark solutions from the input directory to the tmp directory
if __name__ == "__main__":
    uf.copy_python_files(input_directory, output_directory)
    os.remove("tmp/classeval/DocFileHandler.py")
