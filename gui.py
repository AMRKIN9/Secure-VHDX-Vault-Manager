import os
import sys
import ctypes
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image

import theme_nothing as theme
import vhd_manager
import bitlocker
from auth_2fa import SecurityManager
from backup_manager import BackupManager

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def elevate_privileges():
    """Relaunches application with Windows UAC elevation prompt."""
    try:
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Elevation Failed", f"Could not elevate privileges: {e}")

# ==============================================================================
# MODALS & DIALOGS (NOTHING OS INDUSTRIAL AESTHETIC)
# ==============================================================================

class NothingModal(ctk.CTkToplevel):
    """Base modal styled in Nothing industrial monochrome."""
    def __init__(self, parent, title: str, width: int = 420, height: int = 480):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.configure(fg_color=theme.COLOR_BG_ROOT)
        
        # Center on parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        py = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{max(10, px)}+{max(10, py)}")
        
        self.transient(parent)
        self.grab_set()

class CreateVaultModal(NothingModal):
    def __init__(self, parent, callback):
        super().__init__(parent, "CREATE // NEW VAULT", width=460, height=520)
        self.callback = callback
        
        # Container frame
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header
        ctk.CTkLabel(pad_frame, text="[ + NEW ENCRYPTED CONTAINER ]", font=theme.FONT_HEADING,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Vault Name
        ctk.CTkLabel(pad_frame, text="VAULT IDENTIFIER / NAME", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20, pady=(5, 2))
        self.name_entry = ctk.CTkEntry(pad_frame, placeholder_text="MySecureVault", font=theme.FONT_BODY,
                                       fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                       text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.name_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        # Size (GB)
        ctk.CTkLabel(pad_frame, text="CAPACITY (GIGABYTES)", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20, pady=(5, 2))
        self.size_entry = ctk.CTkEntry(pad_frame, placeholder_text="10", font=theme.FONT_BODY,
                                       fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                       text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.size_entry.insert(0, "10")
        self.size_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        # Dynamic switch
        self.dynamic_var = ctk.BooleanVar(value=True)
        self.dyn_switch = ctk.CTkSwitch(pad_frame, text="DYNAMIC EXPANSION (Grows on demand)", font=theme.FONT_CAPTION,
                                        variable=self.dynamic_var, progress_color=theme.COLOR_TEXT_PRIMARY,
                                        fg_color=theme.COLOR_SURFACE_3)
        self.dyn_switch.pack(anchor="w", padx=20, pady=5)
        
        # Auto-mount switch
        self.automount_var = ctk.BooleanVar(value=True)
        self.mount_switch = ctk.CTkSwitch(pad_frame, text="AUTO-MOUNT UPON INITIALIZATION", font=theme.FONT_CAPTION,
                                          variable=self.automount_var, progress_color=theme.COLOR_TEXT_PRIMARY,
                                          fg_color=theme.COLOR_SURFACE_3)
        self.mount_switch.pack(anchor="w", padx=20, pady=5)
        
        # BitLocker Password Section
        ctk.CTkLabel(pad_frame, text="BITLOCKER XTS-AES 256 PASSPHRASE (OPTIONAL)", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_ACCENT_RED).pack(anchor="w", padx=20, pady=(15, 2))
        self.pwd_entry = ctk.CTkEntry(pad_frame, placeholder_text="Leave blank to format without password", show="*",
                                      font=theme.FONT_BODY, fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                      text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.pwd_entry.pack(fill="x", padx=20, pady=(0, 20))
        
        # Action Buttons
        btn_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(5, 15))
        
        ctk.CTkButton(btn_box, text="[ CREATE VAULT ]", font=theme.FONT_STATUS,
                      fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                      hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.on_create).pack(side="left", expand=True, fill="x", padx=(0, 5))
                      
        ctk.CTkButton(btn_box, text="[ CANCEL ]", font=theme.FONT_STATUS,
                      fg_color=theme.COLOR_SURFACE_3, text_color=theme.COLOR_TEXT_SECONDARY,
                      hover_color=theme.COLOR_SURFACE_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.destroy).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def on_create(self):
        name = self.name_entry.get().strip()
        size_str = self.size_entry.get().strip()
        pwd = self.pwd_entry.get().strip() or None
        
        if not name:
            messagebox.showerror("Validation Error", "Vault name cannot be empty.", parent=self)
            return
            
        try:
            size_gb = int(size_str)
            if size_gb <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Validation Error", "Capacity must be a positive integer in GB.", parent=self)
            return
            
        self.callback(name, size_gb, self.dynamic_var.get(), self.automount_var.get(), pwd)
        self.destroy()

class TwoFactorModal(NothingModal):
    """Sleek Nothing-style 2FA QR Code & Verification Modal."""
    def __init__(self, parent, security_manager: SecurityManager, on_updated_callback):
        super().__init__(parent, "SECURITY // TWO-FACTOR AUTH", width=460, height=620)
        self.sm = security_manager
        self.on_updated = on_updated_callback
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(pad_frame, text="[ 2FA // RFC 6238 AUTHENTICATOR ]", font=theme.FONT_HEADING,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(15, 5))
                     
        is_active = self.sm.is_2fa_enabled()
        status_text = "STATUS: ACTIVE (PROTECTED)" if is_active else "STATUS: INACTIVE (UNCONFIGURED)"
        status_color = theme.COLOR_ACCENT_GREEN if is_active else theme.COLOR_ACCENT_RED
        ctk.CTkLabel(pad_frame, text=f"● {status_text}", font=theme.FONT_CAPTION,
                     text_color=status_color).pack(anchor="w", padx=20, pady=(0, 10))
        
        if not is_active:
            # Generate pending secret
            self.pending_secret = self.sm.generate_secret()
            uri = self.sm.get_totp_uri(self.pending_secret)
            
            # QR Code Display
            qr_pil = self.sm.generate_qr_image(uri, size=210)
            self.qr_img = ctk.CTkImage(light_image=qr_pil, dark_image=qr_pil, size=(210, 210))
            
            qr_frame = ctk.CTkFrame(pad_frame, fg_color="#FFFFFF", corner_radius=2, border_width=1, border_color="#FFFFFF")
            qr_frame.pack(pady=10)
            ctk.CTkLabel(qr_frame, image=self.qr_img, text="").pack(padx=5, pady=5)
            
            ctk.CTkLabel(pad_frame, text=f"SECRET KEY: {self.pending_secret}", font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_SECONDARY).pack(pady=(2, 10))
            
            ctk.CTkLabel(pad_frame, text="ENTER 6-DIGIT CODE FROM AUTHENTICATOR APP:", font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(5, 2))
                         
            self.code_entry = ctk.CTkEntry(pad_frame, placeholder_text="000000", font=theme.FONT_HEADING,
                                           justify="center", fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                           text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
            self.code_entry.pack(fill="x", padx=20, pady=(0, 15))
            
            ctk.CTkButton(pad_frame, text="[ VERIFY & ENABLE 2FA ]", font=theme.FONT_STATUS,
                          fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                          hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                          command=self.on_enable).pack(fill="x", padx=20, pady=(0, 10))
        else:
            ctk.CTkLabel(pad_frame, text="Two-Factor Authentication is currently securing this vault system.",
                         font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_SECONDARY, wraplength=380).pack(padx=20, pady=20)
                         
            ctk.CTkLabel(pad_frame, text="ENTER 6-DIGIT CODE TO DISABLE 2FA:", font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(10, 2))
                         
            self.code_entry = ctk.CTkEntry(pad_frame, placeholder_text="000000", font=theme.FONT_HEADING,
                                           justify="center", fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                           text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
            self.code_entry.pack(fill="x", padx=20, pady=(0, 20))
            
            ctk.CTkButton(pad_frame, text="[ DISABLE 2FA ]", font=theme.FONT_STATUS,
                          fg_color=theme.COLOR_ACCENT_RED, text_color=theme.COLOR_TEXT_PRIMARY,
                          hover_color=theme.COLOR_ACCENT_RED_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                          command=self.on_disable).pack(fill="x", padx=20, pady=(0, 10))

    def on_enable(self):
        token = self.code_entry.get().strip()
        if self.sm.enable_2fa(self.pending_secret, token):
            messagebox.showinfo("Success", "Two-Factor Authentication successfully enabled!", parent=self)
            self.on_updated()
            self.destroy()
        else:
            messagebox.showerror("Error", "Invalid authentication token. Please check code and try again.", parent=self)

    def on_disable(self):
        token = self.code_entry.get().strip()
        if self.sm.disable_2fa(token):
            messagebox.showinfo("Success", "Two-Factor Authentication disabled.", parent=self)
            self.on_updated()
            self.destroy()
        else:
            messagebox.showerror("Error", "Invalid authentication token.", parent=self)

class BackupManagerModal(NothingModal):
    """Snapshot backups, manifest, and SHA-256 integrity inspection."""
    def __init__(self, parent, vhdx_list):
        super().__init__(parent, "SYSTEM // VAULT BACKUPS", width=620, height=520)
        self.vhdx_list = vhdx_list
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        header_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        header_box.pack(fill="x", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(header_box, text="[ BACKUP ARCHIVE & INTEGRITY SEALS ]", font=theme.FONT_HEADING,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(side="left")
                     
        # Scrollable list of backups
        self.scroll = ctk.CTkScrollableFrame(pad_frame, fg_color=theme.COLOR_SURFACE_2,
                                             corner_radius=theme.CORNER_RADIUS_BTN,
                                             border_width=1, border_color=theme.COLOR_BORDER)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.status_lbl = ctk.CTkLabel(pad_frame, text="", font=theme.FONT_CAPTION, text_color=theme.COLOR_TEXT_SECONDARY)
        self.status_lbl.pack(padx=20, pady=(0, 10))
        
        self.refresh_backups()

    def refresh_backups(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()
            
        backups = BackupManager.list_backups()
        if not backups:
            ctk.CTkLabel(self.scroll, text="NO ARCHIVES FOUND IN BACKUP DIRECTORY.",
                         font=theme.FONT_CAPTION, text_color=theme.COLOR_TEXT_DIM).pack(pady=40)
            return
            
        for b in backups:
            card = ctk.CTkFrame(self.scroll, fg_color=theme.COLOR_SURFACE_3, corner_radius=theme.CORNER_RADIUS_BTN,
                                border_width=1, border_color=theme.COLOR_BORDER)
            card.pack(fill="x", pady=4, padx=5)
            
            top_line = ctk.CTkFrame(card, fg_color="transparent")
            top_line.pack(fill="x", padx=10, pady=(8, 2))
            
            ctk.CTkLabel(top_line, text=b.get("backup_name", "Unknown"), font=theme.FONT_BODY_BOLD,
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(top_line, text=f"{b.get('size_gb', 0)} GB", font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_SECONDARY).pack(side="right")
                         
            meta_line = ctk.CTkFrame(card, fg_color="transparent")
            meta_line.pack(fill="x", padx=10, pady=(2, 8))
            
            ctk.CTkLabel(meta_line, text=f"DATE: {b.get('timestamp', '-')}  |  SHA: {b.get('checksum', '')[:16]}...",
                         font=theme.FONT_CAPTION, text_color=theme.COLOR_TEXT_SECONDARY).pack(side="left")
                         
            b_path = b.get("backup_path", "")
            ctk.CTkButton(meta_line, text="[ VERIFY ]", font=theme.FONT_CAPTION, width=70, height=22,
                          fg_color=theme.COLOR_SURFACE_1, hover_color=theme.COLOR_SURFACE_HOVER,
                          corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=b_path: self.verify_file(p)).pack(side="right")

    def verify_file(self, path):
        self.status_lbl.configure(text=f"Verifying SHA-256 for {os.path.basename(path)}...")
        def task():
            valid = BackupManager.verify_backup(path)
            res_txt = "VALID (HASH MATCHES)" if valid else "CORRUPTED / MISMATCH"
            self.after(0, lambda: self.status_lbl.configure(
                text=f"INTEGRITY: {res_txt}",
                text_color=theme.COLOR_ACCENT_GREEN if valid else theme.COLOR_ACCENT_RED
            ))
        threading.Thread(target=task, daemon=True).start()

class PasswordPromptModal(NothingModal):
    def __init__(self, parent, title: str, prompt: str, callback):
        super().__init__(parent, title, width=380, height=240)
        self.callback = callback
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(pad_frame, text=prompt, font=theme.FONT_BODY,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 10))
                     
        self.entry = ctk.CTkEntry(pad_frame, placeholder_text="Enter passphrase", show="*", font=theme.FONT_BODY,
                                  fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                  text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.entry.pack(fill="x", padx=20, pady=(0, 20))
        self.entry.focus()
        
        btn_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(btn_box, text="[ CONFIRM ]", font=theme.FONT_STATUS,
                      fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                      hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.on_ok).pack(side="left", expand=True, fill="x", padx=(0, 5))
                      
        ctk.CTkButton(btn_box, text="[ CANCEL ]", font=theme.FONT_STATUS,
                      fg_color=theme.COLOR_SURFACE_3, text_color=theme.COLOR_TEXT_SECONDARY,
                      hover_color=theme.COLOR_SURFACE_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.destroy).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def on_ok(self):
        val = self.entry.get()
        if val:
            self.callback(val)
            self.destroy()

# ==============================================================================
# MAIN APPLICATION WINDOW
# ==============================================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SECURE // VHDX VAULT MANAGER")
        self.geometry("960x680")
        self.minsize(880, 560)
        self.configure(fg_color=theme.COLOR_BG_ROOT)
        
        self.sm = SecurityManager()
        self.is_elevated = is_admin()
        
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        # 1. Elevation Warning Banner (if not admin)
        if not self.is_elevated:
            elevate_bar = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_2, height=36, corner_radius=0,
                                       border_width=1, border_color=theme.COLOR_ACCENT_RED)
            elevate_bar.pack(fill="x")
            
            ctk.CTkLabel(elevate_bar, text="[ ⚠ RESTRICTED PRIVILEGES ] BitLocker & VHDX attachments require Administrator rights.",
                         font=theme.FONT_CAPTION, text_color=theme.COLOR_ACCENT_RED).pack(side="left", padx=15, pady=6)
                         
            ctk.CTkButton(elevate_bar, text="[ ELEVATE AS ADMIN ]", font=theme.FONT_CAPTION, width=150, height=24,
                          fg_color=theme.COLOR_ACCENT_RED, text_color=theme.COLOR_TEXT_PRIMARY,
                          hover_color=theme.COLOR_ACCENT_RED_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                          command=elevate_privileges).pack(side="right", padx=15, pady=6)

        # 2. Main Header Bar
        header = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, height=64, corner_radius=0,
                              border_width=1, border_color=theme.COLOR_BORDER)
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=15, pady=10)
        
        ctk.CTkLabel(title_box, text="● SECURE // VHDX VAULT MANAGER", font=theme.FONT_TITLE,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_box, text="BUILD 2.4.0 [NOTHING_EDITION] // 256-BIT ENCRYPTION // RFC 6238 TOTP",
                     font=theme.FONT_CAPTION, text_color=theme.COLOR_TEXT_SECONDARY).pack(anchor="w")

        # Top Action Suite
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=15, pady=10)
        
        ctk.CTkButton(btn_box, text="↻ REFRESH", width=90, height=30, font=theme.FONT_CAPTION,
                      fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_SURFACE_HOVER,
                      corner_radius=theme.CORNER_RADIUS_BTN, command=self.refresh_list).pack(side="left", padx=3)
                      
        ctk.CTkButton(btn_box, text="+ NEW VAULT", width=105, height=30, font=theme.FONT_STATUS,
                      fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                      hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.open_create_modal).pack(side="left", padx=3)
                      
        self.btn_2fa = ctk.CTkButton(btn_box, text=self.get_2fa_btn_text(), width=100, height=30, font=theme.FONT_CAPTION,
                                     fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_SURFACE_HOVER,
                                     corner_radius=theme.CORNER_RADIUS_BTN, command=self.open_2fa_modal)
        self.btn_2fa.pack(side="left", padx=3)
        
        ctk.CTkButton(btn_box, text="💾 BACKUPS", width=95, height=30, font=theme.FONT_CAPTION,
                      fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_SURFACE_HOVER,
                      corner_radius=theme.CORNER_RADIUS_BTN, command=self.open_backups_modal).pack(side="left", padx=3)
                      
        # Emergency Panic Dismount Button
        ctk.CTkButton(btn_box, text="! PANIC LOCK", width=110, height=30, font=theme.FONT_STATUS,
                      fg_color=theme.COLOR_ACCENT_RED, text_color=theme.COLOR_TEXT_PRIMARY,
                      hover_color=theme.COLOR_ACCENT_RED_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.panic_lock).pack(side="left", padx=(8, 0))

        # 3. Scrollable Vaults View Area
        self.vaults_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.vaults_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # 4. Bottom Industrial Telemetry Bar
        self.telemetry = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, height=28, corner_radius=0,
                                      border_width=1, border_color=theme.COLOR_BORDER)
        self.telemetry.pack(fill="x", side="bottom")
        
        self.status_var = tk.StringVar(value="SYSTEM STATUS: IDLE")
        ctk.CTkLabel(self.telemetry, textvariable=self.status_var, font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(side="left", padx=15, pady=4)
                     
        storage_dir = vhd_manager.get_storage_dir()
        ctk.CTkLabel(self.telemetry, text=f"STORAGE ROOT: {storage_dir}", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_DIM).pack(side="right", padx=15, pady=4)

    def get_2fa_btn_text(self):
        return "[ 2FA: ACTIVE ]" if self.sm.is_2fa_enabled() else "[ 2FA: OFF ]"

    def open_create_modal(self):
        CreateVaultModal(self, self.create_vault)

    def open_2fa_modal(self):
        TwoFactorModal(self, self.sm, on_updated_callback=lambda: self.btn_2fa.configure(text=self.get_2fa_btn_text()))

    def open_backups_modal(self):
        BackupManagerModal(self, vhd_manager.list_containers())

    def create_vault(self, name, size_gb, dynamic, automount, password):
        self.status_var.set(f"CREATING VAULT // {name}...")
        def task():
            try:
                vhd_manager.create_container(name, size_gb, dynamic, automount, password)
                self.after(0, lambda: self.status_var.set("VAULT CREATED SUCCESSFULLY."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Creation Failed", str(e)))
                self.after(0, lambda: self.status_var.set("CREATION ERROR."))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def panic_lock(self):
        """Emergency lock: force locks & unmounts all vaults immediately."""
        self.status_var.set("EMERGENCY PANIC PROTOCOL ACTIVE // DISMOUNTING ALL...")
        def task():
            count = vhd_manager.panic_dismount_all()
            self.after(0, lambda: messagebox.showwarning(
                "Panic Dismount Complete",
                f"Emergency lock executed.\n\nDismounted and locked {count} active vault(s)."
            ))
            self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def refresh_list(self):
        self.status_var.set("SCANNING STORAGE ROOT...")
        def task():
            try:
                containers = vhd_manager.list_containers()
                self.after(0, lambda: self.render_vault_cards(containers))
            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"SCAN FAILED: {e}"))
        threading.Thread(target=task, daemon=True).start()

    def render_vault_cards(self, containers):
        for widget in self.vaults_frame.winfo_children():
            widget.destroy()

        if not containers:
            empty_box = ctk.CTkFrame(self.vaults_frame, fg_color=theme.COLOR_SURFACE_1,
                                     corner_radius=theme.CORNER_RADIUS_CARD,
                                     border_width=1, border_color=theme.COLOR_BORDER)
            empty_box.pack(fill="x", pady=40, padx=20)
            
            ctk.CTkLabel(empty_box, text="[ NO ENCRYPTED CONTAINERS DETECTED ]", font=theme.FONT_HEADING,
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(pady=(30, 8))
            ctk.CTkLabel(empty_box, text="Use [+ NEW VAULT] above to provision your first encrypted VHDX vault.",
                         font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_SECONDARY).pack(pady=(0, 30))
            self.status_var.set("SYSTEM STATUS: 0 VAULTS FOUND")
            return

        for idx, c in enumerate(containers, 1):
            self.create_card(idx, c)

        self.status_var.set(f"SYSTEM STATUS: {len(containers)} VAULT(S) REGISTERED // READY")

    def create_card(self, idx: int, c):
        card = ctk.CTkFrame(self.vaults_frame, fg_color=theme.COLOR_SURFACE_1,
                            corner_radius=theme.CORNER_RADIUS_CARD,
                            border_width=1, border_color=theme.COLOR_BORDER)
        card.pack(fill="x", pady=6, padx=5)

        # Top row: Index, Name, Status Badge, Size
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(14, 6))

        # Title / Index
        ctk.CTkLabel(top_row, text=f"[ {idx:02d} // {c.name.upper()} ]", font=theme.FONT_BODY_BOLD,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(side="left")

        # Status badge
        if c.is_mounted:
            if c.bitlocker_status == "Locked":
                stat_text = f"● LOCKED [{c.drive_letter or '?'}]"
                stat_color = theme.COLOR_ACCENT_RED
            elif c.bitlocker_status == "Unlocked":
                stat_text = f"● MOUNTED [{c.drive_letter or '?'}]"
                stat_color = theme.COLOR_ACCENT_GREEN
            else:
                stat_text = f"● MOUNTED (NO BITLOCKER)"
                stat_color = theme.COLOR_ACCENT_YELLOW
        else:
            stat_text = "○ DISMOUNTED"
            stat_color = theme.COLOR_TEXT_DIM

        ctk.CTkLabel(top_row, text=stat_text, font=theme.FONT_STATUS,
                     text_color=stat_color).pack(side="left", padx=15)

        # Size & Date
        date_str = f"CREATED: {c.created_date}" if c.created_date else ""
        ctk.CTkLabel(top_row, text=f"{date_str}   CAPACITY: {c.size_gb:.2f} GB", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(side="right")

        # Storage capacity bar (if mounted and readable)
        if c.is_mounted and c.used_gb is not None:
            meter_box = ctk.CTkFrame(card, fg_color="transparent")
            meter_box.pack(fill="x", padx=16, pady=(2, 6))
            
            pct = (c.usage_percent or 0) / 100.0
            pbar = ctk.CTkProgressBar(meter_box, height=6, corner_radius=1,
                                     progress_color=theme.COLOR_TEXT_PRIMARY,
                                     fg_color=theme.COLOR_SURFACE_3)
            pbar.set(pct)
            pbar.pack(side="left", fill="x", expand=True, padx=(0, 15))
            
            txt = f"{c.used_gb:.2f} GB / {c.size_gb:.2f} GB ({c.usage_percent:.1f}% USED)"
            ctk.CTkLabel(meter_box, text=txt, font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_SECONDARY).pack(side="right")

        # Action bar
        act_row = ctk.CTkFrame(card, fg_color="transparent")
        act_row.pack(fill="x", padx=16, pady=(6, 12))

        # Mount / Dismount
        if c.is_mounted:
            if c.drive_letter:
                ctk.CTkButton(act_row, text="↗ OPEN", width=75, height=26, font=theme.FONT_CAPTION,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: os.startfile(d)).pack(side="left", padx=3)

            ctk.CTkButton(act_row, text="⏹ DISMOUNT", width=95, height=26, font=theme.FONT_CAPTION,
                          fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                          corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=c.path: self.run_dismount(p)).pack(side="left", padx=3)

            # BitLocker Controls
            if c.bitlocker_status == "Locked" and c.drive_letter:
                ctk.CTkButton(act_row, text="🔓 UNLOCK", width=85, height=26, font=theme.FONT_CAPTION,
                              fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                              hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.prompt_unlock(d)).pack(side="left", padx=3)
            elif c.bitlocker_status == "Unlocked" and c.drive_letter:
                ctk.CTkButton(act_row, text="🔒 LOCK", width=75, height=26, font=theme.FONT_CAPTION,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.run_lock(d)).pack(side="left", padx=3)
            elif c.bitlocker_status == "Off" and c.drive_letter:
                ctk.CTkButton(act_row, text="🛡 ENCRYPT", width=90, height=26, font=theme.FONT_CAPTION,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.prompt_encrypt(d)).pack(side="left", padx=3)

            if c.drive_letter:
                ctk.CTkButton(act_row, text="🔍 CHKDSK", width=85, height=26, font=theme.FONT_CAPTION,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.run_diagnostic(d)).pack(side="left", padx=3)
        else:
            ctk.CTkButton(act_row, text="▶ MOUNT", width=85, height=26, font=theme.FONT_CAPTION,
                          fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                          hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=c.path: self.run_mount(p)).pack(side="left", padx=3)

        # Snapshot backup
        ctk.CTkButton(act_row, text="💾 BACKUP", width=85, height=26, font=theme.FONT_CAPTION,
                      fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                      corner_radius=theme.CORNER_RADIUS_BTN,
                      command=lambda p=c.path: self.run_snapshot(p)).pack(side="left", padx=3)

        # Delete (Right aligned)
        ctk.CTkButton(act_row, text="🗑 DELETE", width=80, height=26, font=theme.FONT_CAPTION,
                      fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_ACCENT_RED,
                      corner_radius=theme.CORNER_RADIUS_BTN,
                      command=lambda p=c.path, n=c.name: self.confirm_delete(p, n)).pack(side="right", padx=3)

    def run_mount(self, path):
        self.status_var.set(f"MOUNTING // {os.path.basename(path)}...")
        def task():
            try:
                vhd_manager.mount_container(path)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Mount Error", str(e)))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def run_dismount(self, path):
        self.status_var.set(f"DISMOUNTING // {os.path.basename(path)}...")
        def task():
            try:
                vhd_manager.dismount_container(path)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Dismount Error", str(e)))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def run_lock(self, drive_letter):
        def task():
            try:
                bitlocker.lock_volume(drive_letter)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Lock Error", str(e)))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def prompt_unlock(self, drive_letter):
        def do_unlock(pwd):
            self.status_var.set(f"AUTHENTICATING // UNLOCKING {drive_letter}...")
            def task():
                try:
                    bitlocker.unlock_volume_password(drive_letter, pwd)
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Unlock Error", str(e)))
                finally:
                    self.after(0, self.refresh_list)
            threading.Thread(target=task, daemon=True).start()
        PasswordPromptModal(self, "UNLOCK // BITLOCKER", f"Enter passphrase for volume {drive_letter}:", do_unlock)

    def prompt_encrypt(self, drive_letter):
        def do_encrypt(pwd):
            self.status_var.set(f"ENCRYPTING // ACTIVATING XTS-AES 256 ON {drive_letter}...")
            def task():
                try:
                    bitlocker.enable_bitlocker(drive_letter, pwd)
                    self.after(0, lambda: messagebox.showinfo("BitLocker Activated", f"Volume {drive_letter} is now protected with BitLocker XTS-AES 256!"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Encryption Error", str(e)))
                finally:
                    self.after(0, self.refresh_list)
            threading.Thread(target=task, daemon=True).start()
        PasswordPromptModal(self, "ENCRYPT // BITLOCKER", f"Set passphrase for volume {drive_letter}:", do_encrypt)

    def run_diagnostic(self, drive_letter):
        self.status_var.set(f"RUNNING DIAGNOSTIC ON {drive_letter}...")
        def task():
            out = BackupManager.run_disk_diagnostic(drive_letter)
            self.after(0, lambda: messagebox.showinfo(f"Diagnostic Report: {drive_letter}", out[:1500]))
            self.after(0, lambda: self.status_var.set("DIAGNOSTIC COMPLETED."))
        threading.Thread(target=task, daemon=True).start()

    def run_snapshot(self, path):
        self.status_var.set(f"CREATING SNAPSHOT FOR {os.path.basename(path)}...")
        def task():
            try:
                meta = BackupManager.create_backup(path)
                self.after(0, lambda: messagebox.showinfo(
                    "Snapshot Created",
                    f"Backup created:\n{meta['backup_name']}\n\nSHA-256:\n{meta['checksum']}"
                ))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Backup Failed", str(e)))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def confirm_delete(self, path, name):
        if self.sm.is_2fa_enabled():
            def on_2fa_ok(code):
                if self.sm.verify_token(code):
                    self.execute_delete(path)
                else:
                    messagebox.showerror("Authentication Failed", "Invalid 2FA token. Delete aborted.")
            PasswordPromptModal(self, "2FA AUTHORIZATION", "Enter 6-digit Authenticator code to authorize deletion:", on_2fa_ok)
        else:
            if messagebox.askyesno("CONFIRM DELETION", f"Permanently delete container:\n{name}?\n\nThis action is irreversible."):
                self.execute_delete(path)

    def execute_delete(self, path):
        def task():
            try:
                vhd_manager.delete_container(path)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Delete Failed", str(e)))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

def run_gui():
    app = App()
    app.mainloop()
