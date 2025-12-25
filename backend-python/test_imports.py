
print("Starting import test")
import os
import sys
sys.path.append(os.getcwd())
print("Path added")
try:
    from app.core.config import settings
    print("Config imported")
    from app.modules.catalog_index.catalog import CatalogIndexer
    print("CatalogIndexer imported")
    from app.modules.assistant import get_assistant_handler
    print("AssistantHandler imported")
except Exception as e:
    print(f"Error during import: {e}")
print("Import test finished")
