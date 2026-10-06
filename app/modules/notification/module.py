from app.core.registry import ModuleSpec
from app.modules.notification import subscribers
from app.modules.notification.router import router

# Bu modülün yalnızca olay dinleyicisi (subscribe) ve router'ı var; zamanlı işi yok.
SPEC = ModuleSpec(name="notification", routers=(router,), subscribe=subscribers.subscribe)
