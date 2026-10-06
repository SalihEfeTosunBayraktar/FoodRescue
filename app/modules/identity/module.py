from app.core.registry import ModuleSpec
from app.modules.identity.router import admin_router, auth_router

# Modülün kartviziti. app/main.py yalnızca bunu okur; modülün içini bilmez.
SPEC = ModuleSpec(name="identity", routers=(auth_router, admin_router))
