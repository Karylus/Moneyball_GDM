import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_management.migracion_db import run_migration

if __name__ == "__main__":
    print("Empezando la migración desde CSV a MongoDB...")
    success = run_migration()
    
    if success:
        print("CSV importado a MongoDB exitosamente!")
    else:
        print("Migración fallida.")