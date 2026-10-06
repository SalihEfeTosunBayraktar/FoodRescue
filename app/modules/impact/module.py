from app.core.registry import ModuleSpec
from app.modules.impact import subscribers
from app.modules.impact.router import admin_router, complaint_router, public_router

SPEC = ModuleSpec(
    name="impact", routers=(public_router, complaint_router, admin_router), subscribe=subscribers.subscribe
)
