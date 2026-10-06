from app.core.registry import ModuleSpec
from app.modules.reservation import service, subscribers
from app.modules.reservation.router import router

SPEC = ModuleSpec(name="reservation", routers=(router,), subscribe=subscribers.subscribe, on_tick=service.expire_due)
