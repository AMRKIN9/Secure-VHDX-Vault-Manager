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
# IN-APP TOAST NOTIFICATION FLYOUT (WITH ANIMATED TIMEOUT BAR)
# ==============================================================================

class ToastFlyout(ctk.CTkFrame):
    """
    Floating in-app notification banner with an animated shrinking timeout bar.
    Disappears automatically after duration_ms without annoying system notifications.
    """
    def __init__(self, master, title: str, message: str, toast_type: str = "info", duration_ms: int = 4000):
        badge_text = "[ ℹ ]"
        badge_color = theme.COLOR_TEXT_PRIMARY
        bar_color = theme.COLOR_TEXT_PRIMARY
        border_color = theme.COLOR_BORDER
        
        if toast_type == "success":
            badge_text = "[ ✓ ]"
            badge_color = theme.COLOR_ACCENT_GREEN
            bar_color = theme.COLOR_ACCENT_GREEN
            border_color = theme.COLOR_ACCENT_GREEN
        elif toast_type in ("warning", "error"):
            badge_text = "[ ! ]"
            badge_color = theme.COLOR_ACCENT_RED
            bar_color = theme.COLOR_ACCENT_RED
            border_color = theme.COLOR_ACCENT_RED

        super().__init__(master, fg_color=theme.COLOR_SURFACE_2, corner_radius=theme.CORNER_RADIUS_CARD,
                         border_width=1, border_color=border_color)
                         
        self.duration_ms = duration_ms
        self.remaining_ms = duration_ms
        self.step_interval = 40

        top_box = ctk.CTkFrame(self, fg_color="transparent")
        top_box.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(top_box, text=badge_text, font=theme.FONT_HEADING,
                     text_color=badge_color).pack(side="left", padx=(0, 12))

        text_box = ctk.CTkFrame(top_box, fg_color="transparent")
        text_box.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(text_box, text=title.upper(), font=theme.FONT_BODY,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(text_box, text=message, font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY, wraplength=480).pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(top_box, text="✕", width=28, height=28, font=theme.FONT_CAPTION,
                      fg_color="transparent", hover_color=theme.COLOR_SURFACE_HOVER,
                      text_color=theme.COLOR_TEXT_SECONDARY, command=self.dismiss).pack(side="right", padx=(10, 0))

        # Animated Timeout Bar
        self.progress_bar = ctk.CTkProgressBar(self, height=4, corner_radius=1,
                                               progress_color=bar_color, fg_color=theme.COLOR_SURFACE_3)
        self.progress_bar.set(1.0)
        self.progress_bar.pack(fill="x", padx=6, pady=(0, 6))

        self.update_timer()

    def update_timer(self):
        self.remaining_ms -= self.step_interval
        if self.remaining_ms <= 0:
            self.dismiss()
        else:
            pct = max(0.0, self.remaining_ms / self.duration_ms)
            self.progress_bar.set(pct)
            self.after(self.step_interval, self.update_timer)

    def dismiss(self):
        try:
            self.destroy()
        except Exception:
            pass

# ==============================================================================
# MODALS & DIALOGS
# ==============================================================================

class NothingModal(ctk.CTkToplevel):
    def __init__(self, parent, title: str, width: int = 440, height: int = 500):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.configure(fg_color=theme.COLOR_BG_ROOT)
        
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        py = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{max(10, px)}+{max(10, py)}")
        
        self.transient(parent)
        self.grab_set()

class SmoothConfirmModal(NothingModal):
    """Smooth confirmation modal with custom styling and destructive option."""
    def __init__(self, parent, title: str, message: str, detail: str, confirm_text: str,
                 callback, is_destructive: bool = False):
        super().__init__(parent, title, width=440, height=260)
        self.callback = callback
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        btn_color = theme.COLOR_ACCENT_RED if is_destructive else theme.COLOR_TEXT_PRIMARY
        btn_text_color = theme.COLOR_TEXT_PRIMARY if is_destructive else theme.COLOR_BG_ROOT
        hover_color = theme.COLOR_ACCENT_RED_HOVER if is_destructive else "#DDDDDD"

        ctk.CTkLabel(pad_frame, text=title.upper(), font=theme.FONT_HEADING,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 8))
                     
        ctk.CTkLabel(pad_frame, text=message, font=theme.FONT_BODY,
                     text_color=theme.COLOR_TEXT_PRIMARY, wraplength=380).pack(anchor="w", padx=20, pady=(0, 4))
                     
        if detail:
            ctk.CTkLabel(pad_frame, text=detail, font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_SECONDARY, wraplength=380).pack(anchor="w", padx=20, pady=(0, 20))
                         
        btn_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(10, 15))
        
        ctk.CTkButton(btn_box, text=f"[ {confirm_text.upper()} ]", font=theme.FONT_BUTTON, height=36,
                      fg_color=btn_color, text_color=btn_text_color, hover_color=hover_color,
                      corner_radius=theme.CORNER_RADIUS_BTN, command=self.on_confirm).pack(side="left", expand=True, fill="x", padx=(0, 6))
                      
        ctk.CTkButton(btn_box, text="[ CANCEL ]", font=theme.FONT_BUTTON, height=36,
                      fg_color=theme.COLOR_SURFACE_3, text_color=theme.COLOR_TEXT_SECONDARY,
                      hover_color=theme.COLOR_SURFACE_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.destroy).pack(side="right", expand=True, fill="x", padx=(6, 0))

    def on_confirm(self):
        self.destroy()
        self.callback()

