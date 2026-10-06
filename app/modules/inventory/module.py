from app.core.registry import ModuleSpec
from app.modules.inventory import service, subscribers
from app.modules.inventory.router import router

SPEC = ModuleSpec(name="inventory", routers=(router,), subscribe=subscribers.subscribe, on_tick=service.expire_due)
