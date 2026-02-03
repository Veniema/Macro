#!/usr/bin/env python3

import tkinter as tk
from ui import MacroMaker


def main() -> None:
    root = tk.Tk()
    app = MacroMaker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
