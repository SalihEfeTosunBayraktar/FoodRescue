from app.core.registry import ModuleSpec
from app.modules.notification import subscribers
from app.modules.notification.router import router

SPEC = ModuleSpec(name="notification", routers=(router,), subscribe=subscribers.subscribe)
