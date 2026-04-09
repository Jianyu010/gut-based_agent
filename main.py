import sys
sys.path.append("/Users/jianyulong/Desktop/gui-based_agent")
from permissions_check import check_read_permission, check_write_permission, check_exe_permission
from pathlib import Path

def file_handling(file_path, user_permissions):
    path = Path(file_path)
    try:
        if not path.exists():
            raise FileNotFoundError(f"The specified path does not exist: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"The specified path is a directory, not a file: {path}")
        # Check for valid directory and file name
        if not path.parent.exists() or not path.parent.is_dir():
            raise NotADirectoryError(f"The directory part of the path does not exist or is not a directory: {path.parent}")
        if not path.name:
            raise ValueError("The file name part of the path is empty.")
        # Example of checking read permission
        if check_read_permission(user_permissions):
            with path.open('r') as file:
                content = file.read()
                print(content)
        else:
            print('User does not have read permission for the document.')
    except FileNotFoundError as fnf_e:
        print(fnf_e)
    except PermissionError as perm_e:
        print(perm_e)
    except IsADirectoryError as dir_e:
        print(dir_e)
    except NotADirectoryError as nadir_e:
        print(nadir_e)
    except ValueError as ve:
        print(ve)

user_permissions = {'read_document': True, 'write_document': False}
def main():
    file_handling("/path/to/your/file.txt", user_permissions)  # Update this path to a valid file path for testing
    # Example usage of the imported functions
    try:
        if check_read_permission(user_permissions):
            print('User has read permission for the document.')
        else:
            print('User does not have read permission for the document.')
    except PermissionError as e:
        print(e)
if __name__ == '__main__':
    main()
