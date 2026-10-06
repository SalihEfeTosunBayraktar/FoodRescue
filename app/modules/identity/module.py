from app.core.registry import ModuleSpec
from app.modules.identity.router import admin_router, auth_router

SPEC = ModuleSpec(name="identity", routers=(auth_router, admin_router))
