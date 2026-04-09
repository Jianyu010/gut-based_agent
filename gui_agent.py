import tkinter as tk
from tkinter import messagebox
import subprocess

def run_readme_updater():
    try:
        result = subprocess.run(['python', 'readme_updater.py'], capture_output=True, text=True, check=True)
        messagebox.showinfo('Success', f'Output:\n{result.stdout}')
    except subprocess.CalledProcessError as e:
        messagebox.showerror('Error', f'An error occurred:\n{e.stderr}')

def show_usage_instructions():
    usage = '''## Usage Instructions
- Run the GUI-based agent by executing `python main.py`
- Ensure all dependencies are installed via `pip install -r requirements.txt`'''
    messagebox.showinfo('Usage Instructions', usage)

# Create the main window
root = tk.Tk()
root.title('GUI-Based Agent')
root.geometry('400x200')

# Add a button to run readme_updater.py
run_button = tk.Button(root, text='Run README Updater', command=run_readme_updater)
run_button.pack(pady=20)

# Add a button to show usage instructions
usage_button = tk.Button(root, text='Show Usage Instructions', command=show_usage_instructions)
usage_button.pack(pady=10)

# Start the GUI event loop
root.mainloop()
