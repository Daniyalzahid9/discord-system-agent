import ctypes
import warnings
import pyperclip

warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError

def _attach_to_default_desktop():
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

def get_clipboard_text() -> str:
    """Retrieves current text copied on laptop clipboard."""
    return pyperclip.paste()

def set_clipboard_text(text: str) -> None:
    """Sets text on laptop clipboard."""
    pyperclip.copy(text)

def focus_window_by_title(title_query: str) -> tuple[bool, str]:
    """Brings a window matching title_query to the foreground."""
    _attach_to_default_desktop()
    try:
        d = Desktop(backend="uia")
        matched = None
        for w in d.windows():
            t = w.window_text()
            if t and title_query.lower() in t.lower():
                matched = w
                break
        
        if not matched:
            d = Desktop(backend="win32")
            for w in d.windows():
                t = w.window_text()
                if t and title_query.lower() in t.lower():
                    matched = w
                    break

        if matched:
            matched.set_focus()
            return True, f"Focused window: '{matched.window_text()}'"
        return False, f"No window found matching '{title_query}'"
    except Exception as e:
        return False, f"Error focusing window: {str(e)}"

def click_native_element(query: str, window_title: str = None) -> tuple[bool, str]:
    """Finds and clicks a native Windows UI control (Button, Tab, MenuItem) by text."""
    _attach_to_default_desktop()
    try:
        d = Desktop(backend="uia")
        target_win = None
        if window_title:
            for w in d.windows():
                if w.window_text() and window_title.lower() in w.window_text().lower():
                    target_win = w
                    break
        else:
            # Use active/top window
            target_win = d.windows()[0] if d.windows() else None

        if not target_win:
            return False, "Could not determine target window."

        target_win.set_focus()
        
        # Search child elements
        controls = target_win.descendants()
        target_ctrl = None
        for c in controls:
            txt = c.window_text()
            if txt and query.lower() in txt.lower():
                target_ctrl = c
                break

        if target_ctrl:
            try:
                target_ctrl.click_input()
                return True, f"Clicked UI element: '{target_ctrl.window_text()}'"
            except Exception:
                target_ctrl.click()
                return True, f"Clicked UI element: '{target_ctrl.window_text()}'"

        return False, f"Could not find UI control matching '{query}' in window '{target_win.window_text()}'"
    except Exception as e:
        return False, f"UI Automation error: {str(e)}"

def list_window_controls(window_title: str = None, limit: int = 20) -> list[str]:
    """Lists clickable/interactive elements in a window."""
    _attach_to_default_desktop()
    elements = []
    try:
        d = Desktop(backend="uia")
        target_win = None
        for w in d.windows():
            txt = w.window_text()
            if txt and (not window_title or window_title.lower() in txt.lower()):
                target_win = w
                break

        if target_win:
            for c in target_win.descendants():
                ctrl_type = c.element_info.control_type
                name = c.window_text()
                if name and ctrl_type in ["Button", "TabItem", "MenuItem", "Hyperlink", "CheckBox", "RadioButton"]:
                    elements.append(f"[{ctrl_type}] {name}")
                if len(elements) >= limit:
                    break
    except Exception:
        pass
    return elements
