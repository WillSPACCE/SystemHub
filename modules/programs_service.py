import platform
from typing import Dict, List
import os

try:
    import winreg
except Exception:
    winreg = None


class InstalledProgramsService:
    @staticmethod
    def get_installed_programs() -> List[Dict[str, str]]:
        if platform.system() != "Windows" or winreg is None:
            return []

        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        programs = []
        seen = set()

        for root, path in roots:
            try:
                with winreg.OpenKey(root, path) as key:
                    for index in range(0, winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, index)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                if not display_name or not isinstance(display_name, str):
                                    continue
                                version = ""
                                try:
                                    version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                                except OSError:
                                    version = ""
                                
                                # Capturar UninstallString e InstallLocation
                                uninstall_string = ""
                                install_location = ""
                                try:
                                    uninstall_string, _ = winreg.QueryValueEx(subkey, "UninstallString")
                                except OSError:
                                    pass
                                try:
                                    install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                except OSError:
                                    pass
                                
                                identifier = (display_name.strip(), version.strip())
                                if identifier in seen:
                                    continue
                                seen.add(identifier)
                                programs.append({
                                    "name": display_name.strip(),
                                    "version": version.strip() if isinstance(version, str) else "",
                                    "uninstall_string": uninstall_string.strip() if isinstance(uninstall_string, str) else "",
                                    "install_location": install_location.strip() if isinstance(install_location, str) else "",
                                })
                        except OSError:
                            continue
            except OSError:
                continue

        programs.sort(key=lambda item: item.get("name", "").lower())
        return programs

    @staticmethod
    def uninstall_program(program_name: str, uninstall_string: str) -> bool:
        """Tenta desinstalar um programa usando a UninstallString do registro."""
        if not uninstall_string:
            return False
        
        try:
            import subprocess
            # UninstallString pode conter argumentos, ex: "C:\Program Files\App\uninstall.exe" /S
            # ou "msiexec.exe /x {GUID} /quiet"
            subprocess.Popen(uninstall_string, shell=True)
            return True
        except Exception:
            return False

    @staticmethod
    def open_install_location(install_location: str) -> bool:
        """Abre a pasta de instalação do programa no Windows Explorer."""
        if not install_location or not os.path.isdir(install_location):
            return False
        
        try:
            if os.name == 'nt':
                os.startfile(install_location)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', install_location])
            return True
        except Exception:
            return False
