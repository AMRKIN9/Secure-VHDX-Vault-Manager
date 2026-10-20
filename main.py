import ctypes
import sys
import tkinter as tk
from tkinter import messagebox
import gui

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    if not is_admin():
        # Create a temporary root just to show the error message before the main app starts
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Administrator Rights Required",
            "This application requires Administrative privileges to manage VHDX containers and BitLocker settings.\n\n"
            "Please restart the application as an Administrator."
        )
        root.destroy()
        # We don't exit, but we warn the user. Let them continue if they want (they might just want to list containers).
        # Actually, let's just let them continue but maybe some functions will fail with PermissionError.
        # But wait, the plan said "alert the user if it is not". We've alerted them.
        
    gui.run_gui()

if __name__ == "__main__":
    main()
