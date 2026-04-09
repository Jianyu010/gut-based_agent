# test_script.py
import time
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from executor import click_marker, type_text, hotkey, ActionError

def main():
    try:
        # Adjust coordinates based on your screen setup
        # Coordinates to open TextEdit (example)
        click_marker(100, 100)  # Click on the application launcher or menu
        time.sleep(2)
        type_text('TextEdit')
        hotkey(Key.enter)
        time.sleep(4)  # Wait for TextEdit to open
        
        # Type 'hello world' in TextEdit
        type_text('hello world', delay=0.1)
        time.sleep(2)  # Give some buffer time
        
        # Save the file
        hotkey(Key.cmd, 's')
        time.sleep(2)  # Wait for save dialog to open
        
        # Type file name and confirm save
        type_text('hello_world.txt', delay=0.1)
        hotkey(Key.enter)
    except ActionError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
