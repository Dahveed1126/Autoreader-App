import winreg
import os
import sys

CONTEXT_MENU_KEY = r"Software\Classes\*\shell\AutoreaderApp"
CONTEXT_MENU_COMMAND_KEY = CONTEXT_MENU_KEY + r"\command"
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "AutoreaderApp"


def install_context_menu(companion_exe_path: str):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Read Aloud with Autoreader")
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, companion_exe_path)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_COMMAND_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{companion_exe_path}"')


def uninstall_context_menu():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY):
            pass
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_COMMAND_KEY)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY)
    except FileNotFoundError:
        pass


def is_context_menu_installed() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY):
            return True
    except FileNotFoundError:
        return False


def install_autostart(exe_path: str):
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')


def uninstall_autostart():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, AUTOSTART_NAME)
    except FileNotFoundError:
        pass


def is_autostart_installed() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            return True
    except FileNotFoundError:
        return False
