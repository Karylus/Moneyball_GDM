import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.gui.app import MoneyballApp

if __name__ == "__main__":
    app = MoneyballApp()
    app.mainloop()