# Construirea programului Windows: pyinstaller testify.spec  (vezi .github/workflows/windows-exe.yml)
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hidden = collect_submodules("uvicorn") + collect_submodules("app") + ["multipart", "python_multipart"]
datas = [
    ("app/static", "app/static"),
    ("app/fiscal", "app/fiscal"),
    ("app/fonts", "app/fonts"),
    ("sample_data", "sample_data"),
] + collect_data_files("reportlab") + collect_data_files("anthropic")

a = Analysis(["launcher.py"], pathex=["."], datas=datas, hiddenimports=hidden, excludes=["pytest", "tkinter"])
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="TestifyHardware",
    icon="app/static/icons/icon.ico" if __import__("os").path.exists("app/static/icons/icon.ico") else None,
    console=True,   # fereastra arată adresa aplicației; închiderea ei oprește aplicația
    upx=False,
)