class CreateVaultModal(NothingModal):
    def __init__(self, parent, callback):
        super().__init__(parent, "CREATE // NEW VAULT", width=480, height=540)
        self.callback = callback
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(pad_frame, text="[ + NEW ENCRYPTED CONTAINER ]", font=theme.FONT_HEADING,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(pad_frame, text="VAULT IDENTIFIER / NAME", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20, pady=(5, 2))
        self.name_entry = ctk.CTkEntry(pad_frame, placeholder_text="MySecureVault", font=theme.FONT_BODY,
                                       height=36, fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                       text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.name_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(pad_frame, text="CAPACITY (GIGABYTES)", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(anchor="w", padx=20, pady=(5, 2))
        self.size_entry = ctk.CTkEntry(pad_frame, placeholder_text="10", font=theme.FONT_BODY,
                                       height=36, fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                       text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.size_entry.insert(0, "10")
        self.size_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        self.dynamic_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(pad_frame, text="DYNAMIC EXPANSION (Grows on demand)", font=theme.FONT_CAPTION,
                      variable=self.dynamic_var, progress_color=theme.COLOR_TEXT_PRIMARY,
                      fg_color=theme.COLOR_SURFACE_3).pack(anchor="w", padx=20, pady=5)
        
        self.automount_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(pad_frame, text="AUTO-MOUNT UPON INITIALIZATION", font=theme.FONT_CAPTION,
                      variable=self.automount_var, progress_color=theme.COLOR_TEXT_PRIMARY,
                      fg_color=theme.COLOR_SURFACE_3).pack(anchor="w", padx=20, pady=5)
        
        ctk.CTkLabel(pad_frame, text="BITLOCKER XTS-AES 256 PASSPHRASE (OPTIONAL)", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_ACCENT_RED).pack(anchor="w", padx=20, pady=(15, 2))
        self.pwd_entry = ctk.CTkEntry(pad_frame, placeholder_text="Leave blank to format without password", show="*",
                                      font=theme.FONT_BODY, height=36, fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                      text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.pwd_entry.pack(fill="x", padx=20, pady=(0, 20))
        
        btn_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(5, 15))
        
        ctk.CTkButton(btn_box, text="[ CREATE VAULT ]", font=theme.FONT_BUTTON, height=36,
                      fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                      hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.on_create).pack(side="left", expand=True, fill="x", padx=(0, 5))
                      
        ctk.CTkButton(btn_box, text="[ CANCEL ]", font=theme.FONT_BUTTON, height=36,
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
    def __init__(self, parent, security_manager: SecurityManager, on_updated_callback):
        super().__init__(parent, "SECURITY // GOOGLE AUTHENTICATOR", width=500, height=680)
        self.sm = security_manager
        self.on_updated = on_updated_callback
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(pad_frame, text="[ 2FA // GOOGLE AUTHENTICATOR ]", font=theme.FONT_HEADING,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(15, 5))
                     
        is_active = self.sm.is_2fa_enabled()
        status_text = "STATUS: ACTIVE (PROTECTED)" if is_active else "STATUS: INACTIVE (UNCONFIGURED)"
        status_color = theme.COLOR_ACCENT_GREEN if is_active else theme.COLOR_ACCENT_RED
        ctk.CTkLabel(pad_frame, text=f"● {status_text}", font=theme.FONT_CAPTION,
                     text_color=status_color).pack(anchor="w", padx=20, pady=(0, 10))
        
        if not is_active:
            self.pending_secret = self.sm.generate_secret()
            uri = self.sm.get_totp_uri(self.pending_secret)
            
            qr_pil = self.sm.generate_qr_image(uri, size=210)
            self.qr_img = ctk.CTkImage(light_image=qr_pil, dark_image=qr_pil, size=(210, 210))
            
            qr_frame = ctk.CTkFrame(pad_frame, fg_color="#FFFFFF", corner_radius=4, border_width=1, border_color="#FFFFFF")
            qr_frame.pack(pady=6)
            ctk.CTkLabel(qr_frame, image=self.qr_img, text="").pack(padx=6, pady=6)
            
            ctk.CTkLabel(pad_frame, text=f"MANUAL KEY: {self.pending_secret}", font=theme.FONT_METADATA,
                         text_color=theme.COLOR_TEXT_SECONDARY).pack(pady=(2, 6))

            # Live token comparison readout
            self.live_sync_lbl = ctk.CTkLabel(pad_frame, text="", font=theme.FONT_STATUS,
                                             text_color=theme.COLOR_ACCENT_GREEN)
            self.live_sync_lbl.pack(pady=(0, 10))
            self.update_live_token()
            
            ctk.CTkLabel(pad_frame, text="ENTER 6-DIGIT CODE FROM YOUR PHONE:", font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(2, 2))
                         
            self.code_entry = ctk.CTkEntry(pad_frame, placeholder_text="000000", font=theme.FONT_HEADING,
                                           height=40, justify="center", fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                           text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
            self.code_entry.pack(fill="x", padx=20, pady=(0, 15))
            
            ctk.CTkButton(pad_frame, text="[ VERIFY & ENABLE 2FA ]", font=theme.FONT_BUTTON, height=38,
                          fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                          hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                          command=self.on_enable).pack(fill="x", padx=20, pady=(0, 10))
        else:
            ctk.CTkLabel(pad_frame, text="Two-Factor Authentication is actively protecting sensitive vault operations.",
                         font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_SECONDARY, wraplength=420).pack(padx=20, pady=25)

            # Live token verification readout for active 2FA
            self.live_sync_lbl = ctk.CTkLabel(pad_frame, text="", font=theme.FONT_STATUS,
                                             text_color=theme.COLOR_ACCENT_GREEN)
            self.live_sync_lbl.pack(pady=(0, 15))
            self.pending_secret = self.sm.get_secret()
            self.update_live_token()
                         
            ctk.CTkLabel(pad_frame, text="ENTER 6-DIGIT CODE TO DISABLE 2FA:", font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(10, 2))
                         
            self.code_entry = ctk.CTkEntry(pad_frame, placeholder_text="000000", font=theme.FONT_HEADING,
                                           height=40, justify="center", fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                           text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
            self.code_entry.pack(fill="x", padx=20, pady=(0, 20))
            
            ctk.CTkButton(pad_frame, text="[ DISABLE 2FA ]", font=theme.FONT_BUTTON, height=38,
                          fg_color=theme.COLOR_ACCENT_RED, text_color=theme.COLOR_TEXT_PRIMARY,
                          hover_color=theme.COLOR_ACCENT_RED_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                          command=self.on_disable).pack(fill="x", padx=20, pady=(0, 10))

    def update_live_token(self):
        try:
            if hasattr(self, 'pending_secret') and self.pending_secret:
                cur_code = self.sm.get_current_token(self.pending_secret)
                rem_sec = self.sm.get_time_remaining()
                self.live_sync_lbl.configure(text=f"PC LIVE TOKEN: [ {cur_code} ]  (EXPIRES IN {rem_sec}s)")
            self.after(1000, self.update_live_token)
        except Exception:
            pass

    def on_enable(self):
        token = self.code_entry.get().strip()
        if self.sm.enable_2fa(self.pending_secret, token):
            messagebox.showinfo("Success", "Two-Factor Authentication successfully enabled!", parent=self)
            self.on_updated()
            self.destroy()
        else:
            messagebox.showerror(
                "Authentication Failed",
                "Invalid code.\n\n"
                "Tip: Look at the 'PC LIVE TOKEN' above. If it differs from your phone, your phone or computer clock is out of sync by more than 90 seconds.",
                parent=self
            )

    def on_disable(self):
        token = self.code_entry.get().strip()
        if self.sm.disable_2fa(token):
            messagebox.showinfo("Success", "Two-Factor Authentication disabled.", parent=self)
            self.on_updated()
            self.destroy()
        else:
            messagebox.showerror("Error", "Invalid authentication token.", parent=self)

class PasswordPromptModal(NothingModal):
    def __init__(self, parent, title: str, prompt: str, callback):
        super().__init__(parent, title, width=420, height=250)
        self.callback = callback
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(pad_frame, text=prompt, font=theme.FONT_BODY,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 10))
                     
        self.entry = ctk.CTkEntry(pad_frame, placeholder_text="Enter passphrase", show="*", font=theme.FONT_BODY,
                                  height=38, fg_color=theme.COLOR_SURFACE_2, border_color=theme.COLOR_BORDER,
                                  text_color=theme.COLOR_TEXT_PRIMARY, corner_radius=theme.CORNER_RADIUS_BTN)
        self.entry.pack(fill="x", padx=20, pady=(0, 20))
        self.entry.focus()
        
        btn_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(btn_box, text="[ CONFIRM ]", font=theme.FONT_BUTTON, height=36,
                      fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                      hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.on_ok).pack(side="left", expand=True, fill="x", padx=(0, 5))
                      
        ctk.CTkButton(btn_box, text="[ CANCEL ]", font=theme.FONT_BUTTON, height=36,
                      fg_color=theme.COLOR_SURFACE_3, text_color=theme.COLOR_TEXT_SECONDARY,
                      hover_color=theme.COLOR_SURFACE_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.destroy).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def on_ok(self):
        val = self.entry.get()
        if val:
            self.callback(val)
            self.destroy()

class BackupManagerModal(NothingModal):
    def __init__(self, parent, vhdx_list, app_ref):
        super().__init__(parent, "SYSTEM // VAULT BACKUPS", width=700, height=560)
        self.vhdx_list = vhdx_list
        self.app_ref = app_ref
        
        pad_frame = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, corner_radius=theme.CORNER_RADIUS_CARD,
                                 border_width=theme.BORDER_WIDTH, border_color=theme.COLOR_BORDER)
        pad_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        header_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        header_box.pack(fill="x", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(header_box, text="[ BACKUP ARCHIVES & ROLLBACKS ]", font=theme.FONT_HEADING,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(side="left")
                     
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
            ctk.CTkLabel(self.scroll, text="NO ARCHIVES FOUND IN BACKUP STORAGE.",
                         font=theme.FONT_CAPTION, text_color=theme.COLOR_TEXT_DIM).pack(pady=50)
            return
            
        for b in backups:
            b_path = b.get("backup_path", "")
            b_name = b.get("backup_name", "Unknown")
            b_size = b.get("size_gb", 0)
            
            card = ctk.CTkFrame(self.scroll, fg_color=theme.COLOR_SURFACE_3, corner_radius=theme.CORNER_RADIUS_BTN,
                                border_width=1, border_color=theme.COLOR_BORDER)
            card.pack(fill="x", pady=6, padx=5)
            
            top_line = ctk.CTkFrame(card, fg_color="transparent")
            top_line.pack(fill="x", padx=14, pady=(10, 4))
            
            ctk.CTkLabel(top_line, text=b_name, font=theme.FONT_BODY,
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(top_line, text=f"{b_size} GB", font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_SECONDARY).pack(side="right")
                         
            meta_line = ctk.CTkFrame(card, fg_color="transparent")
            meta_line.pack(fill="x", padx=14, pady=(2, 10))
            
            ctk.CTkLabel(meta_line, text=f"DATE: {b.get('timestamp', '-')}  |  SHA: {b.get('checksum', '')[:16]}...",
                         font=theme.FONT_CAPTION, text_color=theme.COLOR_TEXT_SECONDARY).pack(side="left")

            # Action Suite for each Backup: Rollback, Verify, Delete
            act_box = ctk.CTkFrame(meta_line, fg_color="transparent")
            act_box.pack(side="right")

            ctk.CTkButton(act_box, text="↺ ROLLBACK", font=theme.FONT_BUTTON, width=95, height=28,
                          fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                          hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=b_path, n=b_name, s=b_size: self.confirm_rollback(p, n, s)).pack(side="left", padx=2)

            ctk.CTkButton(act_box, text="🔍 VERIFY", font=theme.FONT_BUTTON, width=80, height=28,
                          fg_color=theme.COLOR_SURFACE_1, hover_color=theme.COLOR_SURFACE_HOVER,
                          corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=b_path: self.verify_file(p)).pack(side="left", padx=2)

            ctk.CTkButton(act_box, text="🗑 DELETE", font=theme.FONT_BUTTON, width=80, height=28,
                          fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_ACCENT_RED,
                          corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=b_path, n=b_name, s=b_size: self.confirm_delete_backup(p, n, s)).pack(side="left", padx=2)

    def confirm_rollback(self, backup_path, name, size):
        def do_rollback():
            self.status_lbl.configure(text=f"Rolling back to {name}...")
            self.app_ref.show_toast("Rollback Started", f"Restoring vault from {name}...", "info")
            def task():
                try:
                    target_path = BackupManager.restore_backup(backup_path)
                    self.after(0, lambda: self.app_ref.show_toast("Rollback Complete", f"Successfully restored {os.path.basename(target_path)} from backup.", "success", 5000))
                    self.after(0, lambda: self.status_lbl.configure(text="ROLLBACK SUCCESSFUL.", text_color=theme.COLOR_ACCENT_GREEN))
                except Exception as e:
                    self.after(0, lambda: self.app_ref.show_toast("Rollback Failed", str(e), "error", 6000))
                    self.after(0, lambda: self.status_lbl.configure(text="ROLLBACK FAILED.", text_color=theme.COLOR_ACCENT_RED))
                finally:
                    self.after(0, self.app_ref.refresh_list)
            threading.Thread(target=task, daemon=True).start()

        SmoothConfirmModal(
            self,
            title="RESTORE VAULT // ROLLBACK",
            message=f"Roll back active vault to this backup state?",
            detail=f"Archive: {name} ({size} GB)\n\nNote: The active vault will be overwritten with this snapshot. SHA-256 seal will be validated first.",
            confirm_text="RESTORE NOW",
            callback=do_rollback,
            is_destructive=False
        )

    def confirm_delete_backup(self, backup_path, name, size):
        def do_delete():
            BackupManager.delete_backup(backup_path)
            self.app_ref.show_toast("Backup Deleted", f"Removed archive {name}.", "info")
            self.refresh_backups()

        SmoothConfirmModal(
            self,
            title="DELETE BACKUP ARCHIVE",
            message=f"Permanently delete this backup archive?",
            detail=f"Archive: {name} ({size} GB)\n\nThis will remove the VHDX snapshot and its .sha256 seal.",
            confirm_text="DELETE ARCHIVE",
            callback=do_delete,
            is_destructive=True
        )

    def verify_file(self, path):
        self.status_lbl.configure(text=f"Verifying SHA-256 seal for {os.path.basename(path)}...")
        def task():
            valid = BackupManager.verify_backup(path)
            res_txt = "VALID (HASH MATCHES)" if valid else "CORRUPTED / MISMATCH"
            self.after(0, lambda: self.status_lbl.configure(
                text=f"INTEGRITY: {res_txt}",
                text_color=theme.COLOR_ACCENT_GREEN if valid else theme.COLOR_ACCENT_RED
            ))
            self.after(0, lambda: self.app_ref.show_toast(
                "Integrity Verified" if valid else "Checksum Mismatch",
                f"SHA-256 Seal for {os.path.basename(path)}: {res_txt}",
                "success" if valid else "error"
            ))
        threading.Thread(target=task, daemon=True).start()

# ==============================================================================
# MAIN APPLICATION WINDOW
# ==============================================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SECURE // VHDX VAULT MANAGER")
        self.geometry("1000x720")
        self.minsize(920, 600)
        self.configure(fg_color=theme.COLOR_BG_ROOT)
        
        self.current_toast = None
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

    def show_toast(self, title: str, message: str, toast_type: str = "info", duration_ms: int = 4000):
        """Displays a clean in-app toast flyout banner at the top of the window."""
        if self.current_toast:
            try:
                self.current_toast.destroy()
            except Exception:
                pass

        toast = ToastFlyout(self, title=title, message=message, toast_type=toast_type, duration_ms=duration_ms)
        self.current_toast = toast
        toast.place(relx=0.5, y=25, anchor="n")

    def build_ui(self):
        # 1. Elevation Warning Banner (if not admin)
        if not self.is_elevated:
            elevate_bar = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_2, height=44, corner_radius=0,
                                       border_width=1, border_color=theme.COLOR_ACCENT_RED)
            elevate_bar.pack(fill="x")
            
            ctk.CTkLabel(elevate_bar, text="[ ⚠ RESTRICTED PRIVILEGES ] Administrator rights required to attach & encrypt virtual disks.",
                         font=theme.FONT_CAPTION, text_color=theme.COLOR_ACCENT_RED).pack(side="left", padx=16, pady=8)
                         
            ctk.CTkButton(elevate_bar, text="[ ELEVATE AS ADMIN ]", font=theme.FONT_BUTTON, width=160, height=28,
                          fg_color=theme.COLOR_ACCENT_RED, text_color=theme.COLOR_TEXT_PRIMARY,
                          hover_color=theme.COLOR_ACCENT_RED_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                          command=elevate_privileges).pack(side="right", padx=16, pady=8)

        # 2. Main Header Bar
        header = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, height=72, corner_radius=0,
                              border_width=1, border_color=theme.COLOR_BORDER)
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=12)
        
        ctk.CTkLabel(title_box, text="● SECURE // VHDX VAULT MANAGER", font=theme.FONT_TITLE,
                     text_color=theme.COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_box, text="BUILD 2.5.0 [NOTHING_EDITION] // 256-BIT ENCRYPTION // RFC 6238 TOTP",
                     font=theme.FONT_CAPTION, text_color=theme.COLOR_TEXT_SECONDARY).pack(anchor="w")

        # Top Action Suite
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=16, pady=12)
        
        ctk.CTkButton(btn_box, text="↻ REFRESH", width=95, height=34, font=theme.FONT_BUTTON,
                      fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_SURFACE_HOVER,
                      corner_radius=theme.CORNER_RADIUS_BTN, command=self.refresh_list).pack(side="left", padx=4)
                      
        ctk.CTkButton(btn_box, text="+ NEW VAULT", width=120, height=34, font=theme.FONT_BUTTON,
                      fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                      hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.open_create_modal).pack(side="left", padx=4)
                      
        self.btn_2fa = ctk.CTkButton(btn_box, text=self.get_2fa_btn_text(), width=110, height=34, font=theme.FONT_BUTTON,
                                     fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_SURFACE_HOVER,
                                     corner_radius=theme.CORNER_RADIUS_BTN, command=self.open_2fa_modal)
        self.btn_2fa.pack(side="left", padx=4)
        
        ctk.CTkButton(btn_box, text="💾 BACKUPS", width=105, height=34, font=theme.FONT_BUTTON,
                      fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_SURFACE_HOVER,
                      corner_radius=theme.CORNER_RADIUS_BTN, command=self.open_backups_modal).pack(side="left", padx=4)
                      
        ctk.CTkButton(btn_box, text="! PANIC LOCK", width=120, height=34, font=theme.FONT_BUTTON,
                      fg_color=theme.COLOR_ACCENT_RED, text_color=theme.COLOR_TEXT_PRIMARY,
                      hover_color=theme.COLOR_ACCENT_RED_HOVER, corner_radius=theme.CORNER_RADIUS_BTN,
                      command=self.panic_lock).pack(side="left", padx=(8, 0))

        # 3. Scrollable Vaults View Area
        self.vaults_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.vaults_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # 4. Bottom Industrial Telemetry Bar
        self.telemetry = ctk.CTkFrame(self, fg_color=theme.COLOR_SURFACE_1, height=34, corner_radius=0,
                                      border_width=1, border_color=theme.COLOR_BORDER)
        self.telemetry.pack(fill="x", side="bottom")
        
        self.status_var = tk.StringVar(value="SYSTEM STATUS: IDLE")
        ctk.CTkLabel(self.telemetry, textvariable=self.status_var, font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(side="left", padx=16, pady=6)
                     
        storage_dir = vhd_manager.get_storage_dir()
        ctk.CTkLabel(self.telemetry, text=f"STORAGE ROOT: {storage_dir}", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_DIM).pack(side="right", padx=16, pady=6)

    def get_2fa_btn_text(self):
        return "[ 2FA: ACTIVE ]" if self.sm.is_2fa_enabled() else "[ 2FA: OFF ]"

    def open_create_modal(self):
        CreateVaultModal(self, self.create_vault)

    def open_2fa_modal(self):
        TwoFactorModal(self, self.sm, on_updated_callback=lambda: self.btn_2fa.configure(text=self.get_2fa_btn_text()))

    def open_backups_modal(self):
        BackupManagerModal(self, vhd_manager.list_containers(), app_ref=self)

    def create_vault(self, name, size_gb, dynamic, automount, password):
        self.status_var.set(f"CREATING VAULT // {name}...")
        self.show_toast("Creating Vault", f"Initializing {name} ({size_gb} GB)...", "info")
        def task():
            try:
                vhd_manager.create_container(name, size_gb, dynamic, automount, password)
                self.after(0, lambda: self.show_toast("Vault Created", f"Successfully provisioned {name}.", "success"))
                self.after(0, lambda: self.status_var.set("VAULT CREATED SUCCESSFULLY."))
            except Exception as e:
                err_msg = str(e)
                if "elevation" in err_msg.lower() or "740" in err_msg:
                    err_msg = "Administrator rights required to partition disk. Please click [ELEVATE AS ADMIN]."
                self.after(0, lambda: self.show_toast("Creation Failed", err_msg, "error", 6000))
                self.after(0, lambda: self.status_var.set("CREATION ERROR."))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def panic_lock(self):
        self.status_var.set("EMERGENCY PANIC PROTOCOL ACTIVE // DISMOUNTING ALL...")
        def task():
            count = vhd_manager.panic_dismount_all()
            self.after(0, lambda: self.show_toast(
                "Panic Lock Engaged",
                f"Emergency protocol executed: {count} active vault(s) dismounted and locked.",
                "warning",
                5000
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
                         text_color=theme.COLOR_TEXT_PRIMARY).pack(pady=(35, 10))
            ctk.CTkLabel(empty_box, text="Use [+ NEW VAULT] above to provision your first encrypted VHDX vault.",
                         font=theme.FONT_BODY, text_color=theme.COLOR_TEXT_SECONDARY).pack(pady=(0, 35))
            self.status_var.set("SYSTEM STATUS: 0 VAULTS FOUND")
            return

        for idx, c in enumerate(containers, 1):
            self.create_card(idx, c)

        self.status_var.set(f"SYSTEM STATUS: {len(containers)} VAULT(S) REGISTERED // READY")

    def create_card(self, idx: int, c):
        card = ctk.CTkFrame(self.vaults_frame, fg_color=theme.COLOR_SURFACE_1,
                            corner_radius=theme.CORNER_RADIUS_CARD,
                            border_width=1, border_color=theme.COLOR_BORDER)
        card.pack(fill="x", pady=7, padx=5)

        # Top row: Index, Name, Status Badge, Size
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(top_row, text=f"[ {idx:02d} // {c.name.upper()} ]", font=theme.FONT_HEADING,
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
                stat_text = f"● MOUNTED (NO ENCRYPTION)"
                stat_color = theme.COLOR_ACCENT_YELLOW
        else:
            stat_text = "○ DISMOUNTED"
            stat_color = theme.COLOR_TEXT_DIM

        ctk.CTkLabel(top_row, text=stat_text, font=theme.FONT_STATUS,
                     text_color=stat_color).pack(side="left", padx=16)

        date_str = f"CREATED: {c.created_date}" if c.created_date else ""
        ctk.CTkLabel(top_row, text=f"{date_str}   CAPACITY: {c.size_gb:.2f} GB", font=theme.FONT_CAPTION,
                     text_color=theme.COLOR_TEXT_SECONDARY).pack(side="right")

        # Storage capacity bar (if mounted and readable)
        if c.is_mounted and c.used_gb is not None:
            meter_box = ctk.CTkFrame(card, fg_color="transparent")
            meter_box.pack(fill="x", padx=16, pady=(4, 8))
            
            pct = (c.usage_percent or 0) / 100.0
            pbar = ctk.CTkProgressBar(meter_box, height=8, corner_radius=2,
                                      progress_color=theme.COLOR_TEXT_PRIMARY,
                                      fg_color=theme.COLOR_SURFACE_3)
            pbar.set(pct)
            pbar.pack(side="left", fill="x", expand=True, padx=(0, 16))
            
            txt = f"{c.used_gb:.2f} GB / {c.size_gb:.2f} GB ({c.usage_percent:.1f}% USED)"
            ctk.CTkLabel(meter_box, text=txt, font=theme.FONT_CAPTION,
                         text_color=theme.COLOR_TEXT_SECONDARY).pack(side="right")

        # Action bar
        act_row = ctk.CTkFrame(card, fg_color="transparent")
        act_row.pack(fill="x", padx=16, pady=(8, 14))

        if c.is_mounted:
            if c.drive_letter:
                ctk.CTkButton(act_row, text="↗ OPEN", width=80, height=32, font=theme.FONT_BUTTON,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: os.startfile(d)).pack(side="left", padx=3)

            ctk.CTkButton(act_row, text="⏹ DISMOUNT", width=105, height=32, font=theme.FONT_BUTTON,
                          fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                          corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=c.path, n=c.name: self.run_dismount(p, n)).pack(side="left", padx=3)

            # BitLocker Controls
            if c.bitlocker_status == "Locked" and c.drive_letter:
                ctk.CTkButton(act_row, text="🔓 UNLOCK", width=95, height=32, font=theme.FONT_BUTTON,
                              fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                              hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.prompt_unlock(d)).pack(side="left", padx=3)
            elif c.bitlocker_status == "Unlocked" and c.drive_letter:
                ctk.CTkButton(act_row, text="🔒 LOCK", width=85, height=32, font=theme.FONT_BUTTON,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.run_lock(d)).pack(side="left", padx=3)
                
                # Option to DECRYPT / remove BitLocker for clean unencrypted file extraction
                ctk.CTkButton(act_row, text="🔓 DECRYPT (CLEAN)", width=135, height=32, font=theme.FONT_BUTTON,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.prompt_decrypt(d)).pack(side="left", padx=3)
            elif c.bitlocker_status == "Off" and c.drive_letter:
                ctk.CTkButton(act_row, text="🛡 LIVE ENCRYPT", width=125, height=32, font=theme.FONT_BUTTON,
                              fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                              hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.prompt_encrypt(d)).pack(side="left", padx=3)

            if c.drive_letter:
                ctk.CTkButton(act_row, text="🔍 CHKDSK", width=95, height=32, font=theme.FONT_BUTTON,
                              fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                              corner_radius=theme.CORNER_RADIUS_BTN,
                              command=lambda d=c.drive_letter: self.run_diagnostic(d)).pack(side="left", padx=3)
        else:
            ctk.CTkButton(act_row, text="▶ MOUNT", width=95, height=32, font=theme.FONT_BUTTON,
                          fg_color=theme.COLOR_TEXT_PRIMARY, text_color=theme.COLOR_BG_ROOT,
                          hover_color="#DDDDDD", corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=c.path, n=c.name: self.run_mount(p, n)).pack(side="left", padx=3)

            # Dismounted encrypt helper: Mounts first, then activates live encryption
            ctk.CTkButton(act_row, text="🛡 ENCRYPT", width=100, height=32, font=theme.FONT_BUTTON,
                          fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                          corner_radius=theme.CORNER_RADIUS_BTN,
                          command=lambda p=c.path: self.mount_and_encrypt(p)).pack(side="left", padx=3)

        ctk.CTkButton(act_row, text="💾 BACKUP", width=95, height=32, font=theme.FONT_BUTTON,
                      fg_color=theme.COLOR_SURFACE_3, hover_color=theme.COLOR_SURFACE_HOVER,
                      corner_radius=theme.CORNER_RADIUS_BTN,
                      command=lambda p=c.path: self.run_snapshot(p)).pack(side="left", padx=3)

        ctk.CTkButton(act_row, text="🗑 DELETE", width=90, height=32, font=theme.FONT_BUTTON,
                      fg_color=theme.COLOR_SURFACE_2, hover_color=theme.COLOR_ACCENT_RED,
                      corner_radius=theme.CORNER_RADIUS_BTN,
                      command=lambda p=c.path, n=c.name: self.confirm_delete(p, n)).pack(side="right", padx=3)

    def run_mount(self, path, name):
        self.status_var.set(f"MOUNTING // {name}...")
        self.show_toast("Mounting Vault", f"Attaching {name} to Windows...", "info")
        def task():
            try:
                vhd_manager.mount_container(path)
                self.after(0, lambda: self.show_toast("Vault Mounted", f"{name} is now attached and ready.", "success"))
            except Exception as e:
                err_msg = str(e)
                if "elevation" in err_msg.lower() or "740" in err_msg:
                    err_msg = "Administrator rights required to mount disk. Please click [ELEVATE AS ADMIN]."
                self.after(0, lambda: self.show_toast("Mount Failed", err_msg, "error", 5000))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def run_dismount(self, path, name):
        self.status_var.set(f"DISMOUNTING // {name}...")
        self.show_toast("Dismounting", f"Detaching {name}...", "info")
        def task():
            try:
                vhd_manager.dismount_container(path)
                self.after(0, lambda: self.show_toast("Vault Dismounted", f"{name} safely detached.", "success"))
            except Exception as e:
                self.after(0, lambda: self.show_toast("Dismount Failed", str(e), "error", 5000))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def run_lock(self, drive_letter):
        def task():
            try:
                bitlocker.lock_volume(drive_letter)
                self.after(0, lambda: self.show_toast("Volume Locked", f"BitLocker keys flushed for {drive_letter}.", "warning"))
            except Exception as e:
                self.after(0, lambda: self.show_toast("Lock Error", str(e), "error"))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def prompt_unlock(self, drive_letter):
        def do_unlock(pwd):
            self.status_var.set(f"AUTHENTICATING // UNLOCKING {drive_letter}...")
            self.show_toast("Authenticating", f"Verifying BitLocker password for {drive_letter}...", "info")
            def task():
                try:
                    bitlocker.unlock_volume_password(drive_letter, pwd)
                    self.after(0, lambda: self.show_toast("Vault Unlocked", f"Drive {drive_letter} is now open and accessible.", "success"))
                except Exception as e:
                    self.after(0, lambda: self.show_toast("Unlock Failed", f"Incorrect password or unlock error: {e}", "error", 5000))
                finally:
                    self.after(0, self.refresh_list)
            threading.Thread(target=task, daemon=True).start()
        PasswordPromptModal(self, "UNLOCK // BITLOCKER", f"Enter passphrase for volume {drive_letter}:", do_unlock)

    def prompt_encrypt(self, drive_letter):
        def do_encrypt(pwd):
            self.status_var.set(f"ENCRYPTING // ACTIVATING XTS-AES 256 ON {drive_letter}...")
            self.show_toast("Live Encryption Started", f"Activating BitLocker on {drive_letter}...", "info")
            def task():
                try:
                    bitlocker.enable_bitlocker(drive_letter, pwd)
                    self.after(0, lambda: self.show_toast(
                        "Live Encryption Activated",
                        f"Drive {drive_letter} is now actively protected with BitLocker XTS-AES 256!",
                        "success",
                        5000
                    ))
                except Exception as e:
                    self.after(0, lambda: self.show_toast("Encryption Error", str(e), "error", 6000))
                finally:
                    self.after(0, self.refresh_list)
            threading.Thread(target=task, daemon=True).start()
        PasswordPromptModal(self, "LIVE ENCRYPTION // BITLOCKER", f"Set encryption passphrase for drive {drive_letter}:", do_encrypt)

    def prompt_decrypt(self, drive_letter):
        def do_decrypt():
            self.status_var.set(f"DECRYPTING // REMOVING BITLOCKER FROM {drive_letter}...")
            self.show_toast("Decryption In Progress", f"Removing BitLocker from {drive_letter}. Files will be clean.", "info")
            def task():
                try:
                    bitlocker.disable_bitlocker(drive_letter)
                    self.after(0, lambda: self.show_toast(
                        "Decryption Complete",
                        f"Drive {drive_letter} is now clean and unencrypted.",
                        "success",
                        5000
                    ))
                except Exception as e:
                    self.after(0, lambda: self.show_toast("Decryption Error", str(e), "error", 5000))
                finally:
                    self.after(0, self.refresh_list)
            threading.Thread(target=task, daemon=True).start()

        SmoothConfirmModal(
            self,
            title="REMOVE BITLOCKER ENCRYPTION",
            message=f"Remove BitLocker encryption from {drive_letter}?",
            detail="The volume will be decrypted LIVE. All files will remain clean and accessible without a password.",
            confirm_text="DECRYPT DRIVE",
            callback=do_decrypt,
            is_destructive=False
        )

    def mount_and_encrypt(self, path):
        """Helper for dismounted vaults: Mounts first, then prompts for live encryption."""
        name = os.path.basename(path)
        self.show_toast("Mount Required", f"Attaching {name} to a drive letter before enabling BitLocker...", "info", 4000)
        def task():
            try:
                vhd_manager.mount_container(path)
                time.sleep(1.5)
                is_mounted, drive_letter = vhd_manager._get_vhd_info(path)
                if is_mounted and drive_letter:
                    self.after(0, lambda d=drive_letter: self.prompt_encrypt(d))
                else:
                    self.after(0, lambda: self.show_toast("Mount Notice", "Vault mounted. Click [LIVE ENCRYPT] once drive letter appears.", "info"))
            except Exception as e:
                self.after(0, lambda: self.show_toast("Mount Failed", str(e), "error", 5000))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def run_diagnostic(self, drive_letter):
        self.status_var.set(f"RUNNING DIAGNOSTIC ON {drive_letter}...")
        self.show_toast("Running Diagnostic", f"Scanning volume {drive_letter} health...", "info")
        def task():
            out = BackupManager.run_disk_diagnostic(drive_letter)
            self.after(0, lambda: messagebox.showinfo(f"Diagnostic Report: {drive_letter}", out[:1500]))
            self.after(0, lambda: self.status_var.set("DIAGNOSTIC COMPLETED."))
        threading.Thread(target=task, daemon=True).start()

    def run_snapshot(self, path):
        name = os.path.basename(path)
        self.status_var.set(f"CREATING SNAPSHOT FOR {name}...")
        self.show_toast("Backup Started", f"Creating SHA-256 sealed snapshot of {name}...", "info")
        def task():
            try:
                meta = BackupManager.create_backup(path)
                self.after(0, lambda: self.show_toast(
                    "Snapshot Complete",
                    f"Saved {meta['backup_name']} with SHA-256 seal.",
                    "success",
                    5000
                ))
            except Exception as e:
                self.after(0, lambda: self.show_toast("Backup Error", str(e), "error", 5000))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

    def confirm_delete(self, path, name):
        if self.sm.is_2fa_enabled():
            def on_2fa_ok(code):
                if self.sm.verify_token(code):
                    self.execute_delete(path, name)
                else:
                    self.show_toast("2FA Failed", "Invalid authentication token. Deletion aborted.", "error")
            PasswordPromptModal(self, "2FA AUTHORIZATION", "Enter 6-digit Authenticator code to authorize deletion:", on_2fa_ok)
        else:
            SmoothConfirmModal(
                self,
                title="PERMANENTLY DELETE VAULT",
                message=f"Permanently delete container {name}?",
                detail="All encrypted contents inside this VHDX file will be destroyed. This cannot be undone.",
                confirm_text="DELETE PERMANENTLY",
                callback=lambda: self.execute_delete(path, name),
                is_destructive=True
            )

    def execute_delete(self, path, name):
        def task():
            try:
                vhd_manager.delete_container(path)
                self.after(0, lambda: self.show_toast("Vault Deleted", f"{name} was permanently removed.", "info"))
            except Exception as e:
                self.after(0, lambda: self.show_toast("Delete Failed", str(e), "error", 5000))
            finally:
                self.after(0, self.refresh_list)
        threading.Thread(target=task, daemon=True).start()

def run_gui():
    app = App()
    app.mainloop()
