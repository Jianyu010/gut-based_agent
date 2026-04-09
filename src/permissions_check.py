# permissions_check.py
# This module contains logic for checking user permissions within the system.

import logging
from typing import Dict, List

class PermissionChecker:
    """
    A class to handle permission checks for users in the system.
    
    Attributes:
        permissions_db (Dict[str, List[str]]): A dictionary mapping user roles to their permissions.
    """
    def __init__(self, permissions_db: Dict[str, List[str]]):
        """
        Initializes a new PermissionChecker with the given permissions database.

        :param permissions_db: A dictionary where keys are user roles and values are lists of permissions.
        """
        self.permissions_db = permissions_db
        logging.basicConfig(level=logging.DEBUG)

    def check_permission(self, role: str, permission: str) -> bool:
        """
        Checks if a given role has the specified permission.

        :param role: The role of the user (e.g., 'admin', 'user').
        :param permission: The permission to check for (e.g., 'read', 'write').
        :return: True if the role has the permission, False otherwise.
        """
        logging.debug(f'Checking {permission} for role {role}')
        return permission in self.permissions_db.get(role, [])

    def add_permission(self, role: str, permission: str):
        """
        Adds a new permission to an existing role.

        :param role: The role of the user.
        :param permission: The permission to add.
        """
        if role in self.permissions_db:
            if permission not in self.permissions_db[role]:
                self.permissions_db[role].append(permission)
                logging.debug(f'Added {permission} to role {role}')
            else:
                logging.debug(f'{permission} already exists for role {role}')
        else:
            logging.error(f'Role {role} does not exist.')

    def remove_permission(self, role: str, permission: str):
        """
        Removes a permission from an existing role.

        :param role: The role of the user.
        :param permission: The permission to remove.
        """
        if role in self.permissions_db:
            if permission in self.permissions_db[role]:
                self.permissions_db[role].remove(permission)
                logging.debug(f'Removed {permission} from role {role}')
            else:
                logging.debug(f'{permission} does not exist for role {role}')
        else:
            logging.error(f'Role {role} does not exist.')

# Example usage:
if __name__ == '__main__':
    permissions = {
        'admin': ['read', 'write', 'delete'],
        'user': ['read']
    }
    checker = PermissionChecker(permissions)
    print(checker.check_permission('admin', 'write'))  # True
    print(checker.check_permission('user', 'write'))   # False
