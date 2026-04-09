import tkinter as tk
import asyncio
from brain import Brain

class GUIManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GUI Agent")
        self.label = tk.Label(self.root, text="Ready", font=('Helvetica', 18))
        self.label.pack(pady=20)
        
        self.action_queue = asyncio.Queue()
        self.brain = Brain()

    def queue_action(self, action):
        print(f"Action queued: {action}")
        self.action_queue.put_nowait(action)

    async def process_actions(self):
        while not self.action_queue.empty():
            action = await self.action_queue.get()
            print(f"Processing action: {action}")
            response = await self.brain.execute_action(action, self)
            if response:
                print(f"Response received for {action}: {response}")
                self.update_label(response)

    def update_label(self, text):
        # Schedule the label update to run within the Tkinter event loop
        self.root.after(0, lambda: self.label.config(text=text))

    def open_text_edit(self):
        import subprocess
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', '-a', 'TextEdit'])
            elif platform.system() == 'Windows':
                subprocess.Popen(['notepad.exe'])
            else:  # Linux
                subprocess.Popen(['gedit'])
        except Exception as e:
            print(f"Failed to open TextEdit: {e}")

    def type_hello_world(self):
        import pyautogui
        try:
            pyautogui.typewrite('Hello World')
            self.update_label("Hello World Typed")
        except Exception as e:
            print(f"Failed to type 'Hello World': {e}")

    async def start_event_loop(self):
        # Start the Tkinter event loop after all actions are processed
        await asyncio.sleep(0)  # Yield control back to the event loop
        self.root.mainloop()

if __name__ == "__main__":
    gui_manager = GUIManager()
    asyncio.run(asyncio.gather(
        gui_manager.queue_action('Open TextEdit'),
        gui_manager.queue_action('Type Hello World'),
        gui_manager.process_actions(),
        gui_manager.start_event_loop()
    ))