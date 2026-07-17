import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import json
import os
import sys
import time
import re

from modules.firewall import FirewallManager
from modules.cleanup import CleanupManager
from modules.collector_service import HardwareCollectorService
from modules.hardware_service import HardwareService
from modules.programs_service import InstalledProgramsService
from modules.maintenance import MaintenanceCoordinator
from modules.report import ReportGenerator, format_brazilian_date, get_latest_report_path
from modules.settings import ReportSettingsManager


THEME = {
    "bg": "#F6F8FC",
    "card_bg": "#FFFFFF",
    "text_primary": "#111827",
    "text_secondary": "#6B7280",
    "accent_blue": "#2563EB",
    "accent_green": "#22C55E",
    "accent_purple": "#7C3AED",
    "accent_orange": "#F97316",
    "muted": "#E5E7EB",
    "shadow": "#E9EEF5",
    "shadow_hover": "#DBEAFE",
    "sidebar_active_bg": "#EFF6FF",
    "button_primary_bg": "#2563EB",
    "button_secondary_bg": "#F8FAFC",
    "button_hover_bg": "#E8F0FF",
    "button_border": "#D1D5DB",
    "tooltip_bg": "#111827",
    "tooltip_fg": "#FFFFFF",
    "sidebar_width": 230,
    "card_radius": 20,
}


def get_font(size_base, width=None, height=None, min_size=10, max_size=34):
    if width and width > 0:
        width_factor = min(max(width / 1280.0, 0.75), 1.35)
    else:
        width_factor = 1.0
    if height and height > 0:
        height_factor = min(max(height / 720.0, 0.8), 1.2)
    else:
        height_factor = 1.0
    size = size_base * width_factor * height_factor
    return max(min_size, min(max_size, int(round(size))))


def configure_tk_environment():
    if os.name != "nt":
        return
    tcl_dir = os.path.join(sys.prefix, "tcl", "tcl8.6")
    tk_dir = os.path.join(sys.prefix, "tcl", "tk8.6")
    if os.path.isdir(tcl_dir):
        os.environ.setdefault("TCL_LIBRARY", tcl_dir)
    if os.path.isdir(tk_dir):
        os.environ.setdefault("TK_LIBRARY", tk_dir)


configure_tk_environment()


def bind_mouse_wheel_to_canvas(widget, target_canvas=None):
    """Vincula a roda do mouse a um canvas para rolagem suave."""
    if widget is None:
        return

    def _on_scroll(event):
        try:
            target = target_canvas or widget
            if not hasattr(target, "yview_scroll"):
                return
            if hasattr(event, "delta") and event.delta:
                units = int(-event.delta / 120)
            elif hasattr(event, "num"):
                units = -1 if event.num == 5 else 1
            else:
                units = 0
            if units != 0:
                target.yview_scroll(units, "units")
        except Exception:
            pass

    widget.bind("<MouseWheel>", _on_scroll)
    widget.bind("<Button-4>", _on_scroll)
    widget.bind("<Button-5>", _on_scroll)


class Tooltip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if self.widget.winfo_class() == 'Entry' else (0, 0, 0, 0)
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, bg=THEME["tooltip_bg"], fg=THEME["tooltip_fg"], justify="left", relief="solid", borderwidth=0, padx=8, pady=4, font=("Segoe UI", 9))
        label.pack()

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class RoundedCard(tk.Canvas):
    def __init__(self, parent, title: str, accent: str, width: int = 320, height: int = 180):
        super().__init__(parent, width=width, height=height, bg=THEME["bg"], highlightthickness=0, bd=0)
        self.configure(bg=THEME['bg'])
        self.title = title
        self.accent = accent
        self.shadow_id = None
        self.bg_id = None
        self.text_id = None
        self.inner_window = None
        self.tooltip_window = None
        self.hover_text = ""
        self.hovered = False
        self.divider_id = None
        self.inner_frame = tk.Frame(self, bg=THEME['card_bg'], padx=14, pady=12)
        self.inner_frame.pack_propagate(False)
        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)
        self._create_card(width, height)

    def set_hover_text(self, text: str):
        self.hover_text = text

    def _on_hover_enter(self, event=None):
        if self.hover_text:
            self._show_tooltip()
        self.hovered = True
        self._apply_hover_state(True)

    def _on_hover_leave(self, event=None):
        self.hovered = False
        self._hide_tooltip()
        self._apply_hover_state(False)

    def _apply_hover_state(self, hovered: bool):
        if not self.winfo_exists():
            return
        shadow_color = THEME["shadow_hover"] if hovered else THEME["shadow"]
        if self.shadow_id is not None:
            self.itemconfigure(self.shadow_id, fill=shadow_color)
        self.configure(cursor="hand2" if hovered else "")

    def _show_tooltip(self):
        if not self.hover_text or self.tooltip_window is not None:
            return
        x = self.winfo_rootx() + 20
        y = self.winfo_rooty() + self.winfo_height() + 10
        self.tooltip_window = tk.Toplevel(self)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        label = tk.Label(self.tooltip_window, text=self.hover_text, bg=THEME["tooltip_bg"], fg=THEME["tooltip_fg"], justify="left", relief="flat", borderwidth=0, padx=10, pady=8, font=("Segoe UI", 10), wraplength=320)
        label.pack()

    def _hide_tooltip(self):
        if self.tooltip_window is not None:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def _create_card(self, width, height):
        self.config(width=width, height=height)
        radius = THEME.get('card_radius', 14)
        self.shadow_id = self._create_shadow(6, 8, max(width - 2, 0), max(height - 2, 0), radius=radius)
        self.bg_id = self._create_rounded_rectangle(0, 0, max(width - 10, 0), max(height - 10, 0), radius=radius - 2, fill=THEME['card_bg'], outline="")
        if self.title:
            self.text_id = self.create_text(18, 20, text=self.title, anchor="nw", font=("Segoe UI", 13, "bold"), fill=self.accent)
            if self.divider_id is None:
                self.divider_id = self.create_line(18, 44, max(width - 18, 0), 44, fill=THEME['muted'], width=1)
            else:
                self.coords(self.divider_id, 18, 44, max(width - 18, 0), 44)
            content_y = 54
            content_height = max(height - 74, 0)
        else:
            self.text_id = None
            if self.divider_id is not None:
                self.delete(self.divider_id)
                self.divider_id = None
            content_y = 16
            content_height = max(height - 34, 0)
        self.inner_window = self.create_window(18, content_y, anchor="nw", window=self.inner_frame, width=max(width - 36, 0), height=content_height)

    def resize(self, width, height):
        if width < 120 or height < 80:
            return
        self.config(width=width, height=height)
        if self.shadow_id is not None:
            self.coords(self.shadow_id, *self._rounded_rect_points(6, 8, max(width - 2, 0), max(height - 2, 0), 18))
        if self.bg_id is not None:
            self.coords(self.bg_id, *self._rounded_rect_points(0, 0, max(width - 10, 0), max(height - 10, 0), 16))
        if self.text_id is not None:
            self.coords(self.text_id, 18, 20)
            if self.divider_id is None:
                self.divider_id = self.create_line(18, 44, max(width - 18, 0), 44, fill=THEME['muted'], width=1)
            else:
                self.coords(self.divider_id, 18, 44, max(width - 18, 0), 44)
        elif self.divider_id is not None:
            self.delete(self.divider_id)
            self.divider_id = None
        if self.inner_window is not None:
            if self.title:
                content_y = 54
                content_height = max(height - 74, 0)
            else:
                content_y = 16
                content_height = max(height - 34, 0)
            self.coords(self.inner_window, 18, content_y)
            content_width = max(width - 36, 0)
            self.itemconfigure(self.inner_window, width=content_width, height=content_height)
            try:
                self.inner_frame.configure(width=content_width)
            except Exception:
                pass

    def _rounded_rect_points(self, x1, y1, x2, y2, radius=18):
        return [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]

    def _create_shadow(self, x1, y1, x2, y2, radius=18):
        return self._create_rounded_rectangle(x1, y1, x2, y2, radius=radius, fill=THEME['shadow'], outline="")

    def _create_rounded_rectangle(self, x1, y1, x2, y2, radius=18, **kwargs):
        points = self._rounded_rect_points(x1, y1, x2, y2, radius)
        return self.create_polygon(points, smooth=True, **kwargs)


class ProgressBar(tk.Canvas):
    def __init__(self, parent, width: int = 280, height: int = 8, value: float = 0.0, color: str = THEME["accent_blue"], show_text: bool = True):
        adjusted_height = max(height, 18) if show_text else max(height, 8)
        super().__init__(parent, width=width, height=adjusted_height, bg=THEME['bg'], bd=0, highlightthickness=0)
        self.width = width
        self.height = adjusted_height
        self.color = color
        self.show_text = show_text
        self._value = 0.0
        self.bg_rect = self._create_rounded_rectangle(0, 0, width, self.height, radius=self.height // 2, fill=THEME['muted'], outline="")
        self.fill_rect = self._create_rounded_rectangle(0, 0, 0, self.height, radius=self.height // 2, fill=color, outline="")
        self.text = self.create_text(width // 2, self.height // 2, anchor="center", text="0%", fill=THEME['text_primary'], font=("Segoe UI", 9, "bold"))
        self.set_value(value)

    def _create_rounded_rectangle(self, x1, y1, x2, y2, radius=8, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def set_value(self, value: float):
        value = max(0.0, min(100.0, value if value is not None else 0.0))
        self._value = value
        fill_width = int((self.width - 2) * value / 100.0)
        if fill_width < 4:
            fill_width = 4
        self.coords(self.fill_rect, *self._rounded_coords(0, 0, fill_width, self.height, radius=self.height // 2))
        self.itemconfigure(self.fill_rect, fill=self.color)
        if self.show_text:
            self.itemconfigure(self.text, text=f"{value:.0f}%", state="normal")
        else:
            self.itemconfigure(self.text, text=f"{value:.0f}%", state="hidden")

    def resize(self, width: int, height: int | None = None):
        if width < 40:
            return
        self.width = width
        if height is not None:
            self.height = height
        self.config(width=self.width, height=self.height)
        self.coords(self.bg_rect, *self._rounded_coords(0, 0, self.width, self.height, radius=max(2, self.height // 2)))
        self.coords(self.text, self.width // 2, self.height // 2)
        self.set_value(self._value)

    def _rounded_coords(self, x1, y1, x2, y2, radius=8):
        return [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]


class AccordionSection(tk.Frame):
    def __init__(self, parent, title: str):
        super().__init__(parent, bg=THEME["card_bg"])
        self.is_open = False
        self.header = tk.Frame(self, bg=THEME["card_bg"])
        self.header.pack(fill="x")
        self.icon = tk.Label(self.header, text="▶", bg=THEME["card_bg"], fg=THEME["accent_blue"], font=("Segoe UI", 10, "bold"))
        self.icon.pack(side="left")
        self.title_label = tk.Label(self.header, text=title, bg=THEME["card_bg"], fg=THEME["text_primary"], font=("Segoe UI", 11, "bold"))
        self.title_label.pack(side="left", padx=(8, 0))
        self.header.bind("<Button-1>", self.toggle)
        self.icon.bind("<Button-1>", self.toggle)
        self.title_label.bind("<Button-1>", self.toggle)
        self.body = tk.Frame(self, bg=THEME["bg"])

    def toggle(self, event=None):
        self.is_open = not self.is_open
        self.icon.config(text="▼" if self.is_open else "▶")
        if self.is_open:
            self.body.pack(fill="x", padx=8, pady=(0, 12))
        else:
            self.body.forget()


class App(tk.Tk):
    def __init__(self):
        configure_tk_environment()
        super().__init__()
        self.title("System Utility Hub")
        self.geometry("1100x700")
        self.minsize(980, 640)
        self.configure(bg=THEME['bg'])

        self.data = {}
        self.selected_page = "Dashboard"
        self.nav_buttons = {}
        self.nav_indicators = {}
        self.dashboard_cards = []
        self.dashboard_widget_states = {}
        self.quick_status_states = []
        self._dashboard_structure_ready = False
        self._quick_status_ready = False
        self._loading_active = False
        self._loading_frame = 0
        self._last_window_size = (0, 0)
        self._destroying = False
        self.maintenance_coordinator = MaintenanceCoordinator()
        self.report_settings_manager = ReportSettingsManager()
        self._report_settings = self.report_settings_manager.load()
        self.program_filter_terms = self._report_settings.get('program_filter', []) if isinstance(self._report_settings.get('program_filter', []), list) else []
        self.installed_programs = []
        self.selected_programs_for_report = []
        self.maintenance_coordinator.email_service.save_config(self._report_settings)

        try:
            self._configure_styles()
        except Exception:
            pass
        self._build_layout()
        self._build_sidebar()
        self._build_header()
        self._build_pages()
        self._build_footer()
        self.bind("<Configure>", self._handle_window_resize)
        self.after(150, self._handle_window_resize)
        self.show_page("Dashboard")
        self.after(300, self._run_initial_diagnostics)
        # carregamento de settings e timer periódico
        self._settings = {}
        self._periodic_stop = threading.Event()
        self.collector = HardwareCollectorService()
        self._load_settings()
        self._start_periodic_timer()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _schedule_ui_update(self, callback):
        def _run_callback():
            try:
                callback()
            except Exception:
                pass

        try:
            self.after(0, _run_callback)
        except RuntimeError:
            _run_callback()

    def _font(self, size_base, min_size=None, max_size=None, weight="normal", width=None, height=None):
        return ("Segoe UI", get_font(size_base, width=width or self.winfo_width(), height=height or self.winfo_height(), min_size=min_size or 10, max_size=max_size or 34))

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Sidebar.TButton", font=self._font(11, min_size=10, max_size=13), background=THEME['card_bg'], foreground=THEME['text_primary'], relief="flat", padding=(16, 12), anchor="w")
        style.map("Sidebar.TButton", background=[("active", THEME['sidebar_active_bg'])])
        style.configure("Accent.TButton", font=self._font(11, min_size=10, max_size=13, weight="bold"), background=THEME['accent_blue'], foreground=THEME['tooltip_fg'], relief="flat", padding=(14, 10))
        style.map("Accent.TButton", background=[("active", THEME['button_hover_bg'])])
        style.configure("Secondary.TButton", font=self._font(11, min_size=10, max_size=13), background=THEME['card_bg'], foreground=THEME['text_primary'], relief="flat", padding=(14, 10))
        style.map("Secondary.TButton", background=[("active", THEME['button_hover_bg'])])
        style.configure("Card.TFrame", background=THEME['card_bg'])
        style.configure("Header.TLabel", background=THEME['bg'], foreground=THEME['text_primary'], font=self._font(16, min_size=14, max_size=20, weight="bold"))
        style.configure("SubHeader.TLabel", background=THEME['bg'], foreground=THEME['accent_blue'], font=self._font(11, min_size=10, max_size=13))
        style.configure("Vertical.TScrollbar",
            troughcolor=THEME['muted'],
            background=THEME['accent_blue'],
            arrowcolor=THEME['accent_blue'],
            bordercolor=THEME['muted'],
            lightcolor=THEME['muted'],
            darkcolor=THEME['muted'],
            troughrelief="flat",
            relief="flat",
            width=10)
        style.map("Vertical.TScrollbar",
            background=[("active", THEME['accent_blue']), ("!active", THEME['accent_blue'])],
            troughcolor=[("active", THEME['muted']), ("!active", THEME['muted'])])

    def _build_layout(self):
        self.sidebar = tk.Frame(self, bg=THEME['card_bg'], width=THEME['sidebar_width'])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self, bg=THEME['bg'])
        self.content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self):
        logo_frame = tk.Frame(self.sidebar, bg=THEME['card_bg'], pady=18)
        logo_frame.pack(fill="x")
        logo_icon = tk.Label(logo_frame, text="⚡", bg=THEME['card_bg'], fg=THEME['accent_blue'], font=self._font(20, min_size=16, max_size=24, weight="bold"))
        logo_icon.pack(side="left", padx=(14, 6))
        logo_text = tk.Label(logo_frame, text="System Utility Hub", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13, weight="bold"), wraplength=160, justify="left")
        logo_text.pack(side="left")

        # Navigation items (ordered)
        nav_items = [
            ("Dashboard", "🏠", "Dashboard", "Visão geral do hardware"),
            ("Hardware", "🖥", "Hardware", "Informações de hardware"),
            ("Performance", "📈", "Performance", "Monitoramento de performance"),
            ("Firewall", "🛡", "Firewall", "Gerenciar firewall do Windows"),
            ("Aplicativos", "📦", "Aplicativos", "Gerenciar aplicativos"),
            ("Limpeza", "🧹", "Limpeza", "Limpar arquivos temporários"),
            ("Ferramentas", "🧰", "Ferramentas", "Ferramentas utilitárias"),
            ("Configurações", "⚙", "Configurações", "Ajustes do aplicativo"),
            ("Email", "✉", "E-mail", "Configurar envio de relatórios por e-mail"),
        ]
        for key, icon, label, tip in nav_items:
            self._create_nav_button(key, icon, label, tip)

        spacer = tk.Frame(self.sidebar, bg=THEME['card_bg'])
        spacer.pack(fill="both", expand=True)

        version_label = tk.Label(self.sidebar, text="Versão 1.0", bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12))
        version_label.pack(padx=18, pady=16, anchor="w")
        # actions in sidebar (compact)
        sidebar_actions = tk.Frame(self.sidebar, bg=THEME['card_bg'])
        sidebar_actions.pack(fill="x", pady=(0, 12), padx=12)
        self.collect_button = tk.Button(sidebar_actions, text="↻", bg=THEME['accent_blue'], fg=THEME["tooltip_fg"], bd=0, relief="flat", width=3, command=self.run_diagnostics, cursor="hand2")
        self.collect_button.pack(side="left", padx=(0, 6))
        Tooltip(self.collect_button, "Atualizar")
        self.clear_button = tk.Button(sidebar_actions, text="✖", bg=THEME['muted'], fg=THEME['text_primary'], bd=0, relief="flat", width=3, command=self.clear_diagnostics, cursor="hand2")
        self.clear_button.pack(side="left")
        Tooltip(self.clear_button, "Limpar resultados")

    def _create_nav_button(self, key, icon, text, tooltip_text):
        container = tk.Frame(self.sidebar, bg=THEME['card_bg'])
        container.pack(fill="x", padx=8, pady=6)
        indicator = tk.Frame(container, bg=THEME['card_bg'], width=6)
        indicator.pack(side="left", fill="y", padx=(6, 10))
        button = tk.Button(
            container,
            text=f"{icon}  {text}",
            anchor="w",
            font=self._font(11, min_size=10, max_size=13),
            bg=THEME['card_bg'],
            fg=THEME['text_primary'],
            bd=0,
            relief="flat",
            activebackground=THEME['sidebar_active_bg'],
            highlightthickness=0,
            padx=8,
            pady=12,
            command=lambda k=key: self.show_page(k),
            cursor="hand2",
        )
        button.pack(side="left", fill="x", expand=True)
        self.nav_buttons[key] = button
        self.nav_indicators[key] = indicator
        button.bind("<Enter>", lambda event, btn=button: self._highlight_nav_button(btn, True))
        button.bind("<Leave>", lambda event, btn=button: self._highlight_nav_button(btn, False))
        # permitir usar a roda do mouse sobre a sidebar para rolar o conteúdo principal
        button.bind('<MouseWheel>', lambda e: self._on_sidebar_scroll(e))
        button.bind('<Button-4>', lambda e: self._on_sidebar_scroll(e))
        button.bind('<Button-5>', lambda e: self._on_sidebar_scroll(e))
        Tooltip(button, tooltip_text)

    def _highlight_nav_button(self, button, active: bool):
        try:
            current = self.nav_buttons.get(self.selected_page)
            if button is current:
                return
        except Exception:
            pass
        # visual de hover
        button.configure(bg=(THEME['button_hover_bg'] if active else THEME['card_bg']))
        button.configure(fg=(THEME['accent_blue'] if active else THEME['text_primary']))

    def _bind_mouse_wheel_scroll(self, widget):
        if widget is None:
            return
        widget.bind("<MouseWheel>", self._on_page_scroll)
        widget.bind("<Button-4>", self._on_page_scroll)
        widget.bind("<Button-5>", self._on_page_scroll)
        widget.bind("<Enter>", lambda e: self.page_canvas.focus_set() if hasattr(self, 'page_canvas') else None)

    def _on_page_scroll(self, event):
        try:
            widget_class = event.widget.winfo_class()
            if widget_class in ("Text", "Treeview", "Scrollbar", "Entry", "Combobox", "Spinbox", "Listbox"):
                return
            if hasattr(event, 'delta') and event.delta:
                units = int(-event.delta / 120)
            elif hasattr(event, 'num'):
                units = -1 if event.num == 5 else 1
            else:
                units = 0
            if hasattr(self, 'page_canvas') and units != 0:
                self.page_canvas.yview_scroll(units, 'units')
        except Exception:
            pass

    def _on_sidebar_scroll(self, event):
        self._on_page_scroll(event)

    def _set_nav_button_active(self):
        for name, button in self.nav_buttons.items():
            if not button:
                continue
            indicator = self.nav_indicators.get(name)
            if name == self.selected_page:
                try:
                    button.configure(bg=THEME['sidebar_active_bg'], fg=THEME['accent_blue'])
                    if indicator is not None:
                        indicator.configure(bg=THEME['accent_blue'])
                except Exception:
                    pass
            else:
                try:
                    button.configure(bg=THEME['card_bg'], fg=THEME['text_primary'])
                    if indicator is not None:
                        indicator.configure(bg=THEME['card_bg'])
                except Exception:
                    pass

    def _build_header(self):
        header = tk.Frame(self.content, bg=THEME['bg'], pady=10)
        header.pack(fill="x", padx=18)

        left = tk.Frame(header, bg=THEME['bg'])
        left.pack(side="left", anchor="nw")
        title = tk.Label(left, text="Dashboard", bg=THEME['bg'], fg=THEME['text_primary'], font=self._font(20, min_size=18, max_size=28, weight="semibold"), wraplength=400, justify="left")
        title.pack(anchor="w")
        subtitle = tk.Label(left, text="Visão geral do seu sistema em tempo real", bg=THEME['bg'], fg=THEME['text_secondary'], font=self._font(12, min_size=11, max_size=15), wraplength=450, justify="left")
        subtitle.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(header, bg=THEME['bg'])
        right.pack(side="right", anchor="ne")

        # Action buttons
        btn_refresh = tk.Button(right, text="Atualizar", bg=THEME['card_bg'], fg=THEME['text_primary'], bd=0, relief="flat", padx=12, pady=8, cursor="hand2", command=self.run_diagnostics, highlightthickness=1, highlightbackground=THEME['muted'], highlightcolor=THEME['accent_blue'])
        btn_refresh.pack(side="right", padx=(8, 0))
        btn_report = tk.Button(right, text="Relatório", bg=THEME['card_bg'], fg=THEME['text_primary'], bd=0, relief="flat", padx=12, pady=8, cursor="hand2", highlightthickness=1, highlightbackground=THEME['muted'], highlightcolor=THEME['accent_blue'])
        btn_report.pack(side="right", padx=(8, 0))
        btn_check = tk.Button(right, text="Verificar Tudo", bg=THEME['accent_blue'], fg=THEME["tooltip_fg"], bd=0, relief="flat", padx=12, pady=8, cursor="hand2", highlightthickness=1, highlightbackground=THEME['accent_blue'], highlightcolor=THEME['accent_blue'])
        btn_check.pack(side="right", padx=(8, 0))

    def _build_pages(self):
        self.page_canvas = tk.Canvas(self.content, bg=THEME['bg'], highlightthickness=0)
        self.page_scrollbar = ttk.Scrollbar(self.content, style="Vertical.TScrollbar", orient="vertical", command=self.page_canvas.yview)
        self.page_canvas.configure(yscrollcommand=self.page_scrollbar.set)
        self.page_canvas.pack(side="left", fill="both", expand=True)
        self.page_scrollbar.pack(side="right", fill="y")

        self.page_inner = tk.Frame(self.page_canvas, bg=THEME['bg'])
        self.page_canvas.create_window((0, 0), window=self.page_inner, anchor="nw")
        self.page_inner.bind("<Configure>", self._on_page_inner_configure)
        self.page_canvas.bind("<Configure>", self._on_page_canvas_configure)
        self.page_canvas.bind("<Enter>", lambda e: self.page_canvas.focus_set())
        self.page_inner.bind("<Enter>", lambda e: self.page_canvas.focus_set())
        self.bind_all("<MouseWheel>", self._on_page_scroll)
        self.bind_all("<Button-4>", self._on_page_scroll)
        self.bind_all("<Button-5>", self._on_page_scroll)
        self._bind_mouse_wheel_scroll(self.content)
        self._bind_mouse_wheel_scroll(self.page_canvas)
        self._bind_mouse_wheel_scroll(self.page_inner)

        self.page_container = tk.Frame(self.page_inner, bg=THEME['bg'])
        self._bind_mouse_wheel_scroll(self.page_container)
        self.page_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.pages = {}
        self.pages["Dashboard"] = tk.Frame(self.page_container, bg=THEME['bg'])
        self.pages["Informações"] = tk.Frame(self.page_container, bg=THEME['bg'])
        self.pages["Firewall"] = tk.Frame(self.page_container, bg=THEME['bg'])
        self.pages["Aplicativos"] = tk.Frame(self.page_container, bg=THEME['bg'])
        self.pages["Limpeza"] = tk.Frame(self.page_container, bg=THEME['bg'])
        self.pages["Configurações"] = tk.Frame(self.page_container, bg=THEME['bg'])
        self.pages["Email"] = tk.Frame(self.page_container, bg=THEME['bg'])
        self.pages["Regras"] = tk.Frame(self.page_container, bg=THEME['bg'])

        for page in self.pages.values():
            self._bind_mouse_wheel_scroll(page)
            page.pack(fill="both", expand=True)
            page.pack_forget()

        self._build_dashboard_page()
        self._build_info_page()
        self._build_firewall_page()
        self._build_programs_page()
        self._build_rules_page()
        self._build_cleanup_page()
        self._build_settings_page()
        self._build_email_settings_page()

    def _on_page_inner_configure(self, event=None):
        self.page_canvas.configure(scrollregion=self.page_canvas.bbox("all"))

    def _on_page_canvas_configure(self, event=None):
        width = self.page_canvas.winfo_width()
        if width > 0:
            try:
                items = self.page_canvas.find_all()
                if items:
                    self.page_canvas.itemconfigure(items[0], width=width)
            except Exception:
                pass
        if self.winfo_exists() and not self._destroying:
            self._handle_window_resize()

    def _build_dashboard_page(self):
        page = self.pages["Dashboard"]
        page.pack(fill="both", expand=True)
        self.dashboard_content = tk.Frame(page, bg=THEME['bg'])
        self.dashboard_content.pack(fill="both", expand=True, padx=0)
        self.status_bar = tk.Frame(self.dashboard_content, bg=THEME['card_bg'], highlightbackground=THEME['shadow'], highlightthickness=1)
        self.status_bar.pack(fill="x", pady=(0, 8), padx=12)
        self.status_bar.columnconfigure(0, weight=1)
        self.status_indicator = tk.Label(self.status_bar, text="● Saudável", bg=THEME['card_bg'], fg=THEME['accent_green'], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=180, justify="left")
        self.status_indicator.grid(row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 4))
        self.status_message = tk.Label(self.status_bar, text="Sistema funcionando normalmente", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12), wraplength=620, justify="left")
        self.status_message.grid(row=1, column=0, sticky="w", padx=(16, 8), pady=(0, 12))
        self.update_label = tk.Label(self.status_bar, text="Última atualização: nunca", bg=THEME['card_bg'], fg=THEME['accent_blue'], font=self._font(9, min_size=8, max_size=10), wraplength=260, justify="right")
        self.update_label.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 18), pady=12)

        self.quick_cards_frame = tk.Frame(self.dashboard_content, bg=THEME['bg'])
        self.quick_cards_frame.pack(fill="x", pady=(0, 6), padx=12)

        self.dashboard_cards_frame = tk.Frame(self.dashboard_content, bg=THEME['bg'])
        self.dashboard_cards_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.cpu_card = RoundedCard(self.dashboard_cards_frame, "💻 CPU", "#2563EB", width=320, height=300)
        self.cpu_card.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        self.ram_card = RoundedCard(self.dashboard_cards_frame, "🧠 RAM", "#7c3aed", width=320, height=300)
        self.ram_card.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        self.storage_card = RoundedCard(self.dashboard_cards_frame, "💾 SSD", "#0f766e", width=320, height=300)
        self.storage_card.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")
        self.system_card = RoundedCard(self.dashboard_cards_frame, "🖥 Sistema", "#ea580c", width=320, height=300)
        self.system_card.grid(row=1, column=1, padx=6, pady=6, sticky="nsew")
        self.dashboard_cards = [self.cpu_card, self.ram_card, self.storage_card, self.system_card]

        self._build_dashboard_cpu_card()
        self._build_dashboard_ram_card()
        self._build_dashboard_ssd_card()
        self._build_dashboard_system_card()
        self._build_quick_metrics_frame()

    def _build_quick_metrics_frame(self):
        self.quick_metrics = {
            "cpu_temp": {"icon": None, "value": None, "label": None, "bar": None},
            "cpu_usage": {"icon": None, "value": None, "label": None, "bar": None},
            "ram_usage": {"icon": None, "value": None, "label": None, "bar": None},
            "ssd_temp": {"icon": None, "value": None, "label": None, "bar": None},
            "ssd_health": {"icon": None, "value": None, "label": None, "bar": None},
            "ssd_usage": {"icon": None, "value": None, "label": None, "bar": None},
        }
        metrics_row = tk.Frame(self.quick_cards_frame, bg=THEME['bg'])
        metrics_row.pack(fill="x", pady=0)
        items = [("cpu_temp", ("🌡", "Temperatura CPU", THEME['accent_green'])), ("cpu_usage", ("⚙", "Uso CPU", THEME['accent_green'])), ("ram_usage", ("🧠", "Uso RAM", THEME['accent_purple'])), ("ssd_temp", ("💾", "Temperatura SSD", THEME['accent_blue'])), ("ssd_health", ("❤️", "Saúde SSD", THEME['accent_blue'])), ("ssd_usage", ("📁", "Uso SSD", THEME['accent_blue']))]
        for index, (key, (icon, label, color)) in enumerate(items):
            metrics_row.grid_columnconfigure(index, weight=1)
            card = RoundedCard(metrics_row, title="", accent=color, width=180, height=140)
            card.grid(row=0, column=index, sticky="nsew", padx=8, pady=2)
            inner = card.inner_frame
            inner.configure(bg=THEME['card_bg'])
            icon_label = tk.Label(inner, text=icon, bg=THEME['card_bg'], fg=color, font=self._font(12, min_size=11, max_size=14, weight="bold"))
            icon_label.pack(anchor="w")
            value_label = tk.Label(inner, text="N/A", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(12, min_size=11, max_size=14, weight="bold"))
            value_label.pack(anchor="w", pady=(2, 0))
            hint_label = tk.Label(inner, text=label, bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(9, min_size=8, max_size=11), wraplength=140, justify="left")
            hint_label.pack(anchor="w", pady=(4, 0))
            bar = ProgressBar(inner, width=180, height=8, value=0.0, color=color, show_text=False)
            bar.pack(fill="x", pady=(8, 0))
            self.quick_metrics[key] = {"icon": icon_label, "value": value_label, "label": hint_label, "bar": bar}

    def _build_dashboard_cpu_card(self):
        parent = self.cpu_card.inner_frame
        self.lbl_cpu_name = tk.Label(parent, text="Não disponível", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(12, min_size=11, max_size=15, weight="bold"), wraplength=280, justify="left")
        self.lbl_cpu_name.pack(anchor="w", pady=(0, 6))

        metrics_grid = tk.Frame(parent, bg=THEME["card_bg"])
        metrics_grid.pack(fill="x", pady=(2, 6))
        metrics_grid.columnconfigure(0, weight=1)
        metrics_grid.columnconfigure(1, weight=1)

        usage_frame = tk.Frame(metrics_grid, bg=THEME["card_bg"], highlightbackground=THEME['muted'], highlightthickness=1, padx=8, pady=8)
        usage_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.cpu_usage_frame = usage_frame
        tk.Label(usage_frame, text="Uso", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11)).pack(anchor="w")
        self.lbl_cpu_usage = tk.Label(usage_frame, text="0%", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(13, min_size=11, max_size=16, weight="bold"), wraplength=140)
        self.lbl_cpu_usage.pack(anchor="w", pady=(6, 4))
        self.progress_cpu_usage = ProgressBar(usage_frame, width=220, value=0.0, color="#2563EB", show_text=True)
        self.progress_cpu_usage.pack(fill="x")

        temp_frame = tk.Frame(metrics_grid, bg=THEME["card_bg"], highlightbackground=THEME['muted'], highlightthickness=1, padx=8, pady=8)
        temp_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.cpu_temp_frame = temp_frame
        tk.Label(temp_frame, text="Temperatura", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11)).pack(anchor="w")
        self.lbl_cpu_temp = tk.Label(temp_frame, text="0°C", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(13, min_size=11, max_size=16, weight="bold"), wraplength=140)
        self.lbl_cpu_temp.pack(anchor="w", pady=(6, 4))
        self.progress_cpu_temp = ProgressBar(temp_frame, width=220, value=0.0, color="#16a34a", show_text=True)
        self.progress_cpu_temp.pack(fill="x")

        self.cpu_row_frames = []
        for _ in range(5):
            row = tk.Frame(parent, bg=THEME["card_bg"], name=f"cpu_row_{len(self.cpu_row_frames)}")
            row.pack(fill="x", pady=2)
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11), wraplength=120, justify="left").pack(side="left")
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(9, min_size=8, max_size=11, weight="bold"), wraplength=150, justify="right").pack(side="right")
            self.cpu_row_frames.append(row)

    def _build_dashboard_ram_card(self):
        parent = self.ram_card.inner_frame
        self.lbl_ram_total = tk.Label(parent, text="Não disponível", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(12, min_size=11, max_size=15, weight="bold"), wraplength=280, justify="left")
        self.lbl_ram_total.pack(anchor="w", pady=(0, 6))

        usage_frame = tk.Frame(parent, bg=THEME["card_bg"], highlightbackground=THEME['muted'], highlightthickness=1, padx=8, pady=8)
        usage_frame.pack(fill="x", pady=(2, 6))
        self.ram_usage_frame = usage_frame
        tk.Label(usage_frame, text="Uso", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11)).pack(anchor="w")
        self.progress_ram_usage = ProgressBar(usage_frame, width=260, value=0.0, color="#7c3aed", show_text=True)
        self.progress_ram_usage.pack(fill="x", pady=(4, 2))
        self.lbl_ram_usage = tk.Label(usage_frame, text="0%", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(9, min_size=8, max_size=11, weight="bold"), wraplength=140)
        self.lbl_ram_usage.pack(anchor="e")

        self.ram_row_frames = []
        for _ in range(5):
            row = tk.Frame(parent, bg=THEME["card_bg"], name=f"ram_row_{len(self.ram_row_frames)}")
            row.pack(fill="x", pady=2)
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11), wraplength=120, justify="left").pack(side="left")
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(9, min_size=8, max_size=11, weight="bold"), wraplength=150, justify="right").pack(side="right")
            self.ram_row_frames.append(row)

    def _build_dashboard_ssd_card(self):
        parent = self.storage_card.inner_frame
        self.lbl_ssd_model = tk.Label(parent, text="Não disponível", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(12, min_size=11, max_size=15, weight="bold"), wraplength=280, justify="left")
        self.lbl_ssd_model.pack(anchor="w", pady=(0, 6))

        metrics_grid = tk.Frame(parent, bg=THEME["card_bg"])
        metrics_grid.pack(fill="x", pady=(2, 6))
        metrics_grid.columnconfigure(0, weight=1)
        metrics_grid.columnconfigure(1, weight=1)

        usage_frame = tk.Frame(metrics_grid, bg=THEME["card_bg"], highlightbackground=THEME['muted'], highlightthickness=1, padx=8, pady=8)
        usage_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.ssd_usage_frame = usage_frame
        tk.Label(usage_frame, text="Ocupação", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11)).pack(anchor="w")
        self.lbl_ssd_usage = tk.Label(usage_frame, text="0%", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(13, min_size=11, max_size=16, weight="bold"), wraplength=140)
        self.lbl_ssd_usage.pack(anchor="w", pady=(6, 4))
        self.progress_ssd_usage = ProgressBar(usage_frame, width=220, value=0.0, color="#10b981", show_text=True)
        self.progress_ssd_usage.pack(fill="x")

        temp_frame = tk.Frame(metrics_grid, bg=THEME["card_bg"], highlightbackground=THEME['muted'], highlightthickness=1, padx=8, pady=8)
        temp_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.ssd_temp_frame = temp_frame
        tk.Label(temp_frame, text="Temperatura", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11)).pack(anchor="w")
        self.lbl_ssd_temp = tk.Label(temp_frame, text="0°C", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(13, min_size=11, max_size=16, weight="bold"), wraplength=140)
        self.lbl_ssd_temp.pack(anchor="w", pady=(6, 4))
        self.progress_ssd_temp = ProgressBar(temp_frame, width=220, value=0.0, color="#16a34a", show_text=True)
        self.progress_ssd_temp.pack(fill="x")

        health_frame = tk.Frame(parent, bg=THEME["card_bg"], highlightbackground=THEME['muted'], highlightthickness=1, padx=8, pady=8)
        health_frame.pack(fill="x", pady=(2, 6))
        self.ssd_health_frame = health_frame
        tk.Label(health_frame, text="Saúde", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11)).pack(anchor="w")
        self.lbl_ssd_health = tk.Label(health_frame, text="Indisponível", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11, weight="bold"), wraplength=180)
        self.lbl_ssd_health.pack(anchor="w", pady=(2, 0))

        self.ssd_row_frames = []
        for _ in range(5):
            row = tk.Frame(parent, bg=THEME["card_bg"], name=f"ssd_row_{len(self.ssd_row_frames)}")
            row.pack(fill="x", pady=2)
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11), wraplength=120, justify="left").pack(side="left")
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(9, min_size=8, max_size=11, weight="bold"), wraplength=150, justify="right").pack(side="right")
            self.ssd_row_frames.append(row)

    def _build_dashboard_system_card(self):
        parent = self.system_card.inner_frame
        self.lbl_system_os = tk.Label(parent, text="Não disponível", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(12, min_size=11, max_size=15, weight="bold"), wraplength=280, justify="left")
        self.lbl_system_os.pack(anchor="w", pady=(0, 6))

        self.system_row_frames = []
        for _ in range(8):
            row = tk.Frame(parent, bg=THEME["card_bg"], name=f"system_row_{len(self.system_row_frames)}")
            row.pack(fill="x", pady=2)
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=11), wraplength=120, justify="left").pack(side="left")
            tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(9, min_size=8, max_size=11, weight="bold"), wraplength=150, justify="right").pack(side="right")
            self.system_row_frames.append(row)

    def _build_info_page(self):
        page = self.pages["Informações"]
        # Use the main page canvas for vertical scrolling to avoid duplicate scrollbars
        self.info_content = tk.Frame(page, bg=THEME['bg'])
        self.info_content.pack(fill="both", expand=True)
        self.info_canvas = tk.Canvas(self.info_content, bg=THEME['bg'], highlightthickness=0)
        # Do not create a separate scrollbar here (it duplicated the page scrollbar and confundia o usuário)
        self.info_canvas.pack(side="left", fill="both", expand=True)
        self.info_inner = tk.Frame(self.info_canvas, bg=THEME['bg'])
        self.info_canvas.create_window((0, 0), window=self.info_inner, anchor="nw")
        # Atualiza a scrollregion do canvas interno e aciona a atualização do canvas principal
        def _info_inner_configure(event=None):
            try:
                self.info_canvas.configure(scrollregion=self.info_canvas.bbox("all"))
            except Exception:
                pass
            try:
                if hasattr(self, 'page_canvas'):
                    self.page_canvas.configure(scrollregion=self.page_canvas.bbox("all"))
            except Exception:
                pass

        self.info_inner.bind("<Configure>", _info_inner_configure)

    def _build_firewall_page(self):
        page = self.pages["Firewall"]
        header = tk.Label(page, text="Gerencie o firewall do Windows", bg=THEME["bg"], fg=THEME["text_primary"], font=self._font(16, min_size=14, max_size=20, weight="bold"), wraplength=720, justify="left")
        header.pack(anchor="nw", pady=(12, 8), padx=24)
        sub = tk.Label(page, text="Consulte o estado atual e configure portas rapidamente.", bg=THEME["bg"], fg=THEME["text_secondary"], font=self._font(11, min_size=10, max_size=13), wraplength=720, justify="left")
        sub.pack(anchor="nw", padx=24)

        controls = tk.Frame(page, bg=THEME["bg"])
        controls.pack(fill="x", padx=24, pady=16)
        tk.Button(controls, text="Ver estado", bg=THEME['accent_blue'], fg=THEME["tooltip_fg"], activebackground=THEME['button_hover_bg'], bd=0, relief="flat", padx=16, pady=10, cursor="hand2", command=self.check_firewall_state).pack(side="left")
        tk.Button(controls, text="Ativar", bg=THEME['accent_green'], fg=THEME["tooltip_fg"], activebackground=THEME['button_hover_bg'], bd=0, relief="flat", padx=16, pady=10, cursor="hand2", command=lambda: self.toggle_firewall(True)).pack(side="left", padx=8)
        tk.Button(controls, text="Desativar", bg=THEME['muted'], fg=THEME['text_primary'], activebackground=THEME["button_hover_bg"], bd=0, relief="flat", padx=16, pady=10, cursor="hand2", command=lambda: self.toggle_firewall(False)).pack(side="left", padx=8)

        port_frame = tk.Frame(page, bg=THEME["bg"])
        port_frame.pack(fill="x", padx=24, pady=(0, 16))
        self.port_entry = tk.Entry(port_frame, font=self._font(11, min_size=10, max_size=13), bd=0, relief="solid", highlightthickness=1, highlightbackground=THEME["muted"], width=10)
        self.port_entry.insert(0, "3050")
        self.port_entry.pack(side="left", pady=2)
        tk.Label(port_frame, text='Direção:', bg=THEME['bg'], fg=THEME['text_secondary'], font=self._font(10)).pack(side='left', padx=(12, 8))
        self.firewall_port_direction = ttk.Combobox(port_frame, values=['Entrada', 'Saída'], state='readonly', width=10)
        self.firewall_port_direction.set('Entrada')
        self.firewall_port_direction.pack(side='left')
        tk.Button(port_frame, text="Liberar porta", bg=THEME["card_bg"], fg=THEME["text_primary"], bd=0, relief="flat", highlightbackground=THEME["muted"], highlightthickness=1, padx=16, pady=10, cursor="hand2", command=self.open_port).pack(side="left", padx=8)

        # Controls for connections table
        table_controls = tk.Frame(page, bg=THEME["bg"])
        table_controls.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(table_controls, text="Buscar:", bg=THEME["bg"], fg=THEME["text_secondary"], font=self._font(10)).pack(side="left", padx=(0, 8))
        self.firewall_search = tk.Entry(table_controls, font=self._font(10), width=24)
        self.firewall_search.pack(side="left")
        self.firewall_search.bind('<KeyRelease>', lambda e: self._schedule_firewall_filter())

        tk.Label(table_controls, text="Campo:", bg=THEME["bg"], fg=THEME["text_secondary"], font=self._font(10)).pack(side="left", padx=(12, 8))
        self.firewall_filter_field = ttk.Combobox(table_controls, values=["Todos", "Nome", "Porta", "Protocolo", "Direção", "Perfil", "Programa"], state='readonly', width=12)
        self.firewall_filter_field.set("Todos")
        self.firewall_filter_field.pack(side="left")
        self.firewall_filter_field.bind('<<ComboboxSelected>>', lambda e: self._apply_firewall_filter())

        tk.Label(table_controls, text="Protocolo:", bg=THEME["bg"], fg=THEME["text_secondary"], font=self._font(10)).pack(side="left", padx=(12, 8))
        self.protocol_filter = ttk.Combobox(table_controls, values=["Todos", "TCP", "UDP"], state='readonly', width=8)
        self.protocol_filter.set("Todos")
        self.protocol_filter.pack(side="left")
        self.protocol_filter.bind('<<ComboboxSelected>>', lambda e: self._apply_firewall_filter())

        self.firewall_list_refresh_button = tk.Button(table_controls, text="Atualizar lista", bg=THEME["accent_blue"], fg=THEME["tooltip_fg"], bd=0, relief="flat", padx=12, pady=8, cursor="hand2", command=self.refresh_firewall_list)
        self.firewall_list_refresh_button.pack(side="right")

        # TreeView for firewall connections
        cols = ("local", "remote", "protocol", "status", "pid", "process", "local_port")
        self.firewall_tree = ttk.Treeview(page, columns=cols, show='headings', selectmode='browse')
        self.firewall_tree.heading('local', text='Endereço Local', command=lambda: self._treeview_sort_column(self.firewall_tree, 'local', False))
        self.firewall_tree.heading('remote', text='Endereço Remoto', command=lambda: self._treeview_sort_column(self.firewall_tree, 'remote', False))
        self.firewall_tree.heading('protocol', text='Protocolo', command=lambda: self._treeview_sort_column(self.firewall_tree, 'protocol', False))
        self.firewall_tree.heading('status', text='Estado', command=lambda: self._treeview_sort_column(self.firewall_tree, 'status', False))
        self.firewall_tree.heading('pid', text='PID', command=lambda: self._treeview_sort_column(self.firewall_tree, 'pid', False))
        self.firewall_tree.heading('process', text='Processo', command=lambda: self._treeview_sort_column(self.firewall_tree, 'process', False))
        self.firewall_tree.heading('local_port', text='Porta', command=lambda: self._treeview_sort_column(self.firewall_tree, 'local_port', True))
        self.firewall_tree.column('local_port', width=80, anchor='center', stretch=False)
        self.firewall_tree.column('local', width=180, anchor='w')
        self.firewall_tree.column('remote', width=180, anchor='w')
        self.firewall_tree.column('protocol', width=90, anchor='center')
        self.firewall_tree.column('status', width=100, anchor='center')
        self.firewall_tree.column('pid', width=80, anchor='center')
        self.firewall_tree.column('process', width=160, anchor='w')

        tree_frame = tk.Frame(page, bg=THEME["bg"])
        tree_frame.pack(fill='both', expand=True, padx=24, pady=(0, 8))
        tree_scroll = ttk.Scrollbar(tree_frame, style="Vertical.TScrollbar", orient='vertical', command=self.firewall_tree.yview)
        self.firewall_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side='right', fill='y')
        self.firewall_tree.pack(fill='both', expand=True)

        # Action buttons
        actions = tk.Frame(page, bg=THEME["bg"])
        actions.pack(fill='x', padx=24, pady=(4, 12))
        tk.Button(actions, text='Liberar selecionada', bg=THEME['card_bg'], fg=THEME["text_primary"], bd=0, relief='flat', padx=12, pady=8, command=self._action_allow_selected).pack(side='left')
        tk.Button(actions, text='Bloquear selecionada', bg=THEME['card_bg'], fg=THEME["text_primary"], bd=0, relief='flat', padx=12, pady=8, command=self._action_block_selected).pack(side='left', padx=8)
        tk.Button(actions, text='Remover regra por porta', bg=THEME['card_bg'], fg=THEME["text_primary"], bd=0, relief='flat', padx=12, pady=8, command=self._action_remove_selected).pack(side='left', padx=8)

        self.firewall_output = tk.Text(page, wrap="word", height=8, bg=THEME["card_bg"], bd=0, relief="flat", font=self._font(10, min_size=9, max_size=12), fg=THEME["text_primary"])
        self.firewall_output.pack(fill="x", padx=24, pady=(0, 24))

        # storage for rows
        self._firewall_rows = []
        self.refresh_firewall_list()

    def _treeview_sort_column(self, tv, col, numeric=False):
        data = [(tv.set(k, col), k) for k in tv.get_children('')]
        try:
            if numeric:
                data.sort(key=lambda t: float(t[0]) if t[0] not in (None, '') else 0)
            else:
                data.sort(key=lambda t: t[0].lower() if isinstance(t[0], str) else str(t[0]))
        except Exception:
            data.sort(key=lambda t: str(t[0]))
        # detect if already sorted ascending
        ids = [t[1] for t in data]
        current = [k for k in tv.get_children('')]
        if ids == current:
            ids.reverse()
        for index, iid in enumerate(ids):
            tv.move(iid, '', index)

    def _build_rules_page(self):
        page = self.pages["Regras"]
        header = tk.Label(page, text="Regras do Firewall", bg=THEME["bg"], fg=THEME['text_primary'], font=self._font(16, min_size=14, max_size=20, weight="bold"))
        header.pack(anchor="nw", pady=(12, 8), padx=24)

        controls = tk.Frame(page, bg=THEME["bg"])
        controls.pack(fill='x', padx=24, pady=(0, 8))
        tk.Button(controls, text='Atualizar regras', bg=THEME['accent_blue'], fg=THEME["tooltip_fg"], bd=0, relief='flat', padx=12, pady=8, command=self.refresh_rules_list).pack(side='left')
        tk.Button(controls, text='Exportar CSV', bg=THEME['card_bg'], fg=THEME['text_primary'], bd=0, relief='flat', padx=12, pady=8, command=lambda: self._export_rules('csv')).pack(side='right')
        tk.Button(controls, text='Exportar JSON', bg=THEME['card_bg'], fg=THEME['text_primary'], bd=0, relief='flat', padx=12, pady=8, command=lambda: self._export_rules('json')).pack(side='right', padx=8)
        tk.Button(controls, text='Exportar TXT', bg=THEME['card_bg'], fg=THEME['text_primary'], bd=0, relief='flat', padx=12, pady=8, command=lambda: self._export_rules('txt')).pack(side='right', padx=8)

        cols = ('name', 'action', 'enabled', 'direction', 'protocol', 'localport', 'profile')
        self.rules_tree = ttk.Treeview(page, columns=cols, show='headings')
        for c in cols:
            self.rules_tree.heading(c, text=c.capitalize(), command=lambda _c=c: self._treeview_sort_column(self.rules_tree, _c, False))
            self.rules_tree.column(c, width=140, anchor='w')

        frame = tk.Frame(page, bg=THEME['bg'])
        frame.pack(fill='both', expand=True, padx=24, pady=(0, 8))
        scrollbar = ttk.Scrollbar(frame, style="Vertical.TScrollbar", orient='vertical', command=self.rules_tree.yview)
        self.rules_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.rules_tree.pack(fill='both', expand=True)

        self._rules = []
        self.refresh_rules_list()

    def refresh_rules_list(self):
        try:
            manager = FirewallManager()
            rules = manager.list_rules()
            self._rules = rules
            for i in self.rules_tree.get_children():
                self.rules_tree.delete(i)
            for idx, r in enumerate(rules):
                self.rules_tree.insert('', 'end', iid=str(idx), values=(r.get('name',''), r.get('action',''), r.get('enabled',''), r.get('direction',''), r.get('protocol',''), r.get('localport',''), r.get('profile','')))
            if hasattr(self, 'firewall_output'):
                self.firewall_output.insert(tk.END, f'✔ {len(rules)} regras carregadas.\n')
        except Exception as exc:
            if hasattr(self, 'firewall_output'):
                self.firewall_output.insert(tk.END, f'Erro: {exc}\n')

    def _export_rules(self, fmt: str):
        import datetime, csv
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), f'firewall_rules_{ts}'))
        try:
            if fmt == 'csv':
                path = base + '.csv'
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if self._rules:
                        writer.writerow(list(self._rules[0].keys()))
                        for r in self._rules:
                            writer.writerow([r.get(k,'') for k in self._rules[0].keys()])
            elif fmt == 'json':
                path = base + '.json'
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self._rules, f, indent=2, ensure_ascii=False)
            else:
                path = base + '.txt'
                with open(path, 'w', encoding='utf-8') as f:
                    for r in self._rules:
                        f.write('\n'.join(f"{k}: {v}" for k, v in r.items()))
                        f.write('\n' + '-'*40 + '\n')
            if hasattr(self, 'firewall_output'):
                self.firewall_output.insert(tk.END, f'✔ Exportado: {path}\n')
        except Exception as exc:
            if hasattr(self, 'firewall_output'):
                self.firewall_output.insert(tk.END, f'Erro exportando: {exc}\n')

    def _create_action_button(self, parent, text, command, bg=THEME['accent_blue'], fg=THEME['tooltip_fg'], activebg=None, padx=16, pady=10, font=None):
        return tk.Button(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            activebackground=activebg or bg,
            activeforeground=fg,
            bd=0,
            relief="flat",
            padx=padx,
            pady=pady,
            cursor="hand2",
            highlightthickness=0,
            font=font or self._font(10, min_size=9, max_size=12, weight="bold"),
            command=command,
        )

    def _create_page_header(self, parent, title, subtitle, accent=THEME['accent_blue']):
        header_card = tk.Frame(
            parent,
            bg=THEME['card_bg'],
            highlightbackground=THEME['shadow_hover'],
            highlightthickness=1,
            bd=0,
            padx=18,
            pady=16,
        )
        header_card.pack(fill='x', padx=24, pady=(12, 12))
        tk.Label(header_card, text='●', bg=THEME['card_bg'], fg=accent, font=self._font(13, min_size=12, max_size=15, weight='bold')).pack(anchor='w')
        tk.Label(header_card, text=title, bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(15, min_size=13, max_size=18, weight='bold'), anchor='w').pack(anchor='w', pady=(4, 2))
        tk.Label(header_card, text=subtitle, bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12), anchor='w', wraplength=920, justify='left').pack(anchor='w')
        return header_card

    def _create_input_field(self, parent, textvariable, show=None):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            bg=THEME['card_bg'],
            fg=THEME['text_primary'],
            bd=1,
            relief='solid',
            highlightthickness=1,
            highlightbackground=THEME['shadow_hover'],
            highlightcolor=THEME['accent_blue'],
            insertbackground=THEME['accent_blue'],
            font=self._font(10, min_size=9, max_size=12),
            show=show,
        )

    def _build_cleanup_page(self):
        page = self.pages["Limpeza"]
        self._create_page_header(page, "Central de manutenção", "Execute uma manutenção completa com checklist em tempo real, relatório automático e envio opcional por e-mail.", accent=THEME['accent_blue'])

        controls = tk.Frame(page, bg=THEME["bg"])
        controls.pack(fill="x", padx=24, pady=(4, 16))
        self.cleanup_start_button = self._create_action_button(controls, "Iniciar Manutenção", self.run_cleanup, bg=THEME['accent_blue'])
        self.cleanup_start_button.pack(side="left")
        self.cleanup_reports_button = self._create_action_button(controls, "Abrir Pasta de Relatórios", self._open_reports_folder, bg=THEME['accent_green'])
        self.cleanup_reports_button.pack(side="left", padx=8)
        self.cleanup_send_button = self._create_action_button(controls, "Enviar último relatório por e-mail", self._send_last_report, bg=THEME['accent_purple'])
        self.cleanup_send_button.pack(side="left", padx=8)

        summary_card = tk.Frame(page, bg=THEME['card_bg'], highlightbackground=THEME['shadow_hover'], highlightthickness=1, bd=0, padx=18, pady=18)
        summary_card.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(summary_card, text="Resumo da limpeza", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(12, min_size=11, max_size=14, weight="bold"), anchor="w").pack(anchor="w", pady=(0, 6))
        tk.Label(summary_card, text="Acompanhe o progresso geral e o espaço estimado recuperável antes de iniciar.", bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12), anchor="w", wraplength=980, justify="left").pack(anchor="w", pady=(0, 10))
        self.cleanup_summary = tk.Label(summary_card, text="Selecionados: 0 • Recuperável: 0 B", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12), anchor="w")
        self.cleanup_summary.pack(anchor="w")
        self.cleanup_progress = ttk.Progressbar(summary_card, orient="horizontal", length=520, mode="determinate")
        self.cleanup_progress.pack(anchor="w", fill="x", pady=(12, 0), padx=(0, 40))
        self.cleanup_progress_label = tk.Label(summary_card, text="0%", bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12))
        self.cleanup_progress_label.pack(anchor="w", pady=(8, 0))

        options_card = tk.Frame(page, bg=THEME['card_bg'], highlightbackground=THEME['shadow_hover'], highlightthickness=1, bd=0)
        options_card.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(options_card, text="Selecione os itens a limpar", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13, weight="bold"), anchor="w").pack(anchor="w", padx=16, pady=(12, 4))
        tk.Label(options_card, text="Cada item mostra o seu progresso individual e o espaço recuperado após a limpeza.", bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12), anchor="w", wraplength=980, justify="left").pack(anchor="w", padx=16, pady=(0, 10))
        self.cleanup_options_frame = tk.Frame(options_card, bg=THEME['card_bg'])
        self.cleanup_options_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.cleanup_action_vars = {}
        self.cleanup_option_cards = {}
        self.cleanup_option_bars = {}
        self.cleanup_option_result_labels = {}
        for action in self.maintenance_coordinator.get_action_labels():
            var = tk.BooleanVar(value=True)
            self.cleanup_action_vars[action['id']] = var
            row = tk.Frame(self.cleanup_options_frame, bg=THEME['card_bg'], highlightbackground=THEME['shadow_hover'], highlightthickness=1, bd=0, padx=14, pady=12)
            row.pack(fill="x", pady=8)
            row.bind("<Button-1>", lambda event, var=var: var.set(not var.get()))

            check_frame = tk.Frame(row, bg=THEME['card_bg'])
            check_frame.pack(side="left", padx=(0, 12), anchor="n")
            check = tk.Checkbutton(check_frame, variable=var, bg=THEME['card_bg'], fg=THEME['text_primary'], selectcolor=THEME['accent_blue'], command=self._refresh_cleanup_estimate, bd=0, highlightthickness=0, width=1, padx=0, pady=0)
            check.pack(anchor="center")

            content = tk.Frame(row, bg=THEME['card_bg'])
            content.pack(side="left", fill="x", expand=True)
            label = tk.Label(content, text=action['name'], bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12, weight="bold"), anchor="w")
            label.pack(anchor="w")
            description = action.get('description') or action.get('label') or 'Item disponível para limpeza'
            description_label = tk.Label(content, text=description, bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(9, min_size=8, max_size=10), anchor="w", wraplength=520, justify="left")
            description_label.pack(anchor="w", pady=(2, 0))

            bar_frame = tk.Frame(row, bg=THEME['card_bg'], width=220)
            bar_frame.pack(side="right", padx=(12, 0), anchor="n")
            bar_frame.pack_propagate(False)
            bar = ProgressBar(bar_frame, width=220, height=8, value=0.0, color=THEME['accent_blue'])
            bar.pack(fill="x", pady=(6, 0))
            result_label = tk.Label(bar_frame, text="0 B", bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(9, min_size=8, max_size=10), anchor="e")
            result_label.pack(anchor="e", pady=(4, 0))

            self.cleanup_option_cards[action['id']] = row
            self.cleanup_option_bars[action['id']] = bar
            self.cleanup_option_result_labels[action['id']] = result_label
            var.trace_add("write", lambda *_args, action_id=action['id']: self._refresh_cleanup_option_cards())

        checklist_card = tk.Frame(page, bg=THEME['card_bg'], highlightbackground=THEME['shadow_hover'], highlightthickness=1, bd=0)
        checklist_card.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(checklist_card, text="Checklist da manutenção", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13, weight="bold"), anchor="w").pack(anchor="w", padx=16, pady=(12, 6))
        self.cleanup_checklist_frame = tk.Frame(checklist_card, bg=THEME['card_bg'])
        self.cleanup_checklist_frame.pack(fill="x", padx=16, pady=(0, 12))
        self.cleanup_step_labels = {}
        for step_name in ["Coletando informações", "Limpando arquivos", "Defender", "Atualizando informações", "Gerando relatório", "Enviando relatório", "Concluído"]:
            label = tk.Label(self.cleanup_checklist_frame, text=f"☐ {step_name}", bg=THEME['card_bg'], fg=THEME['text_primary'], anchor="w", font=self._font(10, min_size=9, max_size=12))
            label.pack(anchor="w", pady=2)
            self.cleanup_step_labels[step_name] = label

        output_card = tk.Frame(page, bg=THEME['card_bg'], highlightbackground=THEME['shadow_hover'], highlightthickness=1, bd=0)
        output_card.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self.cleanup_output = tk.Text(output_card, wrap="word", height=14, bg=THEME["card_bg"], bd=0, relief="flat", font=self._font(10, min_size=9, max_size=12), fg=THEME['text_primary'])
        self.cleanup_output.pack(fill="both", expand=True, padx=14, pady=14)
        self._reset_cleanup_ui()
        self._refresh_cleanup_estimate()

    def _build_programs_page(self):
        page = self.pages["Aplicativos"]
        self._create_page_header(page, "Aplicativos instalados", "Selecione programas para incluir no próximo relatório. Clique com botão direito para desinstalar ou abrir local.", accent=THEME['accent_blue'])

        filter_frame = tk.Frame(page, bg=THEME["card_bg"], highlightbackground=THEME["shadow_hover"], highlightthickness=1, bd=0)
        filter_frame.pack(fill="x", padx=24, pady=(4, 8))
        filter_inner = tk.Frame(filter_frame, bg=THEME["card_bg"])
        filter_inner.pack(fill="x", padx=14, pady=12)

        tk.Label(filter_inner, text="Buscar:", bg=THEME["card_bg"], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13)).pack(side="left", padx=(0, 8))
        self.programs_filter_var = tk.StringVar()
        filter_entry = self._create_input_field(filter_inner, self.programs_filter_var)
        filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        filter_entry.bind("<KeyRelease>", lambda _event: self._apply_programs_filter())
        filter_entry.bind("<Return>", lambda _event: self._apply_programs_filter())
        self.programs_filter_btn = self._create_action_button(filter_inner, "🔍 Buscar", self._apply_programs_filter, bg=THEME['accent_blue'], padx=12, pady=6)
        self.programs_filter_btn.pack(side="left", padx=(0, 8))

        self.programs_filter_enabled = False
        self.programs_filter_toggle_btn = self._create_action_button(
            filter_inner,
            "🔧 Mostrar Drivers/Serviços",
            self._toggle_driver_filter,
            bg=THEME['accent_orange'],
            padx=12,
            pady=6,
        )
        self.programs_filter_toggle_btn.pack(side="left", padx=(0, 8))

        self.programs_count_var = tk.StringVar(value="")
        self.programs_count_label = tk.Label(filter_inner, textvariable=self.programs_count_var, bg=THEME["card_bg"], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=11))
        self.programs_count_label.pack(side="left", padx=(0, 0))

        programs_panel = tk.Frame(page, bg=THEME["card_bg"], highlightbackground=THEME["shadow_hover"], highlightthickness=1, bd=0)
        programs_panel.pack(fill="both", expand=True, padx=24, pady=(8, 16))
        canvas_frame = tk.Frame(programs_panel, bg=THEME["card_bg"])
        canvas_frame.pack(fill="both", expand=True, padx=12, pady=12)

        canvas = tk.Canvas(canvas_frame, bg=THEME["card_bg"], bd=0, highlightthickness=0, relief="flat")
        scrollbar = ttk.Scrollbar(canvas_frame, style="Vertical.TScrollbar", orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=THEME["card_bg"])
        scrollable_frame.bind("<Configure>", lambda e: self._refresh_programs_scrollregion())
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self.programs_checkboxes_frame = scrollable_frame
        self.programs_canvas = canvas
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        bind_mouse_wheel_to_canvas(canvas, canvas)
        bind_mouse_wheel_to_canvas(scrollable_frame, canvas)

        # Seção de programas selecionados
        selected_label = tk.Label(page, text="Programas selecionados para relatório:", bg=THEME["bg"], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13, weight="bold"))
        selected_label.pack(anchor="w", padx=24, pady=(8, 4))

        selected_box = tk.Frame(page, bg=THEME["card_bg"], highlightbackground=THEME["shadow_hover"], highlightthickness=1, bd=0)
        selected_box.pack(fill="x", padx=24, pady=(0, 16))
        self.selected_programs_output = tk.Text(selected_box, wrap="word", height=4, bg=THEME["card_bg"], bd=0, relief="flat", font=self._font(10, min_size=9, max_size=12), fg=THEME['text_primary'])
        self.selected_programs_output.pack(fill="x", padx=12, pady=12)

        clear_btn = self._create_action_button(page, "Limpar Seleção", self._clear_selected_programs, bg=THEME['accent_orange'], padx=12, pady=8)
        clear_btn.pack(anchor="e", padx=24, pady=(0, 24))

        self._load_installed_programs()

    def _is_windows_driver_or_service(self, program_name: str) -> bool:
        """Verifica se o programa é um driver ou serviço do Windows."""
        name_lower = program_name.lower()
        
        # Padrões que indicam drivers ou serviços do Windows
        exclude_patterns = [
            # Drivers
            "driver", "nvidia", "amd", "intel", "atheros", "realtek", "broadcom",
            "qualcomm", "marvell", "chipset", "gpu", "graphics", "audio",
            ".sys", ".dll", "device", "firmware",
            
            # Serviços e componentes do Windows
            "windows", "microsoft", "defender", "update", "telemetry",
            "cortana", "surface", "xbox", "onedriver", "onedrive",
            "sync", "service pack", "hotfix", "kb", "patch",
            ".net", "framework", "runtime", "redistributable",
            
            # Ferramentas do sistema
            "service", "system", "kernel", "library", "runtime",
            "redistributable", "vcredist", "runtime", "dotnet",
            
            # Filtros adicionais
            "(service", "[service", "service)", "system32",
            "winsys", "windowsupdate", "updates",
        ]
        
        for pattern in exclude_patterns:
            if pattern in name_lower:
                return True
        
        return False

    def _refresh_programs_scrollregion(self):
        if hasattr(self, 'programs_canvas') and self.programs_canvas.winfo_exists():
            try:
                self.programs_canvas.configure(scrollregion=self.programs_canvas.bbox("all"))
            except Exception:
                pass

    def _load_installed_programs(self):
        """Carrega e exibe os programas instalados (todos ou filtrados)."""
        try:
            all_programs = InstalledProgramsService.get_installed_programs()
            
            # Armazenar ambas as listas
            self.all_programs = all_programs
            
            if self.programs_filter_enabled:
                self.installed_programs = [
                    p for p in all_programs 
                    if not self._is_windows_driver_or_service(p.get("name", ""))
                ]
            else:
                self.installed_programs = all_programs
            
            # Atualizar contador
            if hasattr(self, 'programs_count_var'):
                if self.programs_filter_enabled:
                    self.programs_count_var.set(f"{len(self.installed_programs)} de {len(all_programs)}")
                else:
                    self.programs_count_var.set(f"{len(self.installed_programs)} programa(s)")
            
            self._display_programs(self.installed_programs)
        except Exception as exc:
            if hasattr(self, 'selected_programs_output'):
                self.selected_programs_output.delete("1.0", tk.END)
                self.selected_programs_output.insert(tk.END, f"Erro ao carregar programas: {exc}\n")

    def _toggle_driver_filter(self):
        """Alterna o filtro de drivers/serviços."""
        self.programs_filter_enabled = not self.programs_filter_enabled
        
        # Atualizar texto do botão
        if self.programs_filter_enabled:
            self.programs_filter_toggle_btn.config(text="✓ Drivers/Serviços Ocultos")
        else:
            self.programs_filter_toggle_btn.config(text="🔧 Mostrar Drivers/Serviços")
        
        # Recarregar programas
        self._load_installed_programs()

    def _display_programs(self, programs):
        """Exibe uma lista de programas com checkboxes em cards melhorados e menu de contexto."""
        # Limpar frame anterior
        for widget in self.programs_checkboxes_frame.winfo_children():
            widget.destroy()
        
        if not programs:
            empty_label = tk.Label(
                self.programs_checkboxes_frame, 
                text="Nenhum programa encontrado", 
                bg=THEME["bg"], 
                fg=THEME['text_secondary'], 
                font=self._font(11, min_size=10, max_size=13)
            )
            empty_label.pack(pady=20)
            return
        
        # Criar checkboxes para cada programa
        self.programs_vars = {}
        self.programs_data = {}
        
        for idx, program in enumerate(programs):
            name = program.get("name", "")
            version = program.get("version", "")
            uninstall_string = program.get("uninstall_string", "")
            install_location = program.get("install_location", "")
            
            if not name:
                continue
            
            var = tk.BooleanVar(value=name in self.selected_programs_for_report)
            self.programs_vars[name] = var
            self.programs_data[name] = {
                "uninstall_string": uninstall_string,
                "install_location": install_location
            }
            
            # Criar card para programa com design melhorado e destaque azul sutil
            prog_frame = tk.Frame(self.programs_checkboxes_frame, bg=THEME["card_bg"], highlightbackground=THEME["shadow_hover"], highlightthickness=1, bd=0)
            prog_frame.pack(fill="x", pady=4, padx=2)
            accent_bar = tk.Frame(prog_frame, bg=THEME['accent_blue'], width=3)
            accent_bar.pack(side="left", fill="y")
            accent_bar.pack_propagate(False)
            
            # Frame interno com padding
            inner_frame = tk.Frame(prog_frame, bg=THEME["card_bg"])
            inner_frame.pack(fill="x", padx=(10, 12), pady=8)
            
            # Checkbox
            chk = tk.Checkbutton(
                inner_frame, 
                text="", 
                variable=var, 
                bg=THEME["card_bg"], 
                fg=THEME['text_primary'],
                bd=0, 
                highlightthickness=0,
                activebackground=THEME["card_bg"],
                activeforeground=THEME['accent_blue'],
                selectcolor=THEME['accent_blue'],
                command=lambda program_name=name, program_var=var: self._toggle_program_selection(program_name, program_var)
            )
            chk.pack(side="left", padx=(0, 8))
            
            # Frame com informações do programa
            info_frame = tk.Frame(inner_frame, bg=THEME["card_bg"])
            info_frame.pack(side="left", fill="x", expand=True)
            
            # Nome do programa (mais escuro, peso bold)
            name_label = tk.Label(
                info_frame, 
                text=name, 
                bg=THEME["card_bg"], 
                fg=THEME['text_primary'], 
                font=self._font(10, min_size=9, max_size=12, weight="bold"),
                justify="left",
                wraplength=580
            )
            name_label.pack(anchor="w", pady=(0, 2))
            
            # Versão (texto menor e cinza)
            if version and version.strip():
                version_label = tk.Label(
                    info_frame, 
                    text=f"v{version}", 
                    bg=THEME["card_bg"], 
                    fg=THEME['text_secondary'], 
                    font=self._font(9, min_size=8, max_size=10)
                )
                version_label.pack(anchor="w", pady=(0, 0))
            
            # Dica de clique direito
            hint_label = tk.Label(
                info_frame, 
                text="(clique para adicionar ao relatório • clique direito para opções)", 
                bg=THEME["card_bg"], 
                fg="#999999", 
                font=self._font(8, min_size=7, max_size=9)
            )
            hint_label.pack(anchor="w", pady=(2, 0))
            
            def on_program_click(event, prog_name=name, program_var=var):
                if event.widget is chk:
                    return
                self._toggle_program_selection(prog_name, program_var)

            def on_right_click(event, prog_name=name):
                self._show_program_context_menu(event, prog_name)
            
            name_label.bind("<Button-1>", on_program_click)
            if version and version.strip():
                version_label.bind("<Button-1>", on_program_click)
            hint_label.bind("<Button-1>", on_program_click)
            prog_frame.bind("<Button-1>", on_program_click)
            inner_frame.bind("<Button-1>", on_program_click)
            info_frame.bind("<Button-1>", on_program_click)

            name_label.bind("<Button-3>", on_right_click)
            if version and version.strip():
                version_label.bind("<Button-3>", on_right_click)
            hint_label.bind("<Button-3>", on_right_click)
            prog_frame.bind("<Button-3>", on_right_click)
            inner_frame.bind("<Button-3>", on_right_click)
            info_frame.bind("<Button-3>", on_right_click)
            
            # Adicionar borda sutil ao card
            border_frame = tk.Frame(prog_frame, bg=THEME["shadow_hover"], height=1)
            border_frame.pack(fill="x", side="bottom")
            border_frame.pack_propagate(False)

        self.after_idle(self._refresh_programs_scrollregion)

    def _show_program_context_menu(self, event, program_name: str):
        """Mostra menu de contexto com opções de desinstalar e abrir local."""
        if program_name not in self.programs_data:
            return
        
        menu = tk.Menu(self, tearoff=0, bg=THEME["card_bg"], fg=THEME["text_primary"], relief="flat", bd=0)
        
        prog_info = self.programs_data[program_name]
        uninstall_string = prog_info.get("uninstall_string", "")
        install_location = prog_info.get("install_location", "")
        
        # Opção de desinstalar
        if uninstall_string:
            menu.add_command(
                label="🗑 Desinstalar",
                command=lambda: self._uninstall_program(program_name, uninstall_string)
            )
        else:
            menu.add_command(label="🗑 Desinstalar (não disponível)", state="disabled")
        
        # Opção de abrir local
        if install_location:
            menu.add_command(
                label="📂 Abrir Local de Instalação",
                command=lambda: self._open_program_location(program_name, install_location)
            )
        else:
            menu.add_command(label="📂 Abrir Local (não disponível)", state="disabled")
        
        # Separador
        menu.add_separator()
        
        # Copiar nome
        menu.add_command(
            label="📋 Copiar Nome",
            command=lambda: self._copy_to_clipboard(program_name)
        )
        
        # Mostrar menu
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.after_idle(menu.destroy)

    def _uninstall_program(self, program_name: str, uninstall_string: str):
        """Tenta desinstalar um programa."""
        result = InstalledProgramsService.uninstall_program(program_name, uninstall_string)
        
        if result:
            self._append_cleanup_log(f"✓ Iniciando desinstalação de {program_name}...")
            self._append_cleanup_log(f"   Verifique a janela do instalador que será aberta.")
        else:
            self._append_cleanup_log(f"❌ Não foi possível desinstalar {program_name}.")

    def _open_program_location(self, program_name: str, install_location: str):
        """Abre a pasta de instalação do programa."""
        result = InstalledProgramsService.open_install_location(install_location)
        
        if result:
            pass  # Window Explorer já abriu
        else:
            if hasattr(self, 'selected_programs_output'):
                self._append_cleanup_log(f"❌ Não foi possível abrir a pasta de {program_name}.")

    def _copy_to_clipboard(self, text: str):
        """Copia texto para a área de transferência."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except Exception:
            pass

    def _apply_programs_filter(self):
        """Aplica filtro aos programas e atualiza contador."""
        if not hasattr(self, 'programs_filter_var') or not hasattr(self, 'programs_count_var'):
            return
        filter_text = self.programs_filter_var.get().strip().lower()
        if not filter_text:
            filtered = self.installed_programs
        else:
            filtered = [p for p in self.installed_programs if filter_text in p.get("name", "").lower()]
        
        count_text = f"{len(filtered)} programa(s)"
        if filter_text:
            count_text += f" (de {len(self.installed_programs)})"
        self.programs_count_var.set(count_text)
        
        self._display_programs(filtered)

    def _toggle_program_selection(self, program_name: str, variable=None):
        """Alterna a seleção de um programa e atualiza a lista do relatório."""
        if not hasattr(self, 'programs_vars') or program_name not in self.programs_vars:
            return
        target_var = variable or self.programs_vars[program_name]
        target_var.set(not target_var.get())
        self._update_selected_programs()

    def _update_selected_programs(self):
        """Atualiza a lista de programas selecionados e exibe."""
        self.selected_programs_for_report = [name for name, var in self.programs_vars.items() if var.get()]
        self.selected_programs_output.delete("1.0", tk.END)
        
        if self.selected_programs_for_report:
            # Mostrar com numeração e formatação melhorada
            content = f"✓ {len(self.selected_programs_for_report)} programa(s) selecionado(s):\n\n"
            for i, prog in enumerate(self.selected_programs_for_report, 1):
                content += f"{i}. {prog}\n"
            self.selected_programs_output.insert(tk.END, content)
        else:
            self.selected_programs_output.insert(tk.END, "➜ Nenhum programa selecionado")
        
        # Salvar seleção em report_settings para persistência
        self._report_settings['program_filter'] = self.selected_programs_for_report
        self.report_settings_manager.save(self._report_settings)

    def _clear_selected_programs(self):
        """Limpa a seleção de programas."""
        for var in self.programs_vars.values():
            var.set(False)
        self._update_selected_programs()

    def _build_settings_page(self):
        page = self.pages["Configurações"]
        header = tk.Label(page, text="Configurações", bg=THEME["bg"], fg=THEME['text_primary'], font=self._font(16, min_size=14, max_size=20, weight="bold"), wraplength=720, justify="left")
        header.pack(anchor="nw", pady=(12, 8), padx=24)
        sub = tk.Label(page, text="Ajustes e informações do aplicativo.", bg=THEME["bg"], fg=THEME['text_secondary'], font=self._font(11, min_size=10, max_size=13), wraplength=720, justify="left")
        sub.pack(anchor="nw", padx=24)

        settings_card = RoundedCard(page, "Informações do aplicativo", "#2563EB", width=1060, height=160)
        settings_card.pack(padx=24, pady=16, fill="x")
        tk.Label(settings_card.inner_frame, text="Versão: 1.0", bg=THEME["card_bg"], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13)).pack(anchor="w", pady=4)
        tk.Label(settings_card.inner_frame, text="Tema: Claro", bg=THEME["card_bg"], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13)).pack(anchor="w", pady=4)
        tk.Label(settings_card.inner_frame, text="Estilo: Dashboard moderno", bg=THEME["card_bg"], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13)).pack(anchor="w", pady=4)
        tk.Button(settings_card.inner_frame, text="Configurar atualização automática", bg=THEME['accent_blue'], fg=THEME["tooltip_fg"], bd=0, relief="flat", padx=12, pady=8, cursor="hand2", command=self._open_settings_dialog).pack(anchor="e", pady=(8, 0))

        reports_card = RoundedCard(page, "Relatórios", "#0F766E", width=1060, height=220)
        reports_card.pack(padx=24, pady=(0, 16), fill="x")
        tk.Label(reports_card.inner_frame, text="Configuração de envio de e-mail", bg=THEME["card_bg"], fg=THEME['text_primary'], font=self._font(12, min_size=10, max_size=14, weight="bold")).pack(anchor="w", pady=(8, 4))
        tk.Label(reports_card.inner_frame, text="Ajuste API principal e reserva, destinatário, remetente, assunto, corpo do e-mail e o comportamento de reenvio quando houver falha.", bg=THEME["card_bg"], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12), wraplength=980, justify="left").pack(anchor="w", pady=(0, 10))
        action_row = tk.Frame(reports_card.inner_frame, bg=THEME['card_bg'])
        action_row.pack(fill="x", pady=(4, 0))
        tk.Button(action_row, text="Configurar e-mail", bg=THEME['accent_blue'], fg=THEME["tooltip_fg"], bd=0, relief="flat", padx=14, pady=9, cursor="hand2", command=lambda: self.show_page("Email")).pack(side="left")
        tk.Label(action_row, text="A página de e-mail abre diretamente aqui para edição rápida.", bg=THEME["card_bg"], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12), wraplength=620, justify="left").pack(side="left", padx=(12, 0))

    def _build_email_settings_page(self):
        page = self.pages["Email"]
        self._create_page_header(page, "Relatórios por e-mail", "Configure o envio profissional de relatórios via API Resend, personalize o texto do e-mail, defina uma API reserva e guarde relatórios para envio posterior se necessário.", accent=THEME['accent_blue'])

        self.report_auto_send = tk.BooleanVar(value=bool(self._report_settings.get('auto_send', False)))
        self.report_recipient = tk.StringVar(value=self._report_settings.get('recipient_email', ''))
        self.report_api_key = tk.StringVar(value=self._report_settings.get('resend_api_key', ''))
        self.report_backup_api_key = tk.StringVar(value=self._report_settings.get('backup_api_key', ''))
        self.report_subject_template = tk.StringVar(value=self._report_settings.get('email_subject_template', 'Relatório de Manutenção - {computer_name} - {date}'))
        self.report_from_email = tk.StringVar(value=self._report_settings.get('from_email', 'onboarding@resend.dev'))
        self.report_api_key_visible = tk.BooleanVar(value=False)
        self.report_backup_api_key_visible = tk.BooleanVar(value=False)
        self.report_save_pending = tk.BooleanVar(value=bool(self._report_settings.get('save_pending_on_failure', True)))
        self.email_status_var = tk.StringVar(value="🔴 Não Configurada")
        self.internet_status_var = tk.StringVar(value="🔴 Offline")
        self.last_send_var = tk.StringVar(value="Sem envios ainda")

        email_card = RoundedCard(page, "Envio de Relatórios", THEME['accent_blue'], width=1060, height=540)
        email_card.pack(padx=24, pady=(0, 16), fill="x")
        tk.Label(email_card.inner_frame, text="Obtenha sua API Key em: https://resend.com/api-keys", bg=THEME["card_bg"], fg=THEME['text_secondary'], font=self._font(9, min_size=8, max_size=11)).pack(anchor="w", pady=(4, 8))

        status_frame = tk.Frame(email_card.inner_frame, bg=THEME['card_bg'])
        status_frame.pack(fill="x", pady=(0, 8))
        tk.Label(status_frame, text="Status da API", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12, weight="bold")).pack(side="left")
        tk.Label(status_frame, textvariable=self.email_status_var, bg=THEME['card_bg'], fg=THEME['accent_green'], font=self._font(10, min_size=9, max_size=12)).pack(side="left", padx=(8, 16))
        tk.Label(status_frame, text="Internet", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12, weight="bold")).pack(side="left")
        tk.Label(status_frame, textvariable=self.internet_status_var, bg=THEME['card_bg'], fg=THEME['accent_green'], font=self._font(10, min_size=9, max_size=12)).pack(side="left", padx=(8, 16))
        tk.Label(status_frame, text="Último envio", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12, weight="bold")).pack(side="left")
        tk.Label(status_frame, textvariable=self.last_send_var, bg=THEME['card_bg'], fg=THEME['text_secondary'], font=self._font(10, min_size=9, max_size=12), wraplength=280, justify="left").pack(side="left", padx=(8, 0))

        tk.Checkbutton(email_card.inner_frame, text="Enviar automaticamente após gerar relatório", variable=self.report_auto_send, bg=THEME['card_bg'], fg=THEME['text_primary'], selectcolor=THEME['accent_blue'], activebackground=THEME['card_bg']).pack(anchor="w", pady=4)
        tk.Checkbutton(email_card.inner_frame, text="Salvar localmente para envio posterior se falhar", variable=self.report_save_pending, bg=THEME['card_bg'], fg=THEME['text_primary'], selectcolor=THEME['accent_blue'], activebackground=THEME['card_bg']).pack(anchor="w", pady=4)

        action_bar = tk.Frame(email_card.inner_frame, bg=THEME['card_bg'])
        action_bar.pack(fill="x", pady=(8, 10))
        self._create_action_button(action_bar, "💾 Salvar configuração", self._save_report_settings, bg=THEME['accent_green']).pack(side="left")
        self._create_action_button(action_bar, "🧪 Testar envio", self._test_report_delivery, bg=THEME['accent_orange']).pack(side="left", padx=(8, 0))
        self._create_action_button(action_bar, "📬 Enviar pendentes", self._send_pending_reports, bg=THEME['accent_purple']).pack(side="left", padx=(8, 0))

        tk.Label(email_card.inner_frame, text="Email destinatário", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12)).pack(anchor="w", pady=(6, 2))
        self._create_input_field(email_card.inner_frame, self.report_recipient).pack(fill="x", pady=2)

        tk.Label(email_card.inner_frame, text="Assunto do e-mail", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12)).pack(anchor="w", pady=(6, 2))
        self._create_input_field(email_card.inner_frame, self.report_subject_template).pack(fill="x", pady=2)

        tk.Label(email_card.inner_frame, text="Texto do e-mail", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12)).pack(anchor="w", pady=(6, 2))
        self.report_body_template_text = tk.Text(email_card.inner_frame, height=8, bg=THEME['card_bg'], fg=THEME['text_primary'], bd=1, relief="solid", highlightthickness=1, highlightbackground=THEME['shadow_hover'], highlightcolor=THEME['accent_blue'])
        self.report_body_template_text.pack(fill="x", pady=2)
        self.report_body_template_text.insert("1.0", self._report_settings.get('email_body_template', ''))

        tk.Label(email_card.inner_frame, text="API Key Resend (principal)", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12)).pack(anchor="w", pady=(6, 2))
        api_frame = tk.Frame(email_card.inner_frame, bg=THEME['card_bg'])
        api_frame.pack(fill="x", pady=2)
        self.report_api_key_entry = self._create_input_field(api_frame, self.report_api_key, show='*')
        self.report_api_key_entry.pack(side="left", fill="x", expand=True)
        self._create_action_button(api_frame, "Mostrar", self._toggle_report_api_visibility, bg=THEME['accent_blue'], padx=10, pady=8).pack(side="left", padx=(8, 0))
        self._create_action_button(api_frame, "Colar", self._paste_report_api_key, bg=THEME['muted'], fg=THEME['text_primary'], padx=10, pady=8).pack(side="left", padx=(8, 0))
        self._create_action_button(api_frame, "Enviar e-mail teste", self._test_report_delivery, bg=THEME['accent_orange'], padx=10, pady=8).pack(side="left", padx=(8, 0))

        tk.Label(email_card.inner_frame, text="API Key Reserva", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12)).pack(anchor="w", pady=(6, 2))
        backup_frame = tk.Frame(email_card.inner_frame, bg=THEME['card_bg'])
        backup_frame.pack(fill="x", pady=2)
        self.report_backup_api_key_entry = self._create_input_field(backup_frame, self.report_backup_api_key, show='*')
        self.report_backup_api_key_entry.pack(side="left", fill="x", expand=True)
        self._create_action_button(backup_frame, "Mostrar", self._toggle_report_backup_api_visibility, bg=THEME['accent_blue'], padx=10, pady=8).pack(side="left", padx=(8, 0))

        tk.Label(email_card.inner_frame, text="Email remetente", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(10, min_size=9, max_size=12)).pack(anchor="w", pady=(6, 2))
        self._create_input_field(email_card.inner_frame, self.report_from_email).pack(fill="x", pady=2)

        button_frame = tk.Frame(email_card.inner_frame, bg=THEME['card_bg'])
        button_frame.pack(fill="x", pady=(12, 0))
        self._create_action_button(button_frame, "Voltar", lambda: self.show_page("Configurações"), bg=THEME['muted'], fg=THEME['text_primary'], padx=12, pady=8).pack(side="left")

        history_frame = tk.Frame(page, bg=THEME['card_bg'], highlightbackground=THEME['shadow_hover'], highlightthickness=1, bd=0)
        history_frame.pack(fill="x", padx=24, pady=(0, 24))
        tk.Label(history_frame, text="Histórico recente", bg=THEME['card_bg'], fg=THEME['text_primary'], font=self._font(11, min_size=10, max_size=13, weight="bold")).pack(anchor="w", padx=16, pady=(12, 6))
        self.email_history_text = tk.Text(history_frame, height=8, bg=THEME['card_bg'], bd=0, relief="flat", font=self._font(10, min_size=9, max_size=12), fg=THEME['text_primary'])
        self.email_history_text.pack(fill="x", padx=16, pady=(0, 12))
        self._refresh_email_status_widgets()

    def _toggle_report_api_visibility(self):
        if hasattr(self, 'report_api_key_entry') and self.report_api_key_visible.get():
            self.report_api_key_entry.configure(show='*')
            self.report_api_key_visible.set(False)
        elif hasattr(self, 'report_api_key_entry'):
            self.report_api_key_entry.configure(show='')
            self.report_api_key_visible.set(True)

    def _toggle_report_backup_api_visibility(self):
        if hasattr(self, 'report_backup_api_key_entry') and self.report_backup_api_key_visible.get():
            self.report_backup_api_key_entry.configure(show='*')
            self.report_backup_api_key_visible.set(False)
        elif hasattr(self, 'report_backup_api_key_entry'):
            self.report_backup_api_key_entry.configure(show='')
            self.report_backup_api_key_visible.set(True)

    def _refresh_email_status_widgets(self):
        if not hasattr(self, 'email_status_var'):
            return
        service = self.maintenance_coordinator.email_service
        api_error = service.validate_api_key(service.api_key)
        self.email_status_var.set("🟢 Configurada" if not api_error else "🔴 Não Configurada")
        self.internet_status_var.set("🟢 Online" if service.check_internet(timeout=2) else "🔴 Offline")
        pending_dir = getattr(service, 'pending_reports_dir', None)
        pending_count = 0
        if pending_dir and os.path.isdir(pending_dir):
            pending_count = len([name for name in os.listdir(pending_dir) if name.endswith('.json')])
        history = service.load_recent_history(limit=5)
        if history:
            latest = history[-1]
            self.last_send_var.set(f"{pending_count} pendente(s) | {latest['timestamp']} | {latest['status']}")
            lines = []
            for entry in history:
                detail = entry.get('error', '-') if entry.get('error') not in ('-', '') else 'Enviado'
                lines.append(f"{entry['timestamp']} | {entry['status']} | {detail}")
            self.email_history_text.delete("1.0", tk.END)
            self.email_history_text.insert(tk.END, "\n".join(lines))
        else:
            self.last_send_var.set(f"{pending_count} pendente(s)" if pending_count else "Sem envios ainda")
            self.email_history_text.delete("1.0", tk.END)
            self.email_history_text.insert(tk.END, "Nenhum envio registrado.")

    def _refresh_cleanup_estimate(self):
        if not hasattr(self, 'cleanup_summary'):
            return
        selected_ids = [item_id for item_id, var in self.cleanup_action_vars.items() if var.get()]
        estimate = self.maintenance_coordinator.cleaner.estimate_recovery(selected_ids)
        selected_count = len(selected_ids)
        self.cleanup_summary.config(text=f"Selecionados: {selected_count} • Recuperável: {estimate['total_human']}")
        self._refresh_cleanup_option_cards(estimate=estimate)

    def _refresh_cleanup_option_cards(self, estimate=None):
        if not hasattr(self, 'cleanup_option_cards'):
            return
        estimate_details = estimate.get('details', []) if isinstance(estimate, dict) else []
        estimate_map = {detail.get('id'): detail for detail in estimate_details if isinstance(detail, dict)}
        total_estimate = estimate.get('total_bytes', 0) if isinstance(estimate, dict) else 0
        for action_id, card in self.cleanup_option_cards.items():
            if action_id not in self.cleanup_action_vars:
                continue
            selected = self.cleanup_action_vars[action_id].get()
            active_bg = THEME['sidebar_active_bg'] if selected else THEME['card_bg']
            active_border = THEME['accent_blue'] if selected else THEME['shadow']
            card.configure(highlightbackground=active_border, highlightthickness=2)
            card.configure(bg=active_bg)
            for child in card.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg=active_bg)
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Frame):
                            grandchild.configure(bg=active_bg)
                            for item in grandchild.winfo_children():
                                if isinstance(item, tk.Label):
                                    item.configure(bg=active_bg, fg=THEME['text_primary'] if selected else THEME['text_secondary'])
                                elif isinstance(item, tk.Checkbutton):
                                    item.configure(bg=active_bg)
                        elif isinstance(grandchild, tk.Label):
                            grandchild.configure(bg=active_bg, fg=THEME['text_primary'] if selected else THEME['text_secondary'])
                        elif isinstance(grandchild, tk.Checkbutton):
                            grandchild.configure(bg=active_bg)

            detail = estimate_map.get(action_id, {})
            estimated_bytes = detail.get('bytes', 0) if isinstance(detail, dict) else 0
            if selected and total_estimate > 0 and estimated_bytes > 0:
                percent = min(100.0, (estimated_bytes / total_estimate) * 100.0)
            elif selected and estimated_bytes > 0:
                percent = 100.0
            else:
                percent = 0.0
            if action_id in self.cleanup_option_bars:
                self.cleanup_option_bars[action_id].set_value(percent)
            if action_id in self.cleanup_option_result_labels:
                self.cleanup_option_result_labels[action_id].config(text=detail.get('human', '0 B') if selected else '0 B')

    def _apply_cleanup_results(self, cleanup_results):
        if not hasattr(self, 'cleanup_option_bars'):
            return
        result_map = {}
        for item in cleanup_results or []:
            if isinstance(item, dict) and item.get('id'):
                result_map[item['id']] = item
        for action_id, bar in self.cleanup_option_bars.items():
            result = result_map.get(action_id)
            if not result:
                continue
            actual_bytes = result.get('freed_bytes', 0) or 0
            estimated_bytes = 0
            if action_id in self.cleanup_action_vars and self.cleanup_action_vars[action_id].get():
                estimate = self.maintenance_coordinator.cleaner.estimate_recovery([action_id])
                details = estimate.get('details', []) if isinstance(estimate, dict) else []
                if details:
                    estimated_bytes = details[0].get('bytes', 0) or 0
            if estimated_bytes > 0:
                percent = min(100.0, (actual_bytes / estimated_bytes) * 100.0 if estimated_bytes else 100.0)
            else:
                percent = 100.0 if actual_bytes > 0 else 0.0
            bar.set_value(percent)
            if action_id in self.cleanup_option_result_labels:
                self.cleanup_option_result_labels[action_id].config(text=result.get('freed', '0 B'))

    def _reset_cleanup_ui(self):
        if not hasattr(self, 'cleanup_output'):
            return
        self.cleanup_output.delete("1.0", tk.END)
        self.cleanup_output.insert(tk.END, "Aguardando início da manutenção...\n")
        if hasattr(self, 'cleanup_progress'):
            self.cleanup_progress['value'] = 0
        if hasattr(self, 'cleanup_progress_label'):
            self.cleanup_progress_label.config(text="0%")
        for step_name, label in self.cleanup_step_labels.items():
            label.config(text=f"☐ {step_name}")

    def _update_cleanup_step(self, step_name: str, status: str):
        if step_name not in self.cleanup_step_labels:
            return
        icon = "☑" if status == "done" else "⚠" if status == "error" else "⏳"
        self.cleanup_step_labels[step_name].config(text=f"{icon} {step_name}")

    def _update_cleanup_progress(self, percent: int):
        if hasattr(self, 'cleanup_progress'):
            self.cleanup_progress['value'] = percent
        if hasattr(self, 'cleanup_progress_label'):
            self.cleanup_progress_label.config(text=f"{percent}%")

    def _append_cleanup_log(self, message: str):
        if hasattr(self, 'cleanup_output'):
            self.cleanup_output.insert(tk.END, f"{message}\n")
            self.cleanup_output.see(tk.END)

    def _set_cleanup_buttons_state(self, enabled: bool):
        for widget_name in [
            'cleanup_start_button',
            'cleanup_reports_button',
            'cleanup_send_button',
        ]:
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.configure(state="normal" if enabled else "disabled")

    def _save_report_settings(self):
        body_template = self.report_body_template_text.get("1.0", tk.END).strip() if hasattr(self, 'report_body_template_text') else ""
        self._report_settings = {
            "auto_send": bool(self.report_auto_send.get()),
            "resend_api_key": self.report_api_key.get(),
            "backup_api_key": self.report_backup_api_key.get() if hasattr(self, 'report_backup_api_key') else "",
            "recipient_email": self.report_recipient.get(),
            "from_email": self.report_from_email.get(),
            "email_subject_template": self.report_subject_template.get() if hasattr(self, 'report_subject_template') else "Relatório de Manutenção - {computer_name} - {date}",
            "email_body_template": body_template,
            "save_pending_on_failure": bool(self.report_save_pending.get()) if hasattr(self, 'report_save_pending') else True,
        }
        self.report_settings_manager.save(self._report_settings)
        self.maintenance_coordinator.email_service.save_config(self._report_settings)
        self._append_cleanup_log("Configurações de relatórios salvas.")
        self._refresh_email_status_widgets()

    def _paste_report_api_key(self):
        try:
            self.report_api_key.set(self.clipboard_get())
            self._append_cleanup_log("Chave de API colada da área de transferência.")
        except tk.TclError:
            self._append_cleanup_log("Não há texto na área de transferência.")

    def _open_reports_folder(self):
        folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Relatorio_Limpeza'))
        os.makedirs(folder, exist_ok=True)
        try:
            if os.name == 'nt':
                os.startfile(folder)
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception as exc:
            self._append_cleanup_log(f"Não foi possível abrir a pasta: {exc}")

    def _test_report_delivery(self):
        body_template = self.report_body_template_text.get("1.0", tk.END).strip() if hasattr(self, 'report_body_template_text') else ""
        self._report_settings = self.report_settings_manager.load()
        self._report_settings.update({
            "auto_send": bool(self.report_auto_send.get()) if hasattr(self, 'report_auto_send') else bool(self._report_settings.get('auto_send', False)),
            "resend_api_key": self.report_api_key.get() if hasattr(self, 'report_api_key') else self._report_settings.get('resend_api_key', ''),
            "backup_api_key": self.report_backup_api_key.get() if hasattr(self, 'report_backup_api_key') else self._report_settings.get('backup_api_key', ''),
            "recipient_email": self.report_recipient.get() if hasattr(self, 'report_recipient') else self._report_settings.get('recipient_email', ''),
            "from_email": self.report_from_email.get() if hasattr(self, 'report_from_email') else self._report_settings.get('from_email', 'onboarding@resend.dev'),
            "email_subject_template": self.report_subject_template.get() if hasattr(self, 'report_subject_template') else self._report_settings.get('email_subject_template', 'Relatório de Manutenção - {computer_name} - {date}'),
            "email_body_template": body_template if body_template else self._report_settings.get('email_body_template', ''),
            "save_pending_on_failure": bool(self.report_save_pending.get()) if hasattr(self, 'report_save_pending') else bool(self._report_settings.get('save_pending_on_failure', True)),
        })
        self.report_settings_manager.save(self._report_settings)
        self.maintenance_coordinator.email_service.save_config(self._report_settings)

        api_key = self._report_settings.get("resend_api_key", "").strip()
        recipient = self._report_settings.get("recipient_email", "").strip()

        if not api_key:
            self._append_cleanup_log("❌ API Key Resend não configurada.")
            self._append_cleanup_log("   → Acesse Configurações e preencha 'API Key Resend'")
            return

        if not recipient:
            self._append_cleanup_log("❌ Email destinatário não configurado.")
            self._append_cleanup_log("   → Acesse Configurações e preencha 'Email destinatário'")
            return

        try:
            self._append_cleanup_log("📧 Enviando teste de relatório...")
            result = self.maintenance_coordinator.test_send(self._report_settings)
            if result.get("success"):
                self._append_cleanup_log("✅ Email enviado com sucesso.")
            else:
                self._append_cleanup_log(f"❌ {result.get('message', 'Falha no teste de envio.')}")
        except Exception as exc:
            self._append_cleanup_log(f"❌ Erro no teste de envio: {exc}")
            self._append_cleanup_log("   → Verifique se a API Key está correta na aba Configurações")
        self._refresh_email_status_widgets()

    def _send_last_report(self):
        body_template = self.report_body_template_text.get("1.0", tk.END).strip() if hasattr(self, 'report_body_template_text') else ""
        self._report_settings = self.report_settings_manager.load()
        self._report_settings.update({
            "auto_send": bool(self.report_auto_send.get()) if hasattr(self, 'report_auto_send') else bool(self._report_settings.get('auto_send', False)),
            "resend_api_key": self.report_api_key.get() if hasattr(self, 'report_api_key') else self._report_settings.get('resend_api_key', ''),
            "backup_api_key": self.report_backup_api_key.get() if hasattr(self, 'report_backup_api_key') else self._report_settings.get('backup_api_key', ''),
            "recipient_email": self.report_recipient.get() if hasattr(self, 'report_recipient') else self._report_settings.get('recipient_email', ''),
            "from_email": self.report_from_email.get() if hasattr(self, 'report_from_email') else self._report_settings.get('from_email', 'onboarding@resend.dev'),
            "email_subject_template": self.report_subject_template.get() if hasattr(self, 'report_subject_template') else self._report_settings.get('email_subject_template', 'Relatório de Manutenção - {computer_name} - {date}'),
            "email_body_template": body_template if body_template else self._report_settings.get('email_body_template', ''),
            "save_pending_on_failure": bool(self.report_save_pending.get()) if hasattr(self, 'report_save_pending') else bool(self._report_settings.get('save_pending_on_failure', True)),
        })
        self.report_settings_manager.save(self._report_settings)
        self.maintenance_coordinator.email_service.save_config(self._report_settings)

        api_key = self._report_settings.get("resend_api_key", "").strip()
        recipient = self._report_settings.get("recipient_email", "").strip()
        from_email = self._report_settings.get("from_email", "").strip()

        if not api_key:
            self._append_cleanup_log("❌ API Key Resend não configurada.")
            self._append_cleanup_log("   → Acesse Configurações e preencha 'API Key Resend'")
            return

        if not recipient:
            self._append_cleanup_log("❌ Email destinatário não configurado.")
            self._append_cleanup_log("   → Acesse Configurações e preencha 'Email destinatário'")
            return

        if not from_email:
            self._append_cleanup_log("❌ Email remetente não configurado.")
            self._append_cleanup_log("   → Acesse Configurações e preencha 'Email remetente'")
            return

        try:
            report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Relatorio_Limpeza'))
            if not os.path.exists(report_dir):
                self._append_cleanup_log("❌ Nenhum relatório encontrado.")
                self._append_cleanup_log("   → Execute uma manutenção primeiro para gerar um relatório")
                return

            report_path = get_latest_report_path(report_dir)
            if not report_path:
                self._append_cleanup_log("❌ Nenhum relatório encontrado.")
                self._append_cleanup_log("   → Execute uma manutenção primeiro para gerar um relatório")
                return

            report_file_name = os.path.basename(report_path)
            report_dt = datetime.fromtimestamp(os.path.getmtime(report_path))
            report_date = format_brazilian_date(report_dt)
            report_time = report_dt.strftime('%H:%M:%S')

            self._append_cleanup_log(f"📧 Enviando relatório: {report_file_name}...")
            result = self.maintenance_coordinator.email_service.send_report(
                recipient_email=recipient,
                subject=self.maintenance_coordinator.email_service.generate_subject(os.environ.get('COMPUTERNAME', 'Sistema'), report_date=report_date),
                body=self.maintenance_coordinator.email_service.generate_body(
                    {"system": {"computer_name": os.environ.get('COMPUTERNAME', 'Sistema'), "os_name": os.name == 'nt' and 'Windows' or 'Linux', "version": '1.0'}},
                    report_path,
                    0,
                    report_date=report_date,
                    report_time=report_time,
                ),
                attachment_path=report_path,
            )
            if result.get("success"):
                self._append_cleanup_log("✅ Relatório enviado com sucesso.")
            else:
                self._append_cleanup_log(f"❌ {result.get('message', 'Falha ao enviar relatório.')}")
        except Exception as exc:
            self._append_cleanup_log(f"❌ Erro ao enviar relatório: {exc}")
            self._append_cleanup_log("   → Verifique se a API Key está correta na aba Configurações")
        self._refresh_email_status_widgets()

    def _send_pending_reports(self):
        self._report_settings = self.report_settings_manager.load()
        body_template = self.report_body_template_text.get("1.0", tk.END).strip() if hasattr(self, 'report_body_template_text') else ""
        self._report_settings.update({
            "auto_send": bool(self.report_auto_send.get()) if hasattr(self, 'report_auto_send') else bool(self._report_settings.get('auto_send', False)),
            "resend_api_key": self.report_api_key.get() if hasattr(self, 'report_api_key') else self._report_settings.get('resend_api_key', ''),
            "backup_api_key": self.report_backup_api_key.get() if hasattr(self, 'report_backup_api_key') else self._report_settings.get('backup_api_key', ''),
            "recipient_email": self.report_recipient.get() if hasattr(self, 'report_recipient') else self._report_settings.get('recipient_email', ''),
            "from_email": self.report_from_email.get() if hasattr(self, 'report_from_email') else self._report_settings.get('from_email', 'onboarding@resend.dev'),
            "email_subject_template": self.report_subject_template.get() if hasattr(self, 'report_subject_template') else self._report_settings.get('email_subject_template', 'Relatório de Manutenção - {computer_name} - {date}'),
            "email_body_template": body_template if body_template else self._report_settings.get('email_body_template', ''),
            "save_pending_on_failure": bool(self.report_save_pending.get()) if hasattr(self, 'report_save_pending') else bool(self._report_settings.get('save_pending_on_failure', True)),
        })
        self.report_settings_manager.save(self._report_settings)
        self.maintenance_coordinator.email_service.save_config(self._report_settings)
        result = self.maintenance_coordinator.email_service.send_pending_reports()
        self._append_cleanup_log(result.get("message", "Processamento concluído."))
        self._refresh_email_status_widgets()

    def _settings_path(self):
        return os.path.join(os.path.dirname(__file__), '..', 'settings.json') if getattr(sys := __import__('sys'), 'frozen', False) == False else os.path.join(os.path.dirname(sys.executable), 'settings.json')

    def _load_settings(self):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'settings.json'))
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
            else:
                self._settings = {'periodic_enabled': False, 'interval_seconds': 60}
        except Exception:
            self._settings = {'periodic_enabled': False, 'interval_seconds': 60}

    def _save_settings(self):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'settings.json'))
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _open_settings_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title('Configurações de Atualização')
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry('420x200')

        enabled_var = tk.BooleanVar(value=bool(self._settings.get('periodic_enabled', False)))
        tk.Checkbutton(dialog, text='Habilitar atualização periódica', variable=enabled_var, font=self._font(11), bg=THEME['bg']).pack(anchor='w', padx=16, pady=(12, 6))

        tk.Label(dialog, text='Intervalo:', font=self._font(10), bg=THEME['bg']).pack(anchor='w', padx=16, pady=(6, 0))
        options = ['Desativado', '30s', '1m', '2m', '5m', '10m']
        current_seconds = int(self._settings.get('interval_seconds', 60) or 0)
        mapping = {0: 'Desativado', 30: '30s', 60: '1m', 120: '2m', 300: '5m', 600: '10m'}
        selected = tk.StringVar(value=mapping.get(current_seconds, '1m'))
        combo = ttk.Combobox(dialog, values=options, state='readonly', textvariable=selected)
        combo.pack(anchor='w', padx=16, pady=(4, 8))

        def on_save():
            val = selected.get()
            sec = 0 if val == 'Desativado' else (30 if val == '30s' else (60 if val == '1m' else (120 if val == '2m' else (300 if val == '5m' else 600))))
            self._settings['periodic_enabled'] = bool(enabled_var.get()) and sec > 0
            self._settings['interval_seconds'] = sec
            self._save_settings()
            dialog.grab_release()
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=THEME['bg'])
        btn_frame.pack(fill='x', side='bottom', pady=12)
        tk.Button(btn_frame, text='Salvar', bg=THEME["accent_blue"], fg=THEME["tooltip_fg"], bd=0, relief='flat', padx=12, pady=8, command=on_save).pack(side='right', padx=12)
        tk.Button(btn_frame, text='Cancelar', bg=THEME['muted'], fg=THEME["text_primary"], bd=0, relief='flat', padx=12, pady=8, command=lambda: (dialog.grab_release(), dialog.destroy())).pack(side='right')

    def _start_periodic_timer(self):
        def target():
            try:
                self._periodic_worker()
            except Exception:
                pass
        t = threading.Thread(target=target, daemon=True)
        t.start()

    def _periodic_worker(self):
        while not self._periodic_stop.is_set():
            settings = self._settings or {}
            enabled = settings.get('periodic_enabled', False)
            interval = int(settings.get('interval_seconds', 0) or 0)
            if enabled and interval > 0:
                # aguarda com checks curtos para permitir parada rápida
                end = time.time() + interval
                while time.time() < end and not self._periodic_stop.is_set():
                    time.sleep(0.5)
                if self._periodic_stop.is_set():
                    break
                # dispara atualização na thread principal
                try:
                    self.after(0, self.run_diagnostics)
                except Exception:
                    pass
            else:
                time.sleep(1.0)

    def _on_close(self):
        self._destroying = True
        try:
            self._periodic_stop.set()
        except Exception:
            pass
        self.destroy()

    def _build_footer(self):
        self.footer_label = tk.Label(self.content, text="", bg=THEME["bg"])
        self.footer_label.pack_forget()
        self.footer_status = tk.Label(self.content, text="", bg=THEME["bg"])
        self.footer_status.pack_forget()
        self.footer_reading = tk.Label(self.content, text="", bg=THEME["bg"])
        self.footer_reading.pack_forget()
        self.footer_runtime = tk.Label(self.content, text="", bg=THEME["bg"])
        self.footer_runtime.pack_forget()

    def _handle_window_resize(self, event=None):
        if not self.winfo_exists() or self.selected_page != "Dashboard":
            return

        width = self.winfo_width()
        height = self.winfo_height()
        if (width, height) == self._last_window_size:
            return

        self._last_window_size = (width, height)
        if self.winfo_exists() and not self._destroying:
            self._layout_dashboard_cards()

        for widget in (getattr(self, 'status_message', None), getattr(self, 'update_label', None)):
            if widget is not None and widget.winfo_exists():
                widget.update_idletasks()

    def _layout_dashboard_cards(self):
        if not hasattr(self, "dashboard_cards_frame") or not self.dashboard_cards_frame.winfo_ismapped():
            return

        available_width = max(620, self.winfo_width() - 240)
        card_width = min(460, max(270, int((available_width - 24) / 2)))
        columns = 2 if card_width >= 280 else 1
        card_height = 320 if available_width >= 940 else 300

        try:
            for index in range(4):
                self.dashboard_cards_frame.grid_columnconfigure(index, weight=1 if index < columns else 0)
            self.dashboard_cards_frame.grid_rowconfigure(0, weight=1)
            self.dashboard_cards_frame.grid_rowconfigure(1, weight=1)
            self.dashboard_cards_frame.grid_rowconfigure(2, weight=1)
            self.dashboard_cards_frame.grid_rowconfigure(3, weight=1)
        except Exception:
            return

        cards = [getattr(self, "cpu_card", None), getattr(self, "ram_card", None), getattr(self, "storage_card", None), getattr(self, "system_card", None)]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)] if columns == 2 else [(0, 0), (1, 0), (2, 0), (3, 0)]

        for card, (row, column) in zip(cards, positions):
            if card is not None and card.winfo_exists():
                try:
                    card.grid_configure(row=row, column=column, sticky="nsew")
                    card.resize(card_width, card_height)
                    self._update_dashboard_card_content(card, card_width)
                except Exception:
                    continue

    def _update_dashboard_card_content(self, card, card_width: int):
        if card is None or not card.winfo_exists():
            return

        try:
            card.inner_frame.configure(width=max(card_width - 36, 0))
        except Exception:
            pass

        if card is self.cpu_card:
            bar_width = max(120, min(220, int(card_width * 0.38)))
            if hasattr(self, "progress_cpu_temp"):
                self.progress_cpu_temp.resize(bar_width)
            if hasattr(self, "progress_cpu_usage"):
                self.progress_cpu_usage.resize(bar_width)
            if hasattr(self, "lbl_cpu_name"):
                self.lbl_cpu_name.configure(wraplength=max(220, card_width - 40))
        elif card is self.ram_card:
            bar_width = max(180, min(320, int(card_width - 60)))
            if hasattr(self, "progress_ram_usage"):
                self.progress_ram_usage.resize(bar_width)
            if hasattr(self, "lbl_ram_total"):
                self.lbl_ram_total.configure(wraplength=max(220, card_width - 40))
        elif card is self.storage_card:
            bar_width = max(120, min(220, int(card_width * 0.38)))
            if hasattr(self, "progress_ssd_usage"):
                self.progress_ssd_usage.resize(bar_width)
            if hasattr(self, "progress_ssd_temp"):
                self.progress_ssd_temp.resize(bar_width)
            if hasattr(self, "lbl_ssd_model"):
                self.lbl_ssd_model.configure(wraplength=max(220, card_width - 40))
        elif card is self.system_card:
            if hasattr(self, "lbl_system_os"):
                self.lbl_system_os.configure(wraplength=max(220, card_width - 40))


    def show_page(self, page_name: str):
        if page_name not in self.pages:
            return
        self.selected_page = page_name
        for name, page in self.pages.items():
            if name == page_name:
                page.pack(fill="both", expand=True)
                page.lift()
            else:
                page.pack_forget()
        self._set_nav_button_active()
        if page_name == "Dashboard":
            self._render_dashboard(self.data)
        elif page_name == "Informações":
            self._render_info_page(self.data)
        self.after(50, self._on_page_inner_configure)

    def _collect_hardware_payload(self, force: bool = False):
        """Coleta os dados com fallback para a rota direta de hardware, restaurando o fluxo que preenche o dashboard."""
        try:
            service = HardwareService()
            # Use the full normalized collection to ensure fields (percent, totals, temps)
            # are populated by the Python services instead of returning raw host payload
            data = service.collect()
            if isinstance(data, dict) and data:
                data.setdefault("collected_at", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                data.setdefault("debug_file", os.path.join(os.path.dirname(__file__), "modules", "hardware_debug.txt"))
                data.setdefault("log_file", os.path.join(os.path.dirname(__file__), "modules", "hardware_service.log"))
                return data
        except Exception:
            data = None

        try:
            if self.collector is not None:
                if force:
                    self.collector.invalidate()
                cached = self.collector.collect(force=force)
                if isinstance(cached, dict) and cached:
                    return cached
        except Exception:
            pass

        return data or {}

    def _run_initial_diagnostics(self):
        """Coleta automática ao iniciar o aplicativo"""
        self._set_status_message("🔄 Coletando informações do sistema...")
        self.collect_button.configure(state="disabled")

        def worker():
            try:
                data = self._collect_hardware_payload(force=True)
                self._schedule_ui_update(lambda: self._display_initial_diagnostics(data))
            except Exception as exc:
                self._schedule_ui_update(lambda: self._display_diagnostics_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _display_initial_diagnostics(self, data):
        """Exibe resultado da coleta inicial com mensagem de sucesso"""
        self.data = data
        self._set_status_message("✔ Dados atualizados com sucesso.")
        self.update_label.config(text=f"Última atualização: {data.get('collected_at', 'agora')}")
        self._update_footer_status("pronto", data.get('collected_at', 'agora'))
        self._render_dashboard(data)
        self._render_info_page(data)
        self.collect_button.configure(state="normal")

    def run_diagnostics(self):
        self.clear_diagnostics()
        self._set_status_message("🔄 Coletando informações...")
        self.collect_button.configure(state="disabled", text="⟳ Coletando...")
        self._start_loading_animation()

        def worker():
            try:
                data = self._collect_hardware_payload(force=True)
                self._schedule_ui_update(lambda: self._display_diagnostics(data))
            except Exception as exc:
                self._schedule_ui_update(lambda: self._display_diagnostics_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _display_diagnostics(self, data):
        self._stop_loading_animation()
        self.data = data
        self._set_status_message("✔ Dados atualizados com sucesso.")
        self.update_label.config(text=f"Última atualização: {data.get('collected_at', 'agora')}")
        self._update_footer_status("pronto", data.get('collected_at', 'agora'))
        self._render_dashboard(data)
        self._render_info_page(data)
        self.collect_button.configure(state="normal", text="⟳ Atualizar")

    def _display_diagnostics_error(self, exc):
        self._stop_loading_animation()
        self._set_status_message("❌ Erro na coleta de dados.")
        self._update_footer_status("erro", datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        self.collect_button.configure(state="normal", text="⟳ Atualizar")

    def clear_diagnostics(self):
        self.data = {}
        self._clear_dashboard()
        self._clear_info_page()
        self._set_status_message("Pronto para coletar")
        self.update_label.config(text="Última atualização: nunca")
        self._update_footer_status("pronto", "nunca")

    def _update_footer_status(self, status: str, reading: str):
        return None

    def _set_status_message(self, message: str):
        if hasattr(self, "status_message") and self.status_message.winfo_exists():
            self.status_message.config(text=message)

    def _start_loading_animation(self):
        """Inicia animação de loading no status"""
        if not hasattr(self, '_loading_active'):
            self._loading_active = False
        if not hasattr(self, '_loading_frame'):
            self._loading_frame = 0
        self._loading_active = True
        self._animate_loading()

    def _animate_loading(self):
        """Anima pontos de carregamento"""
        if not self._loading_active:
            return
        frames = ["🔄 Coletando informações.  ", "🔄 Coletando informações.. ", "🔄 Coletando informações..."]
        self._set_status_message(frames[self._loading_frame % 3])
        self._loading_frame += 1
        self.after(500, self._animate_loading)

    def _stop_loading_animation(self):
        """Para animação de loading"""
        self._loading_active = False

    def _coerce_number(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.replace("°", "").replace("C", "").replace("c", "").replace("%", "").replace(",", ".").strip()
            if not text:
                return None
            try:
                return float(text)
            except ValueError:
                return None
        return None

    def _extract_percent(self, value):
        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return max(0.0, min(100.0, float(value)))

        if isinstance(value, str):
            text = value.replace("%", "").replace(",", ".").strip()
            if not text:
                return 0.0
            try:
                return max(0.0, min(100.0, float(text)))
            except ValueError:
                return 0.0

        return 0.0

    def _parse_size_value(self, value):
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            text = value.strip().lower().replace(" ", "")
            if not text:
                return None
            try:
                if text.endswith("tb"):
                    return float(text[:-2]) * 1024.0
                if text.endswith("gb"):
                    return float(text[:-2])
                if text.endswith("mb"):
                    return float(text[:-2]) / 1024.0
                if text.endswith("kb"):
                    return float(text[:-2]) / 1024.0 / 1024.0
                if text.endswith("b"):
                    return float(text[:-1]) / 1024.0 / 1024.0 / 1024.0
                return float(text)
            except ValueError:
                return None

        return None

    def _extract_disk_percent(self, disk):
        used = self._parse_size_value(disk.get("used"))
        total = self._parse_size_value(disk.get("total"))
        if used is None or total is None or total <= 0:
            return 0.0
        return max(0.0, min(100.0, (used / total) * 100.0))

    def _format_size(self, value):
        if value is None:
            return "N/A"

        if isinstance(value, (int, float)):
            size = float(value)
            if size >= 1024 ** 3:
                return f"{size / 1024 ** 3:.1f} GB"
            if size >= 1024 ** 2:
                return f"{size / 1024 ** 2:.1f} MB"
            if size >= 1024:
                return f"{size / 1024:.1f} KB"
            return f"{size:.0f} B"

        if isinstance(value, str):
            parsed = self._parse_size_value(value)
            return self._format_size(parsed) if parsed is not None else value

        return str(value)

    def _format_temperature(self, value):
        if value is None:
            return "N/A"

        if isinstance(value, (int, float)):
            return f"{float(value):.1f} °C"

        if isinstance(value, str):
            text = value.replace("°", "").replace("c", "").replace("C", "").strip()
            if not text:
                return "N/A"
            try:
                return f"{float(text):.1f} °C"
            except ValueError:
                return value

        return str(value)

    def _format_frequency(self, value):
        if value is None:
            return "N/A"

        if isinstance(value, (int, float)):
            number = float(value)
            if number >= 1000.0:
                return f"{number / 1000.0:.2f} GHz"
            return f"{number:.1f} MHz"

        if isinstance(value, str):
            text = value.strip().lower()
            if text.endswith("ghz") or text.endswith("mhz"):
                return value
            cleaned = text.replace("mhz", "").replace("ghz", "").strip()
            try:
                number = float(cleaned)
                if number >= 1000.0:
                    return f"{number / 1000.0:.2f} GHz"
                return f"{number:.1f} MHz"
            except ValueError:
                return value

        return str(value)

    def _format_memory_speed(self, value):
        if value is None:
            return "Não disponível"

        if isinstance(value, (int, float)):
            return f"{float(value):.0f} MHz"

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return "Não disponível"
            if text.lower().endswith("mhz"):
                return text
            if text.lower().endswith("ghz"):
                return text
            cleaned = text.replace("mhz", "").replace("ghz", "").strip()
            try:
                return f"{float(cleaned):.0f} MHz"
            except ValueError:
                return text

        return "Não disponível"

    def _format_uptime(self, value):
        if value is None:
            return "N/A"

        seconds = None
        if isinstance(value, (int, float)):
            seconds = float(value)
        elif isinstance(value, str):
            text = value.strip().replace("s", "")
            try:
                seconds = float(text)
            except ValueError:
                return value

        if seconds is None:
            return "N/A"

        minutes = int(seconds // 60)
        hours = int(minutes // 60)
        days = int(hours // 24)
        hours = hours % 24
        minutes = minutes % 60

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes or not parts:
            parts.append(f"{minutes}m")

        return " ".join(parts)

    def _safe_get(self, value, fallback=None):
        if value is None:
            return fallback
        if isinstance(value, str) and not value.strip():
            return fallback
        return value

    def _display_value(self, value, fallback="Indisponível"):
        if value is None:
            return fallback
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return fallback
            lowered = text.lower()
            if "não suportado" in lowered or "unsupported" in lowered or "sensor não suportado" in lowered:
                return fallback
            return text
        return str(value)

    def _is_unavailable_value(self, value):
        if value is None:
            return True
        if isinstance(value, (int, float)):
            return False
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return True
            lowered = text.lower()
            if lowered in {"n/a", "na", "none", "null", "", "-", "—", "indisponível", "indisponivel", "não disponível", "nao disponível", "não suportado", "nao suportado", "unsupported", "not available", "not supported"}:
                return True
            if "não suportado" in lowered or "unsupported" in lowered or "not supported" in lowered or "sensor não suportado" in lowered:
                return True
        return False

    def _set_block_visibility(self, frame, visible, manager=None):
        if frame is None or not frame.winfo_exists():
            return
        if not visible:
            try:
                if manager == "grid":
                    frame.grid_remove()
                elif manager == "pack":
                    frame.pack_forget()
                else:
                    frame.pack_forget()
            except Exception:
                pass
            return
        try:
            if manager == "grid":
                frame.grid()
            elif manager == "pack":
                frame.pack()
            else:
                frame.pack()
        except Exception:
            pass

    def _create_card(self, parent, title, accent, width=520, height=180):
        return RoundedCard(parent, title, accent, width=width, height=height)

    def _create_progressbar(self, parent, value, color=THEME["accent_blue"], width=420):
        bar = ProgressBar(parent, width=width, value=self._extract_percent(value), color=color)
        bar.pack(fill="x", pady=(12, 0))
        return bar

    def _clear_dashboard(self):
        if hasattr(self, "status_message") and self.status_message.winfo_exists():
            self.status_message.config(text="Sistema funcionando normalmente")
        if hasattr(self, "dashboard_widget_states"):
            for state in self.dashboard_widget_states.values():
                if state.get("main_value") and state["main_value"].winfo_exists():
                    state["main_value"].config(text="Não disponível")
                if state.get("progress") and state["progress"].winfo_exists():
                    state["progress"].set_value(0.0)
                for metric in state.get("metric_widgets", []):
                    if metric[1].winfo_exists():
                        metric[1].set_value(0.0)
                    if metric[2].winfo_exists():
                        metric[2].config(text="N/A")
                for row_label, row_value in state.get("row_widgets", []):
                    if row_label.winfo_exists():
                        row_label.config(text="")
                    if row_value.winfo_exists():
                        row_value.config(text="")
                for pill in state.get("status_widgets", []):
                    if pill.winfo_exists():
                        pill.config(text="—")
        if hasattr(self, "quick_status_states"):
            for state in self.quick_status_states:
                if state.get("value") and state["value"].winfo_exists():
                    state["value"].config(text="N/A")
                if state.get("bar") and state["bar"].winfo_exists():
                    state["bar"].set_value(0.0)

    def _clear_info_page(self):
        if hasattr(self, "info_section_states"):
            for state in self.info_section_states.values():
                for row_label, row_value in state.get("row_widgets", []):
                    if row_label.winfo_exists():
                        row_label.config(text="")
                    if row_value.winfo_exists():
                        row_value.config(text="")

    def _render_dashboard(self, data):
        cpu = data.get("cpu", {}) or {}
        ram = data.get("memory", {}) or {}
        disk = (data.get("disks", []) or [{}])[0]
        system = data.get("system", {}) or {}
        
        self._update_quick_metrics(cpu, ram, disk)
        self._update_cpu_card(cpu)
        self._update_ram_card(ram)
        self._update_ssd_card(disk)
        self._update_system_card(system)
        self.cpu_card.set_hover_text(self._build_card_hover_text("cpu", cpu))
        self.ram_card.set_hover_text(self._build_card_hover_text("ram", ram))
        self.storage_card.set_hover_text(self._build_card_hover_text("ssd", disk))
        self.system_card.set_hover_text(self._build_card_hover_text("system", system))
        self._handle_window_resize()

    def _build_card_hover_text(self, kind, payload):
        if kind == "cpu":
            return "\n".join([
                f"Modelo: {payload.get('name', 'Não disponível')}",
                f"Núcleos: {payload.get('physical_cores', 'Não disponível')}",
                f"Threads: {payload.get('threads', 'Não disponível')}",
                f"Clock atual: {payload.get('clock_current', 'Não disponível')}",
                f"Clock máximo: {payload.get('clock_max', 'Não disponível')}",
                f"Uso: {payload.get('usage', 'Não disponível')}",
                f"Temperatura: {payload.get('temperature', 'Não disponível')}",
            ])
        if kind == "ram":
            return "\n".join([
                f"Total: {payload.get('total', 'Não disponível')}",
                f"Em uso: {payload.get('used', 'Não disponível')}",
                f"Livre: {payload.get('free', 'Não disponível')}",
                f"Disponível: {payload.get('available', 'Não disponível')}",
                f"Tipo: {payload.get('type', 'Não disponível')}",
                f"Frequência: {payload.get('speed', 'Não disponível')}",
                f"Fabricante: {payload.get('manufacturer', 'Não disponível')}",
                f"Slots: {payload.get('modules', 'Não disponível')}",
            ])
        if kind == "ssd":
            return "\n".join([
                f"Marca: {payload.get('manufacturer', 'Não disponível')}",
                f"Modelo: {payload.get('model', payload.get('name', 'Não disponível'))}",
                f"Capacidade: {payload.get('total', 'Não disponível')}",
                f"Livre: {payload.get('free', 'Não disponível')}",
                f"Usado: {payload.get('used', 'Não disponível')}",
                f"Temperatura: {payload.get('temperature', 'Não disponível')}",
                f"Saúde: {payload.get('smart_health', 'Não disponível')}",
                f"Firmware: {payload.get('firmware', 'Não disponível')}",
                f"Serial: {payload.get('serial_number', 'Não disponível')}",
            ])
        return "\n".join([
            f"Windows: {payload.get('os_name', 'Não disponível')}",
            f"Versão: {payload.get('version', 'Não disponível')}",
            f"Build: {payload.get('build', 'Não disponível')}",
            f"Arquitetura: {payload.get('architecture', 'Não disponível')}",
            f"Hostname: {payload.get('computer_name', 'Não disponível')}",
            f"Uptime: {payload.get('uptime', 'Não disponível')}",
            f"Status de atualização: {payload.get('update_status', 'Não disponível')}",
        ])

    def _update_quick_metrics(self, cpu, ram, disk):
        cpu_temp_value = self._coerce_number(cpu.get("temperature"))
        cpu_usage_value = self._extract_percent(cpu.get("usage"))
        ram_usage_value = self._extract_percent(ram.get("percent"))
        disk_usage_value = self._extract_disk_percent(disk)
        disk_health_value = self._extract_percent(disk.get("smart_health")) if disk.get("smart_health") is not None else 100.0
        disk_temp_value = self._coerce_number(disk.get("temperature"))
        
        metrics_data = [
            ("cpu_temp", f"{cpu_temp_value:.0f}°C" if cpu_temp_value is not None else "N/A", cpu_temp_value if cpu_temp_value is not None else 0.0, self._temp_color(cpu_temp_value if cpu_temp_value is not None else 0.0)),
            ("cpu_usage", f"{cpu_usage_value:.0f}%", cpu_usage_value, self._status_color(cpu_usage_value, [50, 75, 90])),
            ("ram_usage", f"{ram_usage_value:.0f}%", ram_usage_value, self._status_color(ram_usage_value, [60, 80, 90])),
            ("ssd_temp", f"{disk_temp_value:.0f}°C" if disk_temp_value is not None else "N/A", disk_temp_value if disk_temp_value is not None else 0.0, self._temp_color(disk_temp_value if disk_temp_value is not None else 0.0)),
            ("ssd_health", f"{disk_health_value:.0f}%", disk_health_value, self._status_color(disk_health_value, [95, 80, 60])),
            ("ssd_usage", f"{disk_usage_value:.0f}%", disk_usage_value, self._status_color(disk_usage_value, [70, 85, 95])),
        ]
        
        for key, value_text, fill_value, color in metrics_data:
            if key in self.quick_metrics:
                metric = self.quick_metrics[key]
                metric["value"].config(text=value_text)
                metric["bar"].set_value(fill_value)
                metric["icon"].config(fg=color)

    def _update_cpu_card(self, cpu):
        self.lbl_cpu_name.config(text=self._display_value(cpu.get("name", "Não disponível")))
        
        temp_value = self._coerce_number(cpu.get("temperature"))
        if temp_value is not None:
            self._set_block_visibility(self.cpu_temp_frame, True, manager="grid")
            self.lbl_cpu_temp.config(text=f"{temp_value:.1f}°C", fg=self._temp_color(temp_value))
            self.progress_cpu_temp.set_value(temp_value)
            self.progress_cpu_temp.color = self._temp_color(temp_value)
        else:
            self._set_block_visibility(self.cpu_temp_frame, False, manager="grid")
            self.lbl_cpu_temp.config(text="", fg=THEME["text_secondary"])
            self.progress_cpu_temp.set_value(0.0)
        
        usage_value = self._extract_percent(cpu.get("usage"))
        if usage_value > 0 or not self._is_unavailable_value(cpu.get("usage")):
            self._set_block_visibility(self.cpu_usage_frame, True, manager="grid")
            self.lbl_cpu_usage.config(text=f"{usage_value:.0f}%", fg=self._status_color(usage_value, [50, 75, 90]))
            self.progress_cpu_usage.set_value(usage_value)
            self.progress_cpu_usage.color = self._status_color(usage_value, [50, 75, 90])
        else:
            self._set_block_visibility(self.cpu_usage_frame, False, manager="grid")
            self.lbl_cpu_usage.config(text="", fg=THEME["text_secondary"])
            self.progress_cpu_usage.set_value(0.0)
        
        cpu_rows = [
            ("Núcleos", self._display_value(cpu.get("physical_cores", "Não disponível"))),
            ("Threads", self._display_value(cpu.get("threads", "Não disponível"))),
            ("Clock atual", self._format_frequency(cpu.get("clock_current"))),
            ("Clock máximo", self._format_frequency(cpu.get("clock_max"))),
        ]
        self._update_rows_by_frames(self.cpu_row_frames, cpu_rows)

    def _update_ram_card(self, ram):
        self.lbl_ram_total.config(text=self._display_value(ram.get("total", "Não disponível")))
        
        usage_value = self._extract_percent(ram.get("percent"))
        if usage_value > 0 or not self._is_unavailable_value(ram.get("percent")):
            self._set_block_visibility(self.ram_usage_frame, True, manager="pack")
            self.lbl_ram_usage.config(text=f"{usage_value:.0f}%", fg=self._status_color(usage_value, [60, 80, 90]))
            self.progress_ram_usage.set_value(usage_value)
            self.progress_ram_usage.color = self._status_color(usage_value, [60, 80, 90])
        else:
            self._set_block_visibility(self.ram_usage_frame, False, manager="pack")
            self.lbl_ram_usage.config(text="", fg=THEME["text_secondary"])
            self.progress_ram_usage.set_value(0.0)
        
        ram_speed = self._format_memory_speed(ram.get("speed"))
        ram_rows = [
            ("Tipo", self._display_value(ram.get("type", "Não disponível"))),
            ("Frequência", ram_speed),
            ("Fabricante", self._display_value(ram.get("manufacturer", "Não disponível"))),
            ("Módulos", self._display_value(ram.get("modules", "Não disponível"))),
        ]
        self._update_rows_by_frames(self.ram_row_frames, ram_rows)

    def _update_ssd_card(self, disk):
        model = disk.get("model") or disk.get("name") or "Disco"
        manu = disk.get("manufacturer")
        if not self._is_unavailable_value(manu):
            label = f"{model} — {manu}"
        else:
            label = model
        self.lbl_ssd_model.config(text=self._display_value(label))
        
        usage_value = self._extract_disk_percent(disk)
        if usage_value > 0 or not self._is_unavailable_value(disk.get("used")):
            self._set_block_visibility(self.ssd_usage_frame, True, manager="grid")
            self.lbl_ssd_usage.config(text=f"{usage_value:.0f}%", fg=self._status_color(usage_value, [70, 85, 95]))
            self.progress_ssd_usage.set_value(usage_value)
            self.progress_ssd_usage.color = self._status_color(usage_value, [70, 85, 95])
        else:
            self._set_block_visibility(self.ssd_usage_frame, False, manager="grid")
            self.lbl_ssd_usage.config(text="", fg=THEME["text_secondary"])
            self.progress_ssd_usage.set_value(0.0)
        
        temp_value = self._coerce_number(disk.get("temperature"))
        if temp_value is not None:
            self._set_block_visibility(self.ssd_temp_frame, True, manager="grid")
            self.lbl_ssd_temp.config(text=f"{temp_value:.1f}°C", fg=self._temp_color(temp_value))
            self.progress_ssd_temp.set_value(temp_value)
            self.progress_ssd_temp.color = self._temp_color(temp_value)
        else:
            self._set_block_visibility(self.ssd_temp_frame, False, manager="grid")
            self.lbl_ssd_temp.config(text="", fg=THEME["text_secondary"])
            self.progress_ssd_temp.set_value(0.0)
        
        health_value = self._extract_percent(disk.get("smart_health")) if disk.get("smart_health") is not None else 100.0
        if self._is_unavailable_value(disk.get("smart_health")):
            # Mostrar o nome do disco quando a leitura de saúde não estiver disponível
            self._set_block_visibility(self.ssd_health_frame, True, manager="pack")
            model = disk.get("model") or disk.get("name") or "Disco"
            self.lbl_ssd_health.config(text=self._display_value(model), fg=THEME["text_secondary"])
        else:
            self._set_block_visibility(self.ssd_health_frame, True, manager="pack")
            health_text = self._health_label(health_value)
            health_color = self._status_color(health_value, [95, 80, 60])
            self.lbl_ssd_health.config(text=health_text, fg=health_color)
        
        ssd_rows = [
            ("Modelo", self._display_value(disk.get("model") or disk.get("name") or "Disco")),
            ("Fabricante", self._display_value(disk.get("manufacturer", "Não disponível"))),
            ("Firmware", self._display_value(disk.get("firmware", "Não disponível"))),
            ("Serial", self._display_value(disk.get("serial_number", "Não disponível"))),
            ("Interface", self._display_value(disk.get("interface", "Não disponível"))),
        ]
        self._update_rows_by_frames(self.ssd_row_frames, ssd_rows)

    def _update_system_card(self, system):
        self.lbl_system_os.config(text=self._display_value(system.get("os_name", "Não disponível")))
        network_name = system.get("network_name")
        network_address = system.get("network_address")

        system_rows = [
            ("Versão", self._display_value(system.get("version", "Não disponível"))),
            ("Build", self._display_value(system.get("build", "Não disponível"))),
            ("Arquitetura", self._display_value(system.get("architecture", "Não disponível"))),
            ("Nome", self._display_value(system.get("computer_name", "Não disponível"))),
            ("Atualizações", self._display_value(system.get("update_status", "Não disponível"))),
            ("Rede", self._display_value(network_name, fallback="Não disponível")),
            ("Endereço", self._display_value(network_address, fallback="Não disponível")),
            ("Uptime", self._format_uptime(system.get("uptime"))),
        ]
        self._update_rows_by_frames(self.system_row_frames, system_rows)

    def _update_rows_by_frames(self, row_frames, rows_data):
        """Update row data using pre-stored frame references"""
        for row_index in range(len(row_frames)):
            row_frame = row_frames[row_index]
            row_labels = [w for w in row_frame.winfo_children() if isinstance(w, tk.Label)]
            if len(row_labels) < 2:
                continue
            if row_index < len(rows_data):
                label_text, value_text = rows_data[row_index]
                if self._is_unavailable_value(value_text) or self._is_unavailable_value(label_text):
                    self._set_block_visibility(row_frame, False, manager="pack")
                    continue
                self._set_block_visibility(row_frame, True, manager="pack")
                row_labels[0].config(text=label_text)
                row_labels[1].config(text=str(value_text))
            else:
                self._set_block_visibility(row_frame, False, manager="pack")
                row_labels[0].config(text="")
                row_labels[1].config(text="")

    def _update_card_rows(self, card_frame, rows_data):
        """Deprecated: use _update_rows_by_frames instead"""
        pass

    def _ensure_dashboard_structure(self):
        if self._dashboard_structure_ready:
            return
        self._dashboard_structure_ready = True
        self._create_dashboard_card_state(self.cpu_card.inner_frame, "cpu", "CPU", "#2563EB")
        self._create_dashboard_card_state(self.ram_card.inner_frame, "ram", "RAM", "#7c3aed")
        self._create_dashboard_card_state(self.storage_card.inner_frame, "ssd", "SSD", "#10b981")
        self._create_dashboard_card_state(self.system_card.inner_frame, "system", "Sistema", "#ea580c")

    def _create_dashboard_card_state(self, parent, key, title, accent):
        state = {
            "title": title,
            "accent": accent,
            "metric_widgets": [],
            "row_widgets": [],
            "status_widgets": [],
        }
        state["header"] = tk.Label(parent, text=title, bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(13, min_size=12, max_size=16, weight="bold"), wraplength=320, justify="left")
        state["header"].pack(anchor="w")
        state["main_value"] = tk.Label(parent, text="Não disponível", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(12, min_size=11, max_size=15, weight="bold"), wraplength=320, justify="left")
        state["main_value"].pack(anchor="w", pady=(6, 6))

        metrics_frame = tk.Frame(parent, bg=THEME["card_bg"])
        metrics_frame.pack(fill="x", pady=(0, 4))
        rows_frame = tk.Frame(parent, bg=THEME["card_bg"])
        rows_frame.pack(fill="x", pady=(0, 4))
        progress_frame = tk.Frame(parent, bg=THEME["card_bg"])
        progress_frame.pack(fill="x", pady=(10, 0))
        state["metrics_frame"] = metrics_frame
        state["rows_frame"] = rows_frame
        state["progress_frame"] = progress_frame

        if key == "cpu":
            for label_text, color, suffix in (("Temperatura", self._temp_color(0.0), "°C"), ("Uso", self._status_color(0.0, [50, 75, 90]), "%")):
                metric_frame = tk.Frame(metrics_frame, bg=THEME["card_bg"])
                metric_frame.pack(fill="x", pady=(4, 4))
                metric_label = tk.Label(metric_frame, text=label_text, bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12), wraplength=120)
                metric_label.pack(anchor="w")
                bar = ProgressBar(metric_frame, width=280, value=0.0, color=color)
                bar.pack(fill="x", pady=(4, 2))
                value_label = tk.Label(metric_frame, text="0%", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=140)
                value_label.pack(anchor="e")
                state["metric_widgets"].append((metric_label, bar, value_label))
        elif key == "ram":
            metric_frame = tk.Frame(metrics_frame, bg=THEME["card_bg"])
            metric_frame.pack(fill="x", pady=(4, 4))
            metric_label = tk.Label(metric_frame, text="Uso", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12), wraplength=120)
            metric_label.pack(anchor="w")
            bar = ProgressBar(metric_frame, width=280, value=0.0, color=self._status_color(0.0, [60, 80, 90]))
            bar.pack(fill="x", pady=(4, 2))
            value_label = tk.Label(metric_frame, text="0%", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=140)
            value_label.pack(anchor="e")
            state["metric_widgets"].append((metric_label, bar, value_label))
        elif key == "ssd":
            for label_text, color, suffix in (("Ocupação", self._status_color(0.0, [70, 85, 95]), "%"), ("Temperatura", self._temp_color(0.0), "°C")):
                metric_frame = tk.Frame(metrics_frame, bg=THEME["card_bg"])
                metric_frame.pack(fill="x", pady=(4, 4))
                metric_label = tk.Label(metric_frame, text=label_text, bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12), wraplength=120)
                metric_label.pack(anchor="w")
                bar = ProgressBar(metric_frame, width=280, value=0.0, color=color)
                bar.pack(fill="x", pady=(4, 2))
                value_label = tk.Label(metric_frame, text="0%", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=140)
                value_label.pack(anchor="e")
                state["metric_widgets"].append((metric_label, bar, value_label))
            health_frame = tk.Frame(metrics_frame, bg=THEME["card_bg"])
            health_frame.pack(fill="x", pady=(4, 4))
            tk.Label(health_frame, text="Saúde", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12), wraplength=120).pack(anchor="w")
            health_label = tk.Label(health_frame, text="Indisponível", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=180)
            health_label.pack(anchor="w", pady=(2, 0))
            state["status_widgets"].append(health_label)
        elif key == "system":
            status_frame = tk.Frame(metrics_frame, bg=THEME["card_bg"])
            status_frame.pack(fill="x", pady=(4, 4))
            for text in ("Windows Atualizado", "Status geral"):
                pill = tk.Label(status_frame, text=f"🟢 {text}", bg=THEME["card_bg"], fg=accent, font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=220, justify="left")
                pill.pack(anchor="w", pady=2)
                state["status_widgets"].append(pill)

        for _ in range(5):
            row = tk.Frame(rows_frame, bg=THEME["card_bg"])
            row.pack(fill="x", pady=4)
            label = tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12), wraplength=160, justify="left")
            label.pack(side="left")
            value = tk.Label(row, text="", bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=220, justify="right")
            value.pack(side="right")
            state["row_widgets"].append((label, value))

        state["progress"] = ProgressBar(progress_frame, width=360, value=0.0, color=accent)
        state["progress"].pack(fill="x")
        self.dashboard_widget_states[key] = state
        return state

    def _update_dashboard_card_state(self, key, parent, title, value, rows, percentage, accent, temperature=None, usage=None, health=None):
        state = self.dashboard_widget_states.get(key)
        if state is None:
            state = self._create_dashboard_card_state(parent, key, title, accent)
        state["header"].config(text=title)
        state["main_value"].config(text=value)
        if key == "cpu":
            if state["metric_widgets"]:
                self._update_metric_widget(state["metric_widgets"][0], "Temperatura", temperature, self._temp_color(temperature if temperature is not None else 0.0), "°C")
            if len(state["metric_widgets"]) > 1:
                self._update_metric_widget(state["metric_widgets"][1], "Uso", usage, self._status_color(usage if usage is not None else 0.0, [50, 75, 90]), "%")
        elif key == "ram":
            if state["metric_widgets"]:
                self._update_metric_widget(state["metric_widgets"][0], "Uso", usage, self._status_color(usage if usage is not None else 0.0, [60, 80, 90]), "%")
        elif key == "ssd":
            if state["metric_widgets"]:
                self._update_metric_widget(state["metric_widgets"][0], "Ocupação", usage, self._status_color(usage if usage is not None else 0.0, [70, 85, 95]), "%")
            if len(state["metric_widgets"]) > 1:
                self._update_metric_widget(state["metric_widgets"][1], "Temperatura", temperature, self._temp_color(temperature if temperature is not None else 0.0), "°C")
            if state["status_widgets"]:
                health_value = float(health) if health is not None else 100.0
                state["status_widgets"][0].config(text=self._health_label(health_value), fg=self._status_color(health_value, [95, 80, 60]))
        elif key == "system":
            for index, pill in enumerate(state["status_widgets"]):
                text = "Windows Atualizado" if index == 0 else "Status geral"
                pill.config(text=f"🟢 {text}" if index == 0 else f"🟡 {text}", fg=accent)
        for row_widget, (label_text, value_text) in zip(state["row_widgets"], rows):
            row_widget[0].config(text=label_text)
            row_widget[1].config(text=str(value_text))
        if state.get("progress") and state["progress"].winfo_exists():
            state["progress"].set_value(percentage if percentage is not None else 0.0)

    def _update_metric_widget(self, metric_widget, label, value, color, suffix):
        label_widget, bar, value_label = metric_widget
        label_widget.config(text=label)
        if value is None:
            bar.set_value(0.0)
            value_label.config(text=f"N/A{suffix}")
        else:
            numeric_value = float(value) if isinstance(value, (int, float)) else self._extract_percent(value)
            bar.set_value(numeric_value)
            value_label.config(text=f"{numeric_value:.0f}{suffix}")
            if hasattr(bar, "color"):
                bar.color = color

    def _render_quick_status(self, cpu, ram, disk, system):
        cpu_temp_value = self._coerce_number(cpu.get("temperature"))
        cpu_usage_value = self._extract_percent(cpu.get("usage"))
        ram_usage_value = self._extract_percent(ram.get("percent"))
        disk_usage_value = self._extract_disk_percent(disk)
        disk_health_value = self._extract_percent(disk.get("smart_health")) if disk.get("smart_health") is not None else 100.0
        disk_temp_value = self._coerce_number(disk.get("temperature"))

        metrics = [
            ("🌡", f"{cpu_temp_value:.0f}°C" if cpu_temp_value is not None else "N/A", "Temperatura CPU", self._temp_color(cpu_temp_value if cpu_temp_value is not None else 0.0), cpu_temp_value if cpu_temp_value is not None else 0.0),
            ("⚙", f"{cpu_usage_value:.0f}%", "Uso CPU", self._status_color(cpu_usage_value, [50, 75, 90]), cpu_usage_value),
            ("🧠", f"{ram_usage_value:.0f}%", "Uso RAM", self._status_color(ram_usage_value, [60, 80, 90]), ram_usage_value),
            ("💾", f"{disk_temp_value:.0f}°C" if disk_temp_value is not None else "N/A", "Temperatura SSD", self._temp_color(disk_temp_value if disk_temp_value is not None else 0.0), disk_temp_value if disk_temp_value is not None else 0.0),
            ("❤️", f"{disk_health_value:.0f}%", "Saúde SSD", self._status_color(disk_health_value, [95, 80, 60]), disk_health_value),
            ("📁", f"{disk_usage_value:.0f}%", "Uso SSD", self._status_color(disk_usage_value, [70, 85, 95]), disk_usage_value),
        ]

        if not self._quick_status_ready:
            self._quick_status_ready = True
            for icon, value, label, color, fill in metrics:
                card = tk.Frame(self.quick_cards_frame, bg=THEME["card_bg"], highlightbackground=THEME["muted"], highlightthickness=1, width=140, height=80)
                card.pack(side="left", padx=(0, 8), pady=2)
                card.pack_propagate(False)
                icon_label = tk.Label(card, text=icon, bg=THEME["card_bg"], fg=color, font=self._font(13, min_size=12, max_size=16, weight="bold"), wraplength=100)
                icon_label.pack(anchor="w", padx=10, pady=(8, 0))
                value_label = tk.Label(card, text=value, bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(11, min_size=10, max_size=13, weight="bold"), wraplength=100)
                value_label.pack(anchor="w", padx=10, pady=(3, 0))
                hint_label = tk.Label(card, text=label, bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(9, min_size=8, max_size=10), wraplength=110)
                hint_label.pack(anchor="w", padx=10, pady=(2, 6))
                bar = ProgressBar(card, width=160, height=6, value=fill if fill is not None else 0.0, color=color)
                bar.pack(fill="x", padx=10, pady=(0, 8))
                self.quick_status_states.append({"icon": icon_label, "value": value_label, "label": hint_label, "bar": bar})
            return

        for state, (icon, value, label, color, fill) in zip(self.quick_status_states, metrics):
            state["icon"].config(text=icon, fg=color)
            state["value"].config(text=value)
            state["label"].config(text=label)
            state["bar"].set_value(fill if fill is not None else 0.0)

    def _render_info_page(self, data):
        self._clear_info_page()
        sections = [
            ("CPU", [
                ("Nome completo", data.get("cpu", {}).get("name", "Não disponível")),
                ("Fabricante", data.get("cpu", {}).get("manufacturer", "Não disponível")),
                ("Clock atual", data.get("cpu", {}).get("clock_current", "Não disponível")),
                ("Temperatura", data.get("cpu", {}).get("temperature", "Não disponível")),
                ("Uso", data.get("cpu", {}).get("usage", "Não disponível")),
            ]),
            ("RAM", [
                ("Total", data.get("memory", {}).get("total", "Não disponível")),
                ("Em uso", data.get("memory", {}).get("used", "Não disponível")),
                ("Livre", data.get("memory", {}).get("free", "Não disponível")),
                ("Percentual", data.get("memory", {}).get("percent", "Não disponível")),
                ("Velocidade", data.get("memory", {}).get("speed", "Não disponível")),
            ]),
            ("SSD", [
                ("Modelo", (data.get("disks", []) or [{}])[0].get("model", "Não disponível")),
                ("Capacidade", (data.get("disks", []) or [{}])[0].get("total", "Não disponível")),
                ("Uso", (data.get("disks", []) or [{}])[0].get("used", "Não disponível")),
                ("Livre", (data.get("disks", []) or [{}])[0].get("free", "Não disponível")),
                ("Temperatura", (data.get("disks", []) or [{}])[0].get("temperature", "Não disponível")),
                ("Saúde SMART", (data.get("disks", []) or [{}])[0].get("smart_health", "Não disponível")),
            ]),
            ("GPU", [
                ("Nome", data.get("gpu", {}).get("name", "Não disponível")),
                ("Uso", data.get("gpu", {}).get("usage", "Não disponível")),
                ("Temperatura", data.get("gpu", {}).get("temperature", "Não disponível")),
            ]),
            ("Sistema", [
                ("OS", data.get("system", {}).get("os_name", "Não disponível")),
                ("Versão", data.get("system", {}).get("version", "Não disponível")),
                ("Build", data.get("system", {}).get("build", "Não disponível")),
                ("Arquitetura", data.get("system", {}).get("architecture", "Não disponível")),
                ("Tempo ligado", data.get("system", {}).get("uptime", "Não disponível")),
            ]),
            ("Placa-mãe", [
                ("Fabricante", data.get("motherboard", {}).get("manufacturer", "Não disponível")),
                ("Modelo", data.get("motherboard", {}).get("model", "Não disponível")),
                ("BIOS", data.get("motherboard", {}).get("bios", "Não disponível")),
                ("Versão", data.get("motherboard", {}).get("version", "Não disponível")),
                ("Data", data.get("motherboard", {}).get("date", "Não disponível")),
            ]),
        ]

        if not hasattr(self, "info_section_states"):
            self.info_section_states = {}

        for title, rows in sections:
            state = self.info_section_states.get(title)
            if state is None:
                section = AccordionSection(self.info_inner, title)
                section.pack(fill="x", pady=8)
                state = {"section": section, "row_widgets": []}
                self.info_section_states[title] = state
            else:
                section = state["section"]
            for index, (label, value) in enumerate(rows):
                if index >= len(state["row_widgets"]):
                    row = tk.Frame(section.body, bg=THEME["card_bg"])
                    row.pack(fill="x", pady=6)
                    label_widget = tk.Label(row, text=f"{label}", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12), wraplength=140, justify="left")
                    label_widget.pack(side="left")
                    value_widget = tk.Label(row, text=str(value), bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=260, justify="right")
                    value_widget.pack(side="right")
                    state["row_widgets"].append((label_widget, value_widget))
                else:
                    row_label, row_value = state["row_widgets"][index]
                    row_label.config(text=label)
                    row_value.config(text=str(value))

    def _status_color(self, value, thresholds):
        if value is None:
            return "#6B7280"
        if value >= thresholds[0]:
            return "#16a34a"
        if value >= thresholds[1]:
            return "#f59e0b"
        if value >= thresholds[2]:
            return "#f97316"
        return "#dc2626"

    def _temp_color(self, value):
        if value is None:
            return "#6B7280"
        if value <= 50:
            return "#16a34a"
        if value <= 65:
            return "#f59e0b"
        if value <= 80:
            return "#f97316"
        return "#dc2626"

    def _health_label(self, value):
        if value is None:
            return "Indisponível"
        if value >= 95:
            return "Excelente"
        if value >= 80:
            return "Boa"
        if value >= 60:
            return "Atenção"
        return "Crítica"

    def _render_info_page(self, data):
        self._clear_info_page()
        sections = [
            ("CPU", [
                ("Nome completo", data.get("cpu", {}).get("name", "Não disponível")),
                ("Fabricante", data.get("cpu", {}).get("manufacturer", "Não disponível")),
                ("Clock atual", data.get("cpu", {}).get("clock_current", "Não disponível")),
                ("Temperatura", data.get("cpu", {}).get("temperature", "Não disponível")),
                ("Uso", data.get("cpu", {}).get("usage", "Não disponível")),
            ]),
            ("RAM", [
                ("Total", data.get("memory", {}).get("total", "Não disponível")),
                ("Em uso", data.get("memory", {}).get("used", "Não disponível")),
                ("Livre", data.get("memory", {}).get("free", "Não disponível")),
                ("Percentual", data.get("memory", {}).get("percent", "Não disponível")),
                ("Velocidade", data.get("memory", {}).get("speed", "Não disponível")),
            ]),
            ("SSD", [
                ("Modelo", (data.get("disks", []) or [{}])[0].get("model", "Não disponível")),
                ("Capacidade", (data.get("disks", []) or [{}])[0].get("total", "Não disponível")),
                ("Uso", (data.get("disks", []) or [{}])[0].get("used", "Não disponível")),
                ("Livre", (data.get("disks", []) or [{}])[0].get("free", "Não disponível")),
                ("Temperatura", (data.get("disks", []) or [{}])[0].get("temperature", "Não disponível")),
                ("Saúde SMART", (data.get("disks", []) or [{}])[0].get("smart_health", "Não disponível")),
            ]),
            ("GPU", [
                ("Nome", data.get("gpu", {}).get("name", "Não disponível")),
                ("Uso", data.get("gpu", {}).get("usage", "Não disponível")),
                ("Temperatura", data.get("gpu", {}).get("temperature", "Não disponível")),
            ]),
            ("Sistema", [
                ("OS", data.get("system", {}).get("os_name", "Não disponível")),
                ("Versão", data.get("system", {}).get("version", "Não disponível")),
                ("Build", data.get("system", {}).get("build", "Não disponível")),
                ("Arquitetura", data.get("system", {}).get("architecture", "Não disponível")),
                ("Tempo ligado", data.get("system", {}).get("uptime", "Não disponível")),
            ]),
            ("Placa-mãe", [
                ("Fabricante", data.get("motherboard", {}).get("manufacturer", "Não disponível")),
                ("Modelo", data.get("motherboard", {}).get("model", "Não disponível")),
                ("BIOS", data.get("motherboard", {}).get("bios", "Não disponível")),
                ("Versão", data.get("motherboard", {}).get("version", "Não disponível")),
                ("Data", data.get("motherboard", {}).get("date", "Não disponível")),
            ]),
        ]

        for title, rows in sections:
            section = AccordionSection(self.info_inner, title)
            section.pack(fill="x", pady=8)
            for label, value in rows:
                row = tk.Frame(section.body, bg=THEME["card_bg"])
                row.pack(fill="x", pady=6)
                tk.Label(row, text=f"{label}", bg=THEME["card_bg"], fg=THEME["text_secondary"], font=self._font(10, min_size=9, max_size=12), wraplength=140, justify="left").pack(side="left")
                tk.Label(row, text=str(value), bg=THEME["card_bg"], fg=THEME["text_primary"], font=self._font(10, min_size=9, max_size=12, weight="bold"), wraplength=260, justify="right").pack(side="right")

    def check_firewall_state(self):
        try:
            manager = FirewallManager()
            enabled = manager.get_state()
            self.firewall_output.delete("1.0", tk.END)
            self.firewall_output.insert(tk.END, f"Firewall {'ativado' if enabled else 'desativado'}\n")
        except Exception as exc:
            self.firewall_output.delete("1.0", tk.END)
            self.firewall_output.insert(tk.END, f"Erro: {exc}\n")

    def toggle_firewall(self, enable: bool):
        try:
            manager = FirewallManager()
            manager.set_state(enable)
            self.firewall_output.delete("1.0", tk.END)
            self.firewall_output.insert(tk.END, f"Operação concluída: firewall {'ativado' if enable else 'desativado'}\n")
        except Exception as exc:
            self.firewall_output.delete("1.0", tk.END)
            self.firewall_output.insert(tk.END, f"Erro: {exc}\n")

    def open_port(self):
        try:
            port = self.port_entry.get().strip()
            if not port.isdigit():
                raise ValueError("Informe uma porta numérica.")
            direction = self.firewall_port_direction.get() if hasattr(self, 'firewall_port_direction') else 'Entrada'
            manager = FirewallManager()
            manager.allow_port(int(port), direction=direction)
            self.firewall_output.insert(tk.END, f"✔ Porta {port} liberada com sucesso ({direction}).\n")
            if hasattr(self, 'firewall_filter_field') and self.firewall_filter_field.winfo_exists():
                self.firewall_filter_field.set('Porta')
            if hasattr(self, 'firewall_search') and self.firewall_search.winfo_exists():
                self.firewall_search.delete(0, tk.END)
                self.firewall_search.insert(0, port)
            self.refresh_firewall_list()
        except Exception as exc:
            self.firewall_output.insert(tk.END, f"Erro: {exc}\n")

    def _reset_firewall_filters(self):
        search_widget = self.__dict__.get('firewall_search')
        if search_widget is not None and getattr(search_widget, 'winfo_exists', lambda: False)():
            search_widget.delete(0, tk.END)
        filter_widget = self.__dict__.get('firewall_filter_field')
        if filter_widget is not None and getattr(filter_widget, 'winfo_exists', lambda: False)():
            filter_widget.set('Todos')
        protocol_widget = self.__dict__.get('protocol_filter')
        if protocol_widget is not None and getattr(protocol_widget, 'winfo_exists', lambda: False)():
            protocol_widget.set('Todos')

    def refresh_firewall_list(self):
        self.firewall_output.insert(tk.END, '🔄 Atualizando lista de conexões ativas...\n')
        if hasattr(self, 'firewall_list_refresh_button') and self.firewall_list_refresh_button.winfo_exists():
            self.firewall_list_refresh_button.configure(state='disabled')
        if hasattr(self, 'collect_button') and self.collect_button.winfo_exists():
            self.collect_button.configure(state='disabled')

        def worker():
            try:
                manager = FirewallManager()
                rows = manager.list_connections()
                self._schedule_ui_update(lambda: self._populate_firewall_table(rows))
            except Exception as exc:
                error_message = str(exc)
                self._schedule_ui_update(lambda error_message=error_message: self.firewall_output.insert(tk.END, f'Erro: {error_message}\n'))
            finally:
                def _enable_buttons():
                    if hasattr(self, 'firewall_list_refresh_button') and self.firewall_list_refresh_button.winfo_exists():
                        self.firewall_list_refresh_button.configure(state='normal')
                    if hasattr(self, 'collect_button') and self.collect_button.winfo_exists():
                        self.collect_button.configure(state='normal')
                self._schedule_ui_update(_enable_buttons)

        threading.Thread(target=worker, daemon=True).start()

    def _populate_firewall_table(self, rows):
        # rows: list of dict from list_connections()
        self._firewall_rows = rows
        for i in self.firewall_tree.get_children():
            self.firewall_tree.delete(i)
        # rebuild items and keep master list of iids so detached rows can be reattached later
        self._firewall_iids = []
        for idx, r in enumerate(rows):
            local = f"{r.get('local_addr','')}:{r.get('local_port','')}"
            remote = f"{r.get('remote_addr','')}:{r.get('remote_port','')}" if r.get('remote_addr') else ''
            proto = r.get('protocol','')
            status = r.get('status','')
            pid = r.get('pid', 0)
            proc = r.get('process','')
            item_id = f"conn_{idx}"
            self.firewall_tree.insert('', 'end', iid=item_id, values=(local, remote, proto, status, pid, proc, r.get('local_port', 0)))
            self._firewall_iids.append(item_id)
        self._apply_firewall_filter()

    def _schedule_firewall_filter(self):
        if hasattr(self, '_firewall_filter_after_id') and getattr(self, '_firewall_filter_after_id', None):
            try:
                self.after_cancel(self._firewall_filter_after_id)
            except Exception:
                pass
        try:
            self._firewall_filter_after_id = self.after(250, self._apply_firewall_filter)
        except Exception:
            self._apply_firewall_filter()

    def _apply_firewall_filter(self):
        search_widget = self.__dict__.get('firewall_search')
        term = search_widget.get().strip().lower() if search_widget is not None else ''
        filter_widget = self.__dict__.get('firewall_filter_field')
        filter_field = filter_widget.get() if filter_widget is not None else 'Todos'
        protocol_widget = self.__dict__.get('protocol_filter')
        proto = protocol_widget.get() if protocol_widget is not None else 'Todos'
        all_iids = getattr(self, '_firewall_iids', list(self.firewall_tree.get_children('')))
        for iid in all_iids:
            vals = self.firewall_tree.item(iid, 'values')
            matches_term = True
            if term:
                if filter_field == 'Porta':
                    matches_term = term in str(vals[0]).lower() or term in str(vals[1]).lower() or term in str(vals[6]).lower()
                elif filter_field == 'PID':
                    matches_term = term in str(vals[4]).lower()
                elif filter_field == 'Processo':
                    matches_term = term in str(vals[5]).lower()
                elif filter_field == 'Protocolo':
                    matches_term = term in str(vals[2]).lower()
                elif filter_field == 'Endereço':
                    matches_term = term in str(vals[0]).lower() or term in str(vals[1]).lower()
                else:
                    combined = ' '.join(str(v) for v in vals).lower()
                    matches_term = term in combined
            matches_proto = (proto == 'Todos') or (proto.lower() in str(vals[2]).lower())
            if matches_term and matches_proto:
                self.firewall_tree.reattach(iid, '', 'end')
            else:
                self.firewall_tree.detach(iid)

    def _action_allow_selected(self):
        sel = self.firewall_tree.selection()
        if not sel:
            self.firewall_output.insert(tk.END, 'Selecione uma conexão primeiro.\n')
            return
        iid = sel[0]
        port = int(self.firewall_tree.set(iid, 'local_port') or 0)
        if port <= 0:
            self.firewall_output.insert(tk.END, 'Porta inválida para a seleção.\n')
            return

        def worker():
            try:
                manager = FirewallManager()
                manager.allow_port(port)
                self._schedule_ui_update(lambda: self.firewall_output.insert(tk.END, f'✔ Porta {port} liberada.\n'))
                self._schedule_ui_update(self._reset_firewall_filters)
                self._schedule_ui_update(self.refresh_firewall_list)
            except Exception as exc:
                error_message = str(exc)
                self._schedule_ui_update(lambda error_message=error_message: self.firewall_output.insert(tk.END, f'Erro: {error_message}\n'))

        threading.Thread(target=worker, daemon=True).start()

    def _action_block_selected(self):
        sel = self.firewall_tree.selection()
        if not sel:
            self.firewall_output.insert(tk.END, 'Selecione uma conexão primeiro.\n')
            return
        iid = sel[0]
        port = int(self.firewall_tree.set(iid, 'local_port') or 0)
        if port <= 0:
            self.firewall_output.insert(tk.END, 'Porta inválida para a seleção.\n')
            return

        def worker():
            try:
                manager = FirewallManager()
                manager.block_port(port)
                self._schedule_ui_update(lambda: self.firewall_output.insert(tk.END, f'✔ Porta {port} bloqueada.\n'))
                self._schedule_ui_update(self._reset_firewall_filters)
                self._schedule_ui_update(self.refresh_firewall_list)
            except Exception as exc:
                error_message = str(exc)
                self._schedule_ui_update(lambda error_message=error_message: self.firewall_output.insert(tk.END, f'Erro: {error_message}\n'))

        threading.Thread(target=worker, daemon=True).start()

    def _action_remove_selected(self):
        sel = self.firewall_tree.selection()
        if not sel:
            self.firewall_output.insert(tk.END, 'Selecione uma conexão primeiro.\n')
            return
        iid = sel[0]
        port = int(self.firewall_tree.set(iid, 'local_port') or 0)
        if port <= 0:
            self.firewall_output.insert(tk.END, 'Porta inválida para a seleção.\n')
            return

        def worker():
            try:
                manager = FirewallManager()
                manager.remove_rule_by_port(port)
                self._schedule_ui_update(lambda: self.firewall_output.insert(tk.END, f'✔ Regras associadas à porta {port} removidas.\n'))
                self._schedule_ui_update(self._reset_firewall_filters)
                self._schedule_ui_update(self.refresh_firewall_list)
            except Exception as exc:
                error_message = str(exc)
                self._schedule_ui_update(lambda error_message=error_message: self.firewall_output.insert(tk.END, f'Erro: {error_message}\n'))

        threading.Thread(target=worker, daemon=True).start()

    def run_cleanup(self):
        if getattr(self, '_maintenance_running', False):
            return
        self._maintenance_running = True
        self._set_cleanup_buttons_state(False)
        self._reset_cleanup_ui()
        self._append_cleanup_log("Iniciando manutenção...")
        selected_ids = [item_id for item_id, var in self.cleanup_action_vars.items() if var.get()]

        def worker():
            try:
                initial_payload = self.data or self._collect_hardware_payload(force=True)
                self._schedule_ui_update(lambda: self._append_cleanup_log("Coletando dados iniciais..."))
                self._schedule_ui_update(lambda: self._update_cleanup_step("Coletando informações", "running"))

                def progress(step_name, status, message, percent):
                    self._schedule_ui_update(lambda step_name=step_name, status=status, message=message, percent=percent: self._handle_cleanup_progress(step_name, status, message, percent))

                result = self.maintenance_coordinator.run_maintenance(
                    selected_ids=selected_ids,
                    initial_payload=initial_payload,
                    settings=self._report_settings,
                    progress_callback=progress,
                    selected_programs=self.selected_programs_for_report,
                )
                self._schedule_ui_update(lambda result=result: self._finalize_cleanup(result))
            except Exception as exc:
                self._schedule_ui_update(lambda exc=exc: self._finalize_cleanup({"error": str(exc)}))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_cleanup_progress(self, step_name: str, status: str, message: str, percent: int):
        if message:
            self._append_cleanup_log(message)
        self._update_cleanup_step(step_name, status)
        self._update_cleanup_progress(percent)

    def _finalize_cleanup(self, result: dict):
        self._maintenance_running = False
        self._set_cleanup_buttons_state(True)
        self._update_cleanup_step("Concluído", "done")
        self._update_cleanup_progress(100)
        if result.get("error"):
            self._append_cleanup_log(f"Erro: {result['error']}")
            self._update_cleanup_step("Concluído", "error")
            return
        if result.get("cleanup_results"):
            self._apply_cleanup_results(result.get("cleanup_results"))
        report_path = result.get("report_path")
        if report_path:
            self._append_cleanup_log(f"Relatório salvo em {report_path}")
        if result.get("sent"):
            self._append_cleanup_log("Relatório enviado com sucesso.")
        else:
            self._append_cleanup_log("Relatório salvo localmente. O envio depende da configuração de e-mail.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
