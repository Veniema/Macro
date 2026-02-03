import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import threading
import json
import os
import sys
from typing import List, Any, Sequence

from pynput import mouse
import pyautogui

from actions import format_action
from executor import MacroExecutor


Action = Sequence[Any]


class MacroMaker:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("Macro Maker Pro v2.2.1 - Complete Edition")
        master.geometry("900x700")

        # Actions are tuples/lists describing the macro steps
        self.actions: List[Action] = []
        self.loop_count: int = 1

        # Auto delay between recorded actions
        self.auto_delay = tk.BooleanVar(value=False)
        self.auto_delay_time = tk.DoubleVar(value=0.5)

        # Execution engine
        self.executor: MacroExecutor | None = None
        self.executor_thread: threading.Thread | None = None
        self.macro_running: bool = False

        # File tracking
        self.current_file: str | None = None

        # Build UI
        self._setup_ui()
        self._setup_shortcuts()

        # DPI-awareness + pyautogui failsafe on Windows
        try:
            pyautogui.FAILSAFE = True  # move mouse to top-left to abort
            if sys.platform.startswith("win"):
                import ctypes
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        """Initialize the user interface"""
        self._create_menu()
        self._create_status_bar()
        self._create_recording_buttons()
        self._create_quick_actions()
        self._create_control_buttons()
        self._create_execution_controls()
        self._create_actions_list()

    def _create_menu(self) -> None:
        """Create the menu bar"""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Macro (Ctrl+N)", command=self.new_macro)
        file_menu.add_command(label="Open Macro (Ctrl+O)", command=self.load_macro)
        file_menu.add_command(label="Save Macro (Ctrl+S)", command=self.save_macro)
        file_menu.add_command(label="Save As...", command=self.save_macro_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)

    def _create_status_bar(self) -> None:
        """Create the status bar"""
        status_frame = tk.Frame(self.master)
        status_frame.pack(fill=tk.X, padx=5, pady=2)
        self.status_label = tk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)

    def _create_recording_buttons(self) -> None:
        """Create the main recording buttons"""
        record_frame = tk.Frame(self.master)
        record_frame.pack(pady=4)

        record_btns = [
            ("🖱️ Click", self.record_click),
            ("↗️ Drag", self.record_drag),
            ("⏱️ Delay", self.add_delay),
            ("📋 Copy", self.record_copy),
            ("📄 Paste", self.record_paste),
            ("👁️ OCR", self.record_ocr),
            ("🔍 Img Check", self.record_img_check),
            ("⌨️ Key", self.record_key),
        ]

        for i, (text, cmd) in enumerate(record_btns):
            tk.Button(record_frame, text=text, command=cmd, width=10).grid(row=0, column=i, padx=2)

    def _create_quick_actions(self) -> None:
        """Create quick action buttons for common sequences"""
        quick_frame = tk.Frame(self.master)
        quick_frame.pack(pady=2)

        tk.Label(quick_frame, text="Quick Actions:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        candidates = [
            ("Click + Copy", "_quick_click_copy"),
            ("Click + Paste", "_quick_click_paste"),
            ("Drag + Copy", "_quick_drag_copy"),
            ("Triple Click", "_quick_triple_click"),
            ("Ctrl+A + Copy", "_quick_select_all_copy"),
        ]
        for text, meth in candidates:
            if hasattr(self, meth):
                tk.Button(quick_frame, text=text, command=getattr(self, meth),
                          font=("Arial", 8), pady=1).pack(side=tk.LEFT, padx=1)

    def _create_control_buttons(self) -> None:
        """Create action control buttons"""
        control_frame = tk.Frame(self.master)
        control_frame.pack(pady=4)

        control_btns = [
            ("✏️ Edit", self.edit_action),
            ("🗑️ Delete", self.delete_action),
            ("📋 Duplicate", self.duplicate_action),
            ("⬆️ Move Up", self.move_up),
            ("⬇️ Move Down", self.move_down),
            ("💾 Insert Delay", self.insert_delay),
        ]

        for i, (text, cmd) in enumerate(control_btns):
            tk.Button(control_frame, text=text, command=cmd, width=10).grid(row=0, column=i, padx=2)

    def _create_execution_controls(self) -> None:
        """Create execution control panel"""
        exec_frame = tk.Frame(self.master)
        exec_frame.pack(pady=4)

        tk.Label(exec_frame, text="Loops:").grid(row=0, column=0, padx=2)
        tk.Button(exec_frame, text="Set Count", command=self.set_loop, width=8).grid(row=0, column=1, padx=2)
        self.loop_label = tk.Label(exec_frame, text=f"{self.loop_count}", font=("Arial", 10, "bold"))
        self.loop_label.grid(row=0, column=2, padx=5)

        tk.Checkbutton(exec_frame, text="Auto Delay", variable=self.auto_delay).grid(row=0, column=3, padx=5)
        tk.Entry(exec_frame, textvariable=self.auto_delay_time, width=5).grid(row=0, column=4, padx=2)
        tk.Label(exec_frame, text="s").grid(row=0, column=5)

        self.start_btn = tk.Button(
            exec_frame,
            text="▶️ Start (F5)",
            command=self.start_macro,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
        )
        self.start_btn.grid(row=0, column=6, padx=5)

        self.stop_btn = tk.Button(
            exec_frame,
            text="⏹️ Stop (Esc)",
            command=self.stop_macro,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
            state=tk.DISABLED,
        )
        self.stop_btn.grid(row=0, column=7, padx=5)

        tk.Button(exec_frame, text="🔍 Preview", command=self.preview_macro, width=8).grid(row=0, column=8, padx=2)
        tk.Button(exec_frame, text="🗑️ Clear All", command=self.clear_actions, width=10).grid(row=0, column=9, padx=2)

    def _create_actions_list(self) -> None:
        """Create the actions listbox with scrollbar"""
        list_frame = tk.Frame(self.master)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            list_frame,
            width=100,
            height=15,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            selectmode=tk.SINGLE,
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

    def _setup_shortcuts(self) -> None:
        """Set up all keyboard shortcuts"""
        self.master.bind("<Control-n>", lambda e: self.new_macro())
        self.master.bind("<Control-o>", lambda e: self.load_macro())
        self.master.bind("<Control-s>", lambda e: self.save_macro())
        self.master.bind("<Delete>", lambda e: self.delete_action())
        self.master.bind("<F5>", lambda e: self.start_macro())
        self.master.bind("<Escape>", lambda e: self.stop_macro())
        self.master.bind("<Control-k>", lambda e: self.record_key())

        self.master.bind("<Control-r>", lambda e: self.start_macro())
        self.master.bind("<Control-d>", lambda e: self.duplicate_action())
        self.master.bind("<Control-e>", lambda e: self.edit_action())
        self.master.bind("<Control-t>", lambda e: self._quick_click_copy())
        self.master.bind("<Control-y>", lambda e: self._quick_click_paste())

        self.master.title(
            "Macro Maker Pro v2.2.1 | Ctrl+R=Run | Ctrl+T=QuickCopy | Ctrl+Y=QuickPaste | Ctrl+K=Key"
        )

    # ------------------------------------------------------------------ #
    # Status / macro metadata
    # ------------------------------------------------------------------ #

    def update_status(self, message: str) -> None:
        """Update the status bar message"""
        self.status_label.config(text=message)

    # ------------------------------------------------------------------ #
    # File operations
    # ------------------------------------------------------------------ #

    def new_macro(self) -> None:
        """Create a new macro"""
        if self.actions and not messagebox.askyesno("New Macro", "Clear current macro?"):
            return
        self.actions = []
        self.listbox.delete(0, tk.END)
        self.current_file = None
        self.master.title("Macro Maker Pro v2.2.1")
        self.update_status("New macro created")

    def save_macro(self) -> None:
        """Save the current macro"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.save_macro_as()

    def save_macro_as(self) -> None:
        """Save macro with file dialog"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")],
            title="Save Macro As",
        )
        if filename:
            self._save_to_file(filename)

    def _save_to_file(self, filename: str) -> None:
        """Save macro data to file"""
        try:
            macro_data = {
                "actions": self.actions,
                "loop_count": self.loop_count,
                "auto_delay": self.auto_delay.get(),
                "auto_delay_time": self.auto_delay_time.get(),
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(macro_data, f, indent=2)

            self.current_file = filename
            self.master.title(f"Macro Maker Pro v2.2.1 - {os.path.basename(filename)}")
            self.update_status(f"Saved: {filename}")
            messagebox.showinfo("Save", f"Macro saved to {filename}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save macro:\n{e}")

    def load_macro(self) -> None:
        """Load macro from file"""
        if self.actions and not messagebox.askyesno("Load Macro", "Replace current macro?"):
            return

        filename = filedialog.askopenfilename(
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")],
            title="Load Macro",
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                macro_data = json.load(f)

            self.actions = macro_data.get("actions", [])
            self.loop_count = int(macro_data.get("loop_count", 1))
            self.auto_delay.set(bool(macro_data.get("auto_delay", False)))
            self.auto_delay_time.set(float(macro_data.get("auto_delay_time", 0.5)))

            # Refresh UI
            self.listbox.delete(0, tk.END)
            for action in self.actions:
                self.listbox.insert(tk.END, format_action(action))

            self.loop_label.config(text=f"{self.loop_count}")
            self.current_file = filename
            self.master.title(f"Macro Maker Pro v2.2.1 - {os.path.basename(filename)}")
            self.update_status(f"Loaded: {filename}")
            messagebox.showinfo("Load", f"Macro loaded from {filename}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load macro:\n{e}")

    # ------------------------------------------------------------------ #
    # Small helpers
    # ------------------------------------------------------------------ #

    def _maybe_auto_delay(self) -> None:
        """Add auto delay if enabled"""
        if self.auto_delay.get():
            d = float(self.auto_delay_time.get())
            action = ("delay", d)
            self.actions.append(action)
            self.listbox.insert(tk.END, format_action(action))
            self.update_status(f"Auto delay added: {d:.2f}s")

    # ------------------------------------------------------------------ #
    # Recording methods
    # ------------------------------------------------------------------ #

    def _repick_click(self, idx: int) -> None:
        """Let the user click on screen to set new (x,y) for a click action."""
        self.update_status("Click anywhere to set new coordinates…")
        messagebox.showinfo("Edit Click", "Click anywhere to set the new coordinates.")

        def on_click(x, y, button, pressed):
            if pressed:
                self.actions[idx] = ("click", int(x), int(y))

                def _update():
                    self.listbox.delete(idx)
                    self.listbox.insert(idx, format_action(self.actions[idx]))
                    self.listbox.select_clear(0, tk.END)
                    self.listbox.select_set(idx)
                    self.update_status(f"Click edited → ({int(x)}, {int(y)})")

                self.master.after(0, _update)
                return False

        mouse.Listener(on_click=on_click).start()

    def record_click(self) -> None:
        """Record a mouse click"""
        self.update_status("Click anywhere to record this click...")
        messagebox.showinfo("Record Click", "Click anywhere to record this click.")

        def on_click(x, y, button, pressed):
            if pressed:
                action = ("click", int(x), int(y))
                self.actions.append(action)

                def _update():
                    self.listbox.insert(tk.END, format_action(action))
                    self._maybe_auto_delay()
                    self.update_status("Click recorded successfully")

                self.master.after(0, _update)
                return False

        mouse.Listener(on_click=on_click).start()

    def record_drag(self) -> None:
        """Record a mouse drag"""
        self.update_status("Click and drag to record this action...")
        messagebox.showinfo("Record Drag", "Click and drag to record this action.")

        coords: List[tuple[int, int]] = []

        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((int(x), int(y)))
            else:
                coords.append((int(x), int(y)))
                if len(coords) == 2:
                    action = ("drag", coords[0], coords[1])
                    self.actions.append(action)

                    def _update():
                        self.listbox.insert(tk.END, format_action(action))
                        self._maybe_auto_delay()
                        self.update_status("Drag recorded successfully")

                    self.master.after(0, _update)
                    return False

        mouse.Listener(on_click=on_click).start()

    def record_copy(self) -> None:
        """Record a copy action"""
        action = ("copy",)
        self.actions.append(action)
        self.listbox.insert(tk.END, format_action(action))
        self._maybe_auto_delay()
        self.update_status("Copy action added")

    def record_paste(self) -> None:
        """Record a paste action"""
        action = ("paste",)
        self.actions.append(action)
        self.listbox.insert(tk.END, format_action(action))
        self._maybe_auto_delay()
        self.update_status("Paste action added")

    def record_ocr(self) -> None:
        """Record an OCR action with enhanced options"""
        self.update_status("Click upper-left then lower-right to define OCR region...")
        messagebox.showinfo(
            "Record OCR Region", "Click upper-left then release lower-right to define OCR region."
        )

        coords: List[tuple[int, int]] = []

        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((int(x), int(y)))
            else:
                coords.append((int(x), int(y)))
                if len(coords) == 2:
                    self.master.after(0, lambda: self._configure_ocr_options(coords))
                    return False

        mouse.Listener(on_click=on_click).start()

    def _configure_ocr_options(self, coords: List[tuple[int, int]]) -> None:
        """Configure OCR options through a dialog"""
        dialog = tk.Toplevel(self.master)
        dialog.title("OCR Configuration")
        dialog.geometry("500x400")
        dialog.transient(self.master)
        dialog.grab_set()

        mode_var = tk.StringVar(value="all_text")
        pattern_var = tk.StringVar()
        processing_var = tk.StringVar(value="copy")

        tk.Label(dialog, text="OCR Configuration", font=("Arial", 14, "bold")).pack(pady=10)

        mode_frame = tk.LabelFrame(dialog, text="What to Extract", padx=10, pady=10)
        mode_frame.pack(fill="x", padx=10, pady=5)

        tk.Radiobutton(
            mode_frame, text="All text (copy everything)", variable=mode_var, value="all_text"
        ).pack(anchor="w")
        tk.Radiobutton(
            mode_frame, text="Numbers only (any digits found)", variable=mode_var, value="numbers"
        ).pack(anchor="w")
        tk.Radiobutton(
            mode_frame, text="Email addresses", variable=mode_var, value="email"
        ).pack(anchor="w")
        tk.Radiobutton(
            mode_frame, text="Custom pattern (regex)", variable=mode_var, value="custom"
        ).pack(anchor="w")

        pattern_frame = tk.LabelFrame(dialog, text="Custom Pattern (if selected)", padx=10, pady=10)
        pattern_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(pattern_frame, text="Regex pattern:").pack(anchor="w")
        pattern_entry = tk.Entry(pattern_frame, textvariable=pattern_var, width=50)
        pattern_entry.pack(fill="x", pady=2)

        tk.Label(
            pattern_frame,
            text=r"Examples: \d{4,8} (4-8 digits), \b\w+@\w+\.\w+\b (emails)",
            font=("Arial", 8),
            fg="gray",
        ).pack(anchor="w")

        process_frame = tk.LabelFrame(dialog, text="What to do with extracted text", padx=10, pady=10)
        process_frame.pack(fill="x", padx=10, pady=5)

        tk.Radiobutton(
            process_frame, text="Copy to clipboard", variable=processing_var, value="copy"
        ).pack(anchor="w")
        tk.Radiobutton(
            process_frame,
            text="Save to variable (show in status)",
            variable=processing_var,
            value="show",
        ).pack(anchor="w")
        tk.Radiobutton(
            process_frame,
            text="Copy first match only",
            variable=processing_var,
            value="first",
        ).pack(anchor="w")
        tk.Radiobutton(
            process_frame,
            text="Copy all matches (separated by spaces)",
            variable=processing_var,
            value="all",
        ).pack(anchor="w")

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)

        def save_ocr():
            mode = mode_var.get()
            pattern = pattern_var.get() if mode == "custom" else ""
            processing = processing_var.get()

            if mode == "custom" and not pattern:
                messagebox.showwarning("Missing Pattern", "Please enter a regex pattern for custom mode.")
                return

            (x1, y1), (x2, y2) = coords
            action = ("ocr", (x1, y1, x2, y2), mode, pattern, processing)
            self.actions.append(action)
            self.listbox.insert(tk.END, format_action(action))
            self._maybe_auto_delay()
            self.update_status(f"OCR region added: {mode} mode")
            dialog.destroy()

        def cancel_ocr():
            self.update_status("OCR recording cancelled")
            dialog.destroy()

        tk.Button(
            button_frame,
            text="Add OCR Action",
            command=save_ocr,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
        ).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel_ocr).pack(side="left", padx=5)

        pattern_entry.focus_set()

    def record_img_check(self) -> None:
        """Record an image check action with branching logic"""
        image_path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*"),
            ],
            title="Select Reference Image",
        )
        if not image_path:
            self.update_status("Image check cancelled")
            return

        self.update_status("Click and drag to define search region...")
        messagebox.showinfo(
            "Define Search Region",
            "Click and drag to define the region where the image should be found.",
        )

        coords: List[tuple[int, int]] = []

        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((int(x), int(y)))
            else:
                coords.append((int(x), int(y)))
                if len(coords) == 2:
                    self.master.after(
                        0, lambda: self._finish_img_check_recording(coords, image_path)
                    )
                    return False

        mouse.Listener(on_click=on_click).start()

    def _finish_img_check_recording(
        self,
        coords: List[tuple[int, int]],
        image_path: str,
    ) -> None:
        (x1, y1), (x2, y2) = coords

        threshold = simpledialog.askfloat(
            "Image Similarity",
            "Enter similarity threshold (0.0-1.0, higher = more strict):",
            initialvalue=0.8,
            minvalue=0.0,
            maxvalue=1.0,
        )
        if threshold is None:
            threshold = 0.8

        # Ask if this image check should wait until the image appears
        wait_until_found = messagebox.askyesno(
            "Wait Until Found?",
            "Do you want this Image Check to keep checking until the image is found?\n\n"
            "Yes = poll the region until the image appears.\n"
            "No  = check once and continue.",
        )

        max_wait_seconds = 0.0
        if wait_until_found:
            # NEW: Ask for a maximum wait time (in minutes, 0 = no limit)
            max_wait_minutes = simpledialog.askfloat(
                "Max Wait Time",
                "Maximum wait time (minutes, 0 = no limit):",
                initialvalue=1.0,  # 1 minute default
                minvalue=0.0,
            )
            if max_wait_minutes is None:
                max_wait_minutes = 1.0
            max_wait_seconds = float(max_wait_minutes) * 60.0

        sub_actions = self._create_sub_actions_dialog()

        # Backward-compatible storage of config: either float or dict
        if wait_until_found:
            config = {
                "threshold": float(threshold),
                "wait": True,
                "interval": 0.5,  # polling interval in seconds
                "timeout": max_wait_seconds,  # 0 = no timeout; else seconds
            }
        else:
            config = float(threshold)

        action = ("img_check", image_path, (x1, y1, x2, y2), sub_actions, config)
        self.actions.append(action)
        self.listbox.insert(tk.END, format_action(action))
        self._maybe_auto_delay()

        img_name = os.path.basename(image_path)
        self.update_status(f"Image check added: {img_name} with {len(sub_actions)} sub-actions")


    def _create_sub_actions_dialog(self) -> List[Action]:
        """Create a dialog to define sub-actions for image check branching"""
        sub_actions: List[Action] = []

        dialog = tk.Toplevel(self.master)
        dialog.title("Define Sub-Actions")
        dialog.geometry("620x420")
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Define actions to execute when image IS found:",
            font=("Arial", 12, "bold"),
        ).pack(pady=10)

        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        sub_listbox = tk.Listbox(frame)
        sub_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=sub_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sub_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        def add_click():
            messagebox.showinfo(
                "Record Click", "Click anywhere to record this click for sub-actions."
            )
            dialog.withdraw()

            def on_click(x, y, button, pressed):
                if pressed:
                    action = ("click", int(x), int(y))
                    sub_actions.append(action)

                    def _update():
                        sub_listbox.insert(tk.END, format_action(action))
                        dialog.deiconify()

                    self.master.after(0, _update)
                    return False

            mouse.Listener(on_click=on_click).start()

        def add_delay():
            d = simpledialog.askfloat("Delay", "Enter delay in seconds:", initialvalue=1.0)
            if d is not None:
                action = ("delay", float(d))
                sub_actions.append(action)
                sub_listbox.insert(tk.END, format_action(action))

        def add_copy():
            action = ("copy",)
            sub_actions.append(action)
            sub_listbox.insert(tk.END, format_action(action))

        def add_paste():
            action = ("paste",)
            sub_actions.append(action)
            sub_listbox.insert(tk.END, format_action(action))

        def add_click_found():
            action = ("click_found",)
            sub_actions.append(action)
            sub_listbox.insert(tk.END, format_action(action))

        def remove_action():
            selection = sub_listbox.curselection()
            if selection:
                idx = selection[0]
                sub_actions.pop(idx)
                sub_listbox.delete(idx)

        tk.Button(btn_frame, text="Add Click", command=add_click).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Add Delay", command=add_delay).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Add Copy", command=add_copy).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Add Paste", command=add_paste).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Click Found Image", command=add_click_found).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(btn_frame, text="Remove", command=remove_action).pack(side=tk.LEFT, padx=2)

        def done():
            dialog.destroy()

        tk.Button(dialog, text="Done", command=done, font=("Arial", 12, "bold")).pack(pady=10)

        dialog.wait_window()
        return sub_actions

    def record_key(self) -> None:
        """Create a key-press action (e.g., Arrow Down × N at an interval)."""
        dialog = tk.Toplevel(self.master)
        dialog.title("Add Keyboard Command")
        dialog.geometry("360x260")
        dialog.transient(self.master)
        dialog.grab_set()

        try:
            known = sorted(pyautogui.KEYBOARD_KEYS)
        except Exception:
            known = [
                "up",
                "down",
                "left",
                "right",
                "enter",
                "tab",
                "esc",
                "space",
                "backspace",
                "delete",
                "home",
                "end",
                "pageup",
                "pagedown",
            ] + [f"f{i}" for i in range(1, 13)]

        key_var = tk.StringVar(value="down")
        count_var = tk.IntVar(value=1)
        interval_var = tk.DoubleVar(value=0.05)

        frm = tk.Frame(dialog)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(frm, text="Key name:").grid(row=0, column=0, sticky="w")
        key_entry = tk.Entry(frm, textvariable=key_var, width=18)
        key_entry.grid(row=0, column=1, sticky="w")

        tk.Label(frm, text="Common:").grid(row=1, column=0, sticky="nw", pady=(8, 0))
        common_list = tk.Listbox(frm, height=8, width=18, exportselection=False)
        for k in [
            "up",
            "down",
            "left",
            "right",
            "enter",
            "tab",
            "esc",
            "space",
            "backspace",
            "delete",
            "home",
            "end",
            "pageup",
            "pagedown",
        ]:
            common_list.insert(tk.END, k)
        common_list.grid(row=1, column=1, sticky="w", pady=(8, 0))

        def pick_key(_evt=None):
            sel = common_list.curselection()
            if sel:
                key_var.set(common_list.get(sel[0]))

        common_list.bind("<<ListboxSelect>>", pick_key)

        tk.Label(frm, text="Count:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        tk.Spinbox(frm, from_=1, to=999, textvariable=count_var, width=6).grid(
            row=2, column=1, sticky="w", pady=(10, 0)
        )

        tk.Label(frm, text="Interval (s):").grid(row=3, column=0, sticky="w", pady=(6, 0))
        tk.Entry(frm, textvariable=interval_var, width=8).grid(
            row=3, column=1, sticky="w", pady=(6, 0)
        )

        btns = tk.Frame(dialog)
        btns.pack(pady=10)

        def add_action():
            key = key_var.get().strip().lower()
            try:
                cnt = max(1, int(count_var.get()))
            except Exception:
                cnt = 1
            try:
                iv = float(interval_var.get())
            except ValueError:
                iv = 0.0

            try:
                known_keys = sorted(pyautogui.KEYBOARD_KEYS)
            except Exception:
                known_keys = []
            if known_keys and key not in known_keys:
                messagebox.showwarning(
                    "Unknown Key",
                    f"'{key}' is not a recognized key.\n\n"
                    f"Try one of: {', '.join(known_keys[:20])} ...",
                )
                return

            action = ("key", key, cnt, iv)
            self.actions.append(action)
            self.listbox.insert(tk.END, format_action(action))
            self._maybe_auto_delay()
            self.update_status(f"Key action added: {key} ×{cnt}")
            dialog.destroy()

        tk.Button(btns, text="Add", command=add_action, bg="#4CAF50", fg="white").pack(
            side="left", padx=6
        )
        tk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=6)

        key_entry.focus_set()

    # ------------------------------------------------------------------ #
    # Quick actions
    # ------------------------------------------------------------------ #

    def _quick_click_copy(self) -> None:
        """Add click followed by copy action"""
        self.update_status("Click where you want to click then copy...")
        messagebox.showinfo("Quick Click+Copy", "Click anywhere to record click + copy sequence.")

        def on_click(x, y, button, pressed):
            if pressed:
                click_action = ("click", int(x), int(y))
                copy_action = ("copy",)
                self.actions.extend([click_action, copy_action])

                def _update():
                    self.listbox.insert(tk.END, format_action(click_action))
                    self.listbox.insert(tk.END, format_action(copy_action))
                    self.update_status("Click + Copy sequence added")

                self.master.after(0, _update)
                return False

        mouse.Listener(on_click=on_click).start()

    def _quick_click_paste(self) -> None:
        """Add click followed by paste action"""
        self.update_status("Click where you want to click then paste...")
        messagebox.showinfo("Quick Click+Paste", "Click anywhere to record click + paste sequence.")

        def on_click(x, y, button, pressed):
            if pressed:
                click_action = ("click", int(x), int(y))
                paste_action = ("paste",)
                self.actions.extend([click_action, paste_action])

                def _update():
                    self.listbox.insert(tk.END, format_action(click_action))
                    self.listbox.insert(tk.END, format_action(paste_action))
                    self.update_status("Click + Paste sequence added")

                self.master.after(0, _update)
                return False

        mouse.Listener(on_click=on_click).start()

    def _quick_drag_copy(self) -> None:
        """Add drag followed by copy action"""
        self.update_status("Drag to select text then auto-copy...")
        messagebox.showinfo("Quick Drag+Copy", "Drag to select text, will auto-add copy action.")

        coords: List[tuple[int, int]] = []

        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((int(x), int(y)))
            else:
                coords.append((int(x), int(y)))
                if len(coords) == 2:
                    drag_action = ("drag", coords[0], coords[1])
                    copy_action = ("copy",)
                    self.actions.extend([drag_action, copy_action])

                    def _update():
                        self.listbox.insert(tk.END, format_action(drag_action))
                        self.listbox.insert(tk.END, format_action(copy_action))
                        self.update_status("Drag + Copy sequence added")

                    self.master.after(0, _update)
                    return False

        mouse.Listener(on_click=on_click).start()

    def _quick_triple_click(self) -> None:
        """Add triple click (select line) action"""
        self.update_status("Click where you want to triple-click...")
        messagebox.showinfo("Triple Click", "Click anywhere to add triple-click action.")

        def on_click(x, y, button, pressed):
            if pressed:
                actions_to_add: List[tuple[Action, str]] = []

                for i in range(3):
                    click_action = ("click", int(x), int(y))
                    self.actions.append(click_action)
                    actions_to_add.append((click_action, f" ({i + 1}/3)"))

                    if i < 2:
                        delay_action = ("delay", 0.05)
                        self.actions.append(delay_action)
                        actions_to_add.append((delay_action, ""))

                def _update():
                    for act, suffix in actions_to_add:
                        self.listbox.insert(tk.END, format_action(act) + suffix)
                    self.update_status("Triple-click sequence added")

                self.master.after(0, _update)
                return False

        mouse.Listener(on_click=on_click).start()

    def _quick_select_all_copy(self) -> None:
        """Add Ctrl+A + Copy sequence"""
        select_action = ("hotkey", "ctrl", "a")
        copy_action = ("copy",)
        self.actions.extend([select_action, copy_action])
        self.listbox.insert(tk.END, format_action(select_action))
        self.listbox.insert(tk.END, format_action(copy_action))
        self.update_status("Select All + Copy sequence added")

    # ------------------------------------------------------------------ #
    # Action management
    # ------------------------------------------------------------------ #

    def add_delay(self) -> None:
        """Add a delay action"""
        d = simpledialog.askfloat(
            "Delay (s)", "Enter delay in seconds:", minvalue=0.0, initialvalue=1.0
        )
        if d is not None:
            action = ("delay", float(d))
            self.actions.append(action)
            self.listbox.insert(tk.END, format_action(action))
            self.update_status(f"Added {d:.2f}s delay")

    def insert_delay(self) -> None:
        """Insert delay after selected action"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action first.")
            return

        d = simpledialog.askfloat(
            "Insert Delay", "Enter delay in seconds:", minvalue=0.0, initialvalue=1.0
        )
        if d is None:
            return

        idx = sel[0] + 1  # insert after selected item
        action = ("delay", float(d))
        self.actions.insert(idx, action)
        self.listbox.insert(idx, format_action(action))
        self.update_status(f"Inserted {d:.2f}s delay")

    def duplicate_action(self) -> None:
        """Duplicate the selected action"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action to duplicate.")
            return

        idx = sel[0]
        original = self.actions[idx]
        # shallow clone, like original behavior
        cloned = list(original) if isinstance(original, list) else tuple(original)
        self.actions.insert(idx + 1, cloned)
        self.listbox.insert(idx + 1, format_action(cloned) + " (copy)")
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(idx + 1)
        self.update_status("Action duplicated")

    def delete_action(self) -> None:
        """Delete the selected action"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action to delete.")
            return

        idx = sel[0]
        self.actions.pop(idx)
        self.listbox.delete(idx)
        self.update_status("Action deleted")

    def move_up(self) -> None:
        """Move selected action up"""
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return

        idx = sel[0]
        self.actions[idx - 1], self.actions[idx] = self.actions[idx], self.actions[idx - 1]

        self.listbox.delete(idx - 1, idx)
        self.listbox.insert(idx - 1, format_action(self.actions[idx - 1]))
        self.listbox.insert(idx, format_action(self.actions[idx]))
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(idx - 1)
        self.update_status("Action moved up")

    def move_down(self) -> None:
        """Move selected action down"""
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.actions) - 1:
            return

        idx = sel[0]
        self.actions[idx], self.actions[idx + 1] = self.actions[idx + 1], self.actions[idx]

        self.listbox.delete(idx, idx + 1)
        self.listbox.insert(idx, format_action(self.actions[idx]))
        self.listbox.insert(idx + 1, format_action(self.actions[idx + 1]))
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(idx + 1)
        self.update_status("Action moved down")

    def edit_action(self) -> None:
        """Edit the selected action (currently supports delay & click)"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action to edit.")
            return

        idx = sel[0]
        act = self.actions[idx]
        if not act:
            return

        typ = act[0]

        if typ == "delay":
            try:
                current = float(act[1])
            except Exception:
                current = 1.0
            new_delay = simpledialog.askfloat(
                "Edit Delay", "Enter new delay:", initialvalue=current
            )
            if new_delay is not None:
                self.actions[idx] = ("delay", float(new_delay))
                self.listbox.delete(idx)
                self.listbox.insert(idx, format_action(self.actions[idx]))
                self.listbox.select_clear(0, tk.END)
                self.listbox.select_set(idx)
                self.update_status("Delay action edited")
            return

        if typ == "click":
            # act = ('click', x, y)
            try:
                x0, y0 = int(act[1]), int(act[2])
            except Exception:
                x0, y0 = 0, 0

            repick = messagebox.askyesno(
                "Edit Click",
                "Do you want to re-pick the coordinates on screen?\n\n"
                "Yes = click to set new (x,y)\nNo = type numbers manually",
            )

            if repick:
                self._repick_click(idx)
                return

            new_x = simpledialog.askinteger("Edit Click", "New X:", initialvalue=x0)
            if new_x is None:
                return
            new_y = simpledialog.askinteger("Edit Click", "New Y:", initialvalue=y0)
            if new_y is None:
                return

            self.actions[idx] = ("click", int(new_x), int(new_y))
            self.listbox.delete(idx)
            self.listbox.insert(idx, format_action(self.actions[idx]))
            self.listbox.select_clear(0, tk.END)
            self.listbox.select_set(idx)
            self.update_status(f"Click edited → ({int(new_x)}, {int(new_y)})")
            return

        messagebox.showinfo("Edit", f"Editing '{typ}' actions is not yet supported.")

    def preview_macro(self) -> None:
        """Show a preview of what the macro will do"""
        if not self.actions:
            messagebox.showwarning("Empty", "No actions to preview.")
            return

        preview_text = f"Macro Preview - Will execute {self.loop_count} time(s):\n\n"
        for i, action in enumerate(self.actions, 1):
            preview_text += f"{i:2d}. {format_action(action)}\n"

        preview_window = tk.Toplevel(self.master)
        preview_window.title("Macro Preview")
        preview_window.geometry("600x400")

        text_widget = tk.Text(preview_window, wrap=tk.WORD, font=("Consolas", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, preview_text)
        text_widget.config(state=tk.DISABLED)

    def clear_actions(self) -> None:
        """Clear all actions"""
        if self.actions and messagebox.askyesno("Clear All", "Clear all actions?"):
            self.actions = []
            self.listbox.delete(0, tk.END)
            self.update_status("All actions cleared")

    def set_loop(self) -> None:
        """Set loop count"""
        count = simpledialog.askinteger(
            "Loop Count", "Enter number of loops:", minvalue=1, initialvalue=self.loop_count
        )
        if count:
            self.loop_count = int(count)
            self.loop_label.config(text=f"{self.loop_count}")
            self.update_status(f"Loop count set to {self.loop_count}")

    # ------------------------------------------------------------------ #
    # Macro execution (using MacroExecutor)
    # ------------------------------------------------------------------ #

    def start_macro(self) -> None:
        """Start macro execution via MacroExecutor"""
        if not self.actions:
            messagebox.showwarning("Empty Macro", "No actions to execute.")
            return

        if self.macro_running:
            messagebox.showwarning("Already Running", "Macro is already running.")
            return

        # Create a new executor instance
        def status_cb(msg: str) -> None:
            # Ensure thread-safe UI updates
            self.master.after(0, lambda m=msg: self.update_status(m))

        def error_cb(msg: str) -> None:
            self.master.after(
                0, lambda m=msg: messagebox.showerror("Execution Error", m)
            )

        def done_cb(ok: bool) -> None:
            self.master.after(0, lambda: self._on_macro_done(ok))

        self.executor = MacroExecutor(
            actions=self.actions,
            loop_count=self.loop_count,
            status_callback=status_cb,
            error_callback=error_cb,
            done_callback=done_cb,
        )

        self.macro_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Run macro in a background thread
        self.executor_thread = threading.Thread(target=self.executor.run, daemon=True)
        self.executor_thread.start()

    def stop_macro(self) -> None:
        """Stop macro execution"""
        self.macro_running = False
        if self.executor and self.executor.running:
            self.executor.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("Macro stopped")

    def _on_macro_done(self, completed_ok: bool) -> None:
        """Called by done_callback when MacroExecutor finishes"""
        self.macro_running = False
        self.executor = None
        self.executor_thread = None

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        if completed_ok:
            self.update_status("Macro completed successfully!")
            messagebox.showinfo("Complete", "Macro execution finished!")
        else:
            # Either user stopped or an error occurred.
            # Error messages are already shown via error_cb.
            self.update_status("Ready")
