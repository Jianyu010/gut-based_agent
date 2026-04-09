import pyautogui
import time

def main():
    # Open TextEdit on macOS
    pyautogui.hotkey('command', 'space')
time.sleep(1)
pyautogui.typewrite('TextEdit')
pyautogui.press('enter')
time.sleep(2)

# Type "hello world"
pyautogui.typewrite('hello world')
time.sleep(1)

# Save the file
pyautogui.hotkey('command', 's')
time.sleep(1)
pyautogui.typewrite('/Users/jianyulong/Desktop/gui-based_agent/hello_world.txt')
pyautogui.press('enter')
time.sleep(2)

if __name__ == '__main__':
    main()
