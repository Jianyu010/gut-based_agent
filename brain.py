import asyncio
from tkinter import Tk, Button, Label, StringVar
import subprocess
import pyautogui
class Brain:
    def __init__(self):
        self.root = Tk()
        self.action = None
        self.setup_ui()

    def setup_ui(self):
        self.label_var = StringVar(value="Ready")
        label = Label(self.root, textvariable=self.label_var)
        label.pack(pady=20)
        button = Button(self.root, text="Execute", command=self.execute_action)
        button.pack()

    def execute_action(self):
        self.action = asyncio.create_task(self.perform_actions())

    async def perform_actions(self):
        try:
            await self.open_text_edit()
            await self.type_hello_world()
            self.label_var.set("Completed")
        except Exception as e:
            self.label_var.set(f"Error: {e}")
            print(f"Error during action execution: {e}")

    async def open_text_edit(self):
        try:
            process = await asyncio.to_thread(subprocess.Popen, ['open', '-a', 'TextEdit'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise Exception(f"Failed to open TextEdit: {stderr.decode()}")
        except Exception as e:
            print(f"Error opening TextEdit: {e}")

    async def type_hello_world(self):
        try:
            await asyncio.to_thread(pyautogui.typewrite, 'Hello World')
        except Exception as e:
            print(f"Error typing Hello World: {e}")
def start_gui(root):
    brain = Brain()
    root.mainloop()
if __name__ == "__main__":
    root = Tk()
    root.title("GUI Agent")
    asyncio.run(start_gui(root))
