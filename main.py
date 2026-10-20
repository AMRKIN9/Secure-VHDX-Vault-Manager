import sys
import ctypes
import gui
import vhd_manager

def main():
    if "--panic" in sys.argv:
        # CLI panic dismount
        vhd_manager.panic_dismount_all()
        sys.exit(0)
        
    gui.run_gui()

if __name__ == "__main__":
    main()
