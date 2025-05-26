import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.gui.app import FootballAnalysisApp

if __name__ == "__main__":
    app = FootballAnalysisApp()
    app.mainloop()