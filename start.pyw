"""
Klad Macro Tool - Launcher (No Console)
.pyw uzantısı Windows'ta konsol olmadan çalıştırır
"""

import sys
import os

# Çalışma dizinini ayarla
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Ana modülü import et ve çalıştır
from klad_macro_tool import main


if __name__ == "__main__":
    main()
