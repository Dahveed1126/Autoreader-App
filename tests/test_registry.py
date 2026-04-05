from unittest.mock import patch, MagicMock, call
import winreg

def test_install_context_menu_creates_registry_keys():
    with patch("winreg.CreateKey") as mock_create, \
         patch("winreg.SetValueEx") as mock_set, \
         patch("winreg.CloseKey"):
        mock_create.return_value = MagicMock()
        from src.registry import install_context_menu
        install_context_menu("C:/path/to/autoreader_send.exe")
        assert mock_create.called
        assert mock_set.called

def test_uninstall_context_menu_deletes_key():
    with patch("winreg.DeleteKey") as mock_del, \
         patch("winreg.OpenKey") as mock_open:
        mock_open.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        from src.registry import uninstall_context_menu
        uninstall_context_menu()
