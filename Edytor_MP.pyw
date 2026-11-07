# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional window-only Windows launcher."""
if __name__ == "__main__":
    try:
        from editor import main
        main()
    except Exception as exc:
        import traceback
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Edytor MP — błąd uruchomienia", str(exc) + "\n\nSpróbuj uruchomić URUCHOM.bat.")
            root.destroy()
        except Exception:
            traceback.print_exc()
