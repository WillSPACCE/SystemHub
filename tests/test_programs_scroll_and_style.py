import tkinter as tk

from main import THEME, bind_mouse_wheel_to_canvas


def test_bind_mouse_wheel_to_canvas_registers_wheel_handlers():
    root = tk.Tk()
    root.withdraw()
    try:
        canvas = tk.Canvas(root, bg=THEME["bg"], highlightthickness=0)
        target = tk.Canvas(root, bg=THEME["card_bg"], highlightthickness=0)

        bind_mouse_wheel_to_canvas(canvas, target)

        assert canvas.bind("<MouseWheel>")
        assert canvas.bind("<Button-4>")
        assert canvas.bind("<Button-5>")
    finally:
        root.destroy()
