import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("main_module", ROOT / "main.py")
main_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main_module)


def test_format_memory_speed_adds_mhz_suffix():
    app = object.__new__(main_module.App)

    assert app._format_memory_speed("3200") == "3200 MHz"
    assert app._format_memory_speed("3200 MHz") == "3200 MHz"
    assert app._format_memory_speed(None) == "Não disponível"
