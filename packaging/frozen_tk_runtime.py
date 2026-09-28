"""PyInstaller runtime: Tcl resources stay relative to the extracted bundle."""
import os
import sys
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
    os.environ['TCL_LIBRARY'] = './_tcl_data'
    os.environ['TK_LIBRARY'] = './_tk_data'
