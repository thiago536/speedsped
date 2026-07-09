import pyautogui
import os

def main():
    screenshot_path = "current_screen.png"
    print("Capturing current screen...")
    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    print(f"Screenshot successfully saved to {os.path.abspath(screenshot_path)}")

if __name__ == "__main__":
    main()
