import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import vhd_manager
import bitlocker

def apply_modern_window_effects(window):
    try:
        from ctypes import windll, byref, sizeof, c_int
        window.update()
        hwnd = int(window.wm_frame(), 16)
        
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), sizeof(c_int))
        
        # DWMWA_SYSTEMBACKDROP_TYPE = 38
        # 2 = Mica, 3 = Acrylic, 4 = Mica Alt
        windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, byref(c_int(2)), sizeof(c_int))
    except Exception as e:
        pass # Silently fail on older Windows versions

class CreateContainerDialog(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Create Container")
        self.geometry("320x220")
        self.resizable(False, False)
        self.callback = callback
        
        self.configure(bg="#202020", padx=15, pady=15)
        apply_modern_window_effects(self)
        
        style = ttk.Style(self)
        style.configure("Dialog.TLabel", background="#202020", foreground="white")
        style.configure("Dialog.TCheckbutton", background="#202020", foreground="white")
        
        ttk.Label(self, text="Container Name:", style="Dialog.TLabel").grid(row=0, column=0, sticky="w", pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.name_var).grid(row=0, column=1, pady=5)
        
        ttk.Label(self, text="Size (GB):", style="Dialog.TLabel").grid(row=1, column=0, sticky="w", pady=5)
        self.size_var = tk.StringVar(value="10")
        ttk.Entry(self, textvariable=self.size_var).grid(row=1, column=1, pady=5)
        
        self.dynamic_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Dynamic (Expands on use)", variable=self.dynamic_var, style="Dialog.TCheckbutton").grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        self.automount_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Auto-mount after creation", variable=self.automount_var, style="Dialog.TCheckbutton").grid(row=3, column=0, columnspan=2, sticky="w", pady=5)
        
        btn_frame = tk.Frame(self, bg="#202020")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text="Create", command=self.on_create).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)
        
        self.transient(parent)
        self.grab_set()

    def on_create(self):
        name = self.name_var.get().strip()
        size = self.size_var.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Name cannot be empty.", parent=self)
            return
            
        try:
            size_gb = int(size)
            if size_gb <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Size must be a positive integer.", parent=self)
            return
            
        self.callback(name, size_gb, self.dynamic_var.get(), self.automount_var.get())
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Secure VHDX Vault Manager")
        self.geometry("750x450")
        
        self.setup_theme()
        self.create_widgets()
        apply_modern_window_effects(self)
        self.refresh_list()
        
    def setup_theme(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        
        bg_color = "#202020"
        fg_color = "#FFFFFF"
        sel_bg = "#005FB8" # Windows 11 accent color
        
        self.configure(bg=bg_color)
        
        style.configure(".", background=bg_color, foreground=fg_color, font=("Segoe UI", 9))
        
        # Frame
        style.configure("TFrame", background=bg_color)
        
        # Buttons
        style.configure("TButton", padding=6, background="#333333", foreground=fg_color, borderwidth=0, relief="flat")
        style.map("TButton", background=[('active', "#444444"), ('pressed', "#222222")])
        
        # Treeview
        style.configure("Treeview", 
                        background="#2A2A2A", 
                        fieldbackground="#2A2A2A", 
                        foreground="white", 
                        borderwidth=0,
                        rowheight=30)
        style.configure("Treeview.Heading", 
                        background="#1A1A1A", 
                        foreground="white", 
                        relief="flat",
                        padding=5)
        style.map("Treeview", 
                  background=[('selected', sel_bg)], 
                  foreground=[('selected', 'white')])
                  
        # Status bar
        style.configure("Status.TLabel", background="#1A1A1A", foreground="#CCCCCC", padding=5)

    def create_widgets(self):
        # Top Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=15, pady=15)
        
        # Left buttons
        ttk.Button(toolbar, text="↻ Refresh", command=self.refresh_list).pack(side="left", padx=(0,5))
        ttk.Button(toolbar, text="＋ Create", command=self.open_create_dialog).pack(side="left", padx=5)
        ttk.Button(toolbar, text="▶ Mount", command=self.mount_selected).pack(side="left", padx=5)
        ttk.Button(toolbar, text="⏹ Dismount", command=self.dismount_selected).pack(side="left", padx=5)
        ttk.Button(toolbar, text="🗑 Delete", command=self.delete_selected).pack(side="left", padx=5)
        
        # Right buttons
        ttk.Button(toolbar, text="Unlock", command=self.unlock_selected).pack(side="right", padx=(5,0))
        ttk.Button(toolbar, text="Lock", command=self.lock_selected).pack(side="right", padx=5)
        ttk.Button(toolbar, text="BitLocker", command=bitlocker.open_bitlocker_setup).pack(side="right", padx=5)
        
        # Treeview
        columns = ("Name", "Size (GB)", "Status", "Drive", "BitLocker")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
            
        self.tree.column("Name", width=200, anchor="w")
        self.tree.column("Status", width=120)
        
        self.tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Bottom Status Area
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, style="Status.TLabel")
        status_bar.pack(fill="x", side="bottom")

    def run_async(self, func, *args, on_success=None):
        def task():
            try:
                func(*args)
                if on_success:
                    self.after(0, on_success)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self.status_var.set("Error occurred."))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def refresh_list(self):
        self.status_var.set("Refreshing...")
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        def fetch():
            try:
                containers = vhd_manager.list_containers()
                self.after(0, lambda: self.update_tree(containers))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to list containers:\n{e}"))
                self.after(0, lambda: self.status_var.set("Failed to refresh"))
                
        threading.Thread(target=fetch, daemon=True).start()

    def update_tree(self, containers):
        for c in containers:
            status = "Mounted" if c.is_mounted else "Unmounted"
            drive = c.drive_letter if c.drive_letter else "-"
            self.tree.insert("", "end", values=(c.name, c.size_gb, status, drive, c.bitlocker_status), tags=(c.path,))
        self.status_var.set(f"Ready - {len(containers)} containers found.")

    def get_selected_path(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a container.")
            return None
        return self.tree.item(selected[0])['tags'][0]
        
    def get_selected_drive(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a container.")
            return None
        drive = self.tree.item(selected[0])['values'][3]
        return drive if drive != "-" else None

    def open_create_dialog(self):
        CreateContainerDialog(self, self.create_container)
        
    def create_container(self, name, size, dynamic, automount):
        self.status_var.set(f"Creating container {name}...")
        self.run_async(vhd_manager.create_container, name, size, dynamic, automount)

    def mount_selected(self):
        path = self.get_selected_path()
        if path:
            self.status_var.set("Mounting container...")
            self.run_async(vhd_manager.mount_container, path)

    def dismount_selected(self):
        path = self.get_selected_path()
        if path:
            self.status_var.set("Dismounting container...")
            self.run_async(vhd_manager.dismount_container, path)

    def delete_selected(self):
        path = self.get_selected_path()
        if path:
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to PERMANENTLY delete:\n{path}\n\nThis cannot be undone."):
                self.status_var.set("Deleting container...")
                self.run_async(vhd_manager.delete_container, path)

    def lock_selected(self):
        drive = self.get_selected_drive()
        if drive:
            self.status_var.set("Locking volume...")
            self.run_async(bitlocker.lock_volume, drive)
        else:
            messagebox.showinfo("Info", "Selected container must be mounted to lock it.")
            
    def unlock_selected(self):
        drive = self.get_selected_drive()
        if drive:
            bitlocker.unlock_volume(drive)
        else:
            messagebox.showinfo("Info", "Selected container must be mounted to unlock it.")

def run_gui():
    app = App()
    app.mainloop()
