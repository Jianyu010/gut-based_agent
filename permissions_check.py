import os
from pathlib import Path

def check_read_permission(file_path):
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'The file or directory {path} does not exist.')
        if not path.is_file() and not path.is_dir():
            raise TypeError(f'The path {path} is neither a file nor a directory.')
        if not os.access(path, os.R_OK):
            return False
        return True
    except (FileNotFoundError, TypeError) as e:
        print(e)
        return False

def check_write_permission(file_path):
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'The file or directory {path} does not exist.')
        if not path.is_file() and not path.is_dir():
            raise TypeError(f'The path {path} is neither a file nor a directory.')
        if not os.access(path, os.W_OK):
            return False
        return True
    except (FileNotFoundError, TypeError) as e:
        print(e)
        return False

def check_exe_permission(file_path):
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'The file or directory {path} does not exist.')
        if not path.is_file() and not path.is_dir():
            raise TypeError(f'The path {path} is neither a file nor a directory.')
        if not os.access(path, os.X_OK):
            return False
        return True
    except (FileNotFoundError, TypeError) as e:
        print(e)
        return False