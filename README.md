import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import time
import re

from pynput import mouse
import pyautogui
import pyperclip
import mss
from PIL import Image
import pytesseract

class MacroMaker:
    def __init__(self, master):
        self.master = master
        master.title("Macro Maker Pro")

        # Actions: ('click', x, y), ('drag', (x1,y1),(x2,y2)), ('delay', secs),
        #          ('copy',), ('paste',), ('ocr', (x1,y1,x2,y2))
        self.actions = []
        self.loop_count = 1
        self.auto_delay = tk.BooleanVar(value=False)
        self.auto_delay_time = tk.DoubleVar(value=0.5)

        # --- UI Layout ---
        top_frame = tk.Frame(master)
        top_frame.pack(pady=4)
        btns = [
            ("Record Click", self.record_click),
            ("Record Drag",  self.record_drag),
            ("Add Delay",    self.add_delay),
            ("Insert Delay", self.insert_delay),
            ("Copy",         self.record_copy),
            ("Paste",        self.record_paste),
            ("Record OCR Region", self.record_ocr),
            ("Edit Action",  self.edit_action),
            ("Delete Action",self.delete_action),
        ]
        for i, (text, cmd) in enumerate(btns):
            tk.Button(top_frame, text=text, command=cmd).grid(row=0, column=i, padx=4)

        bottom_frame = tk.Frame(master)
        bottom_frame.pack(pady=4)
        tk.Button(bottom_frame, text="Move Up",        command=self.move_up).grid(row=0, column=0, padx=4)
        tk.Button(bottom_frame, text="Move Down",      command=self.move_down).grid(row=0, column=1, padx=4)
        tk.Button(bottom_frame, text="Set Loop Count", command=self.set_loop).grid(row=0, column=2, padx=4)
        tk.Checkbutton(bottom_frame, text="Auto Add Delay", variable=self.auto_delay).grid(row=0, column=3, padx=4)
        tk.Entry(bottom_frame, textvariable=self.auto_delay_time, width=5).grid(row=0, column=4)
        tk.Button(bottom_frame, text="Start Macro ▶", command=self.start_macro).grid(row=0, column=5, padx=4)
        tk.Button(bottom_frame, text="Clear All",      command=self.clear_actions).grid(row=0, column=6, padx=4)

        self.loop_label = tk.Label(master, text=f"Loops: {self.loop_count}")
        self.loop_label.pack()

        self.listbox = tk.Listbox(master, width=100)
        self.listbox.pack(padx=10, pady=10)

    def _maybe_auto_delay(self):
        if self.auto_delay.get():
            d = self.auto_delay_time.get()
            self.actions.append(('delay', d))
            self.listbox.insert(tk.END, f"Delay {d:.2f} s (auto)")

    def record_click(self):
        messagebox.showinfo("Record Click", "Click anywhere to record this click.")
        def on_click(x, y, button, pressed):
            if pressed:
                self.actions.append(('click', x, y))
                self.listbox.insert(tk.END, f"Click at ({x}, {y})")
                self._maybe_auto_delay()
                return False
        mouse.Listener(on_click=on_click).start()

    def record_drag(self):
        messagebox.showinfo("Record Drag", "Click and drag to record this action.")
        coords = []
        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear(); coords.append((x, y))
            else:
                coords.append((x, y))
                if len(coords) == 2:
                    self.actions.append(('drag', coords[0], coords[1]))
                    self.listbox.insert(tk.END, f"Drag from {coords[0]} to {coords[1]}")
                    self._maybe_auto_delay()
                    return False
        mouse.Listener(on_click=on_click).start()

    def record_copy(self):
        self.actions.append(('copy',)); self.listbox.insert(tk.END, "Copy"); self._maybe_auto_delay()

    def record_paste(self):
        self.actions.append(('paste',)); self.listbox.insert(tk.END, "Paste"); self._maybe_auto_delay()

    def record_ocr(self):
        messagebox.showinfo("Record OCR Region", "Click upper-left then release lower-right to define OCR region.")
        coords = []
        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear(); coords.append((x, y))
            else:
                coords.append((x, y))
                if len(coords) == 2:
                    (x1, y1), (x2, y2) = coords
                    self.actions.append(('ocr', (x1, y1, x2, y2)))
                    self.listbox.insert(tk.END, f"OCR region: ({x1},{y1})-({x2},{y2})")
                    self._maybe_auto_delay()
                    return False
        mouse.Listener(on_click=on_click).start()

    def add_delay(self):
        d = simpledialog.askfloat("Delay (s)", "Seconds:", minvalue=0.0)
        if d is not None: self.actions.append(('delay', d)); self.listbox.insert(tk.END, f"Delay {d:.2f} s")

    def insert_delay(self):
        sel = self.listbox.curselection();
        if not sel: messagebox.showwarning("No Selection", "Select an action first."); return
        d = simpledialog.askfloat("Insert Delay", "Seconds:", minvalue=0.0)
        if d is not None: idx = sel[0]; self.actions.insert(idx, ('delay', d)); self.listbox.insert(idx, f"Delay {d:.2f} s")

    def edit_action(self):
        sel = self.listbox.curselection();
        if not sel: messagebox.showwarning("No Selection","Select an action to edit."); return
        i = sel[0]; act = self.actions[i]; typ = act[0]
        if typ == 'click':
            x = simpledialog.askinteger("Edit Click X","New X:",initialvalue=act[1]); y = simpledialog.askinteger("Edit Click Y","New Y:",initialvalue=act[2])
            if x is not None and y is not None: self.actions[i] = ('click', x, y); self.listbox.delete(i); self.listbox.insert(i, f"Click at ({x}, {y})")
        elif typ == 'drag':
            (x1, y1), (x2, y2) = act[1], act[2]
            nx1 = simpledialog.askinteger("Edit Drag X1","New start X:",initialvalue=x1)
            ny1 = simpledialog.askinteger("Edit Drag Y1","New start Y:",initialvalue=y1)
            nx2 = simpledialog.askinteger("Edit Drag X2","New end X:",initialvalue=x2)
            ny2 = simpledialog.askinteger("Edit Drag Y2","New end Y:",initialvalue=y2)
            if None not in (nx1,ny1,nx2,ny2): self.actions[i] = ('drag',(nx1,ny1),(nx2,ny2)); self.listbox.delete(i); self.listbox.insert(i, f"Drag from ({nx1},{ny1}) to ({nx2},{ny2})")
        elif typ == 'delay':
            d = simpledialog.askfloat("Edit Delay","New delay:",initialvalue=act[1],minvalue=0.0)
            if d is not None: self.actions[i] = ('delay',d); self.listbox.delete(i); self.listbox.insert(i, f"Delay {d:.2f} s")
        else: messagebox.showinfo("No Edit", f"'{typ}' has no parameters to edit.")

    def delete_action(self):
        sel = self.listbox.curselection();
        if not sel: return
        i = sel[0]; del self.actions[i]; self.listbox.delete(i)

    def move_up(self):
        sel = self.listbox.curselection();
        if not sel or sel[0]==0: return
        i = sel[0]; self.actions[i-1],self.actions[i]=self.actions[i],self.actions[i-1]
        prev,cur=self.listbox.get(i-1),self.listbox.get(i)
        self.listbox.delete(i-1,i); self.listbox.insert(i-1,cur); self.listbox.insert(i,prev); self.listbox.select_set(i-1)

    def move_down(self):
        sel=self.listbox.curselection();
        if not sel or sel[0]==len(self.actions)-1: return
        i=sel[0]; self.actions[i],self.actions[i+1]=self.actions[i+1],self.actions[i]
        cur,nxt=self.listbox.get(i),self.listbox.get(i+1)
        self.listbox.delete(i,i+1); self.listbox.insert(i,nxt); self.listbox.insert(i+1,cur); self.listbox.select_set(i+1)

    def set_loop(self):
        n=simpledialog.askinteger("Loop Count","How many times to repeat?",minvalue=1)
        if n is not None: self.loop_count=n; self.loop_label.config(text=f"Loops: {self.loop_count}")

    def clear_actions(self):
        if messagebox.askyesno("Clear All","Delete all recorded actions?"): self.actions.clear(); self.listbox.delete(0,tk.END)

    def start_macro(self):
        if not self.actions: messagebox.showwarning("Empty","No actions to play."); return
        threading.Thread(target=self.run_macro).start()

    def run_macro(self):
        time.sleep(2)
        for _ in range(self.loop_count):
            for act in self.actions:
                typ = act[0]
                if typ == 'click': _,x,y=act; pyautogui.click(x,y)
                elif typ == 'drag': _,(x1,y1),(x2,y2)=act; left,top=min(x1,x2),min(y1,y2); width,height=abs(x2-x1),abs(y2-y1)
                pyautogui.mouseDown(left,top); pyautogui.moveTo(left+width,top+height,duration=0.1); pyautogui.mouseUp()
                elif typ=='delay': time.sleep(act[1])
                elif typ=='copy': pyautogui.hotkey('ctrl','c')
                elif typ=='paste': pyautogui.hotkey('ctrl','v')
                elif typ=='ocr':
                x1,y1,x2,y2=act[1]
                left,top=min(x1,x2),min(y1,y2)
                width,height=abs(x2-x1),abs(y2-y1)
                try:
                    with mss.mss() as sct:
                        monitor={'top':top,'left':left,'width':width,'height':height}
                        sct_img=sct.grab(monitor); img=Image.frombytes('RGB',sct_img.size,sct_img.rgb)
                    img.show(); text=pytesseract.image_to_string(img)
                    m=re.search(r"(\d{9})",text)
                    if m: num=m.group(1); pyperclip.copy(num); self.master.after(0,lambda n=num:messagebox.showinfo("OCR Copied",f"Copied: {n}"))
                    else: self.master.after(0,lambda:messagebox.showwarning("OCR","No 9-digit number found"))
                except Exception as e: self.master.after(0,lambda exc=e:messagebox.showerror("OCR Error",str(exc)))

if __name__ == "__main__":
    root=tk.Tk(); app=MacroMaker(root); root.mainloop()
