import os
import ast
import re
def extract_function_signatures_and_docstrings(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        tree = ast.parse(content)
        function_details = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_signature = ast.unparse(node).split(':')[0].strip()
                docstring = ast.get_docstring(node)
                if docstring:
                    function_details.append((function_signature, docstring))
        return function_details
    except FileNotFoundError as e:
        print(f"Error: File {file_path} not found.")
def generate_action_specs_md(file_paths, output_path):
    with open(output_path, 'w') as outfile:
        for file_path in file_paths:
            if os.path.exists(file_path):
                outfile.write(f"## File: {file_path}\n\n")
                functions = extract_function_signatures_and_docstrings(file_path)
                if not functions:
                    outfile.write("No function signatures or docstrings found.\n\n")
                for signature, docstring in functions:
                    outfile.write(f"### {signature}\n\n{docstring}\n\n")
def main():
    legacy_files = ['executor.py', 'gui_agent.py', 'brain.py', 'gui_manager.py']
    target_files = ['executor.py']  # Only parse executor.py for the specs
    generate_action_specs_md(target_files, 'action_specs.md')
if __name__ == '__main__':
    main()
