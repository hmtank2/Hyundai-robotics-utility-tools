from pathlib import Path
import os
import sys
base = Path(sys.base_prefix) / 'tcl'
tcl = Path(os.environ.get('TCL_LIBRARY', str(base / 'tcl8.6')))
tk = Path(os.environ.get('TK_LIBRARY', str(base / 'tk8.6')))
datas = [(str(tcl), '_tcl_data'), (str(tk), '_tk_data')]
