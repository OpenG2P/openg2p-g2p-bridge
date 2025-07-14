from ..implementations.novu_notifier import NovuNotifier
from ..interface.notification_interface import NotificationInterface

class NotificationFactory:
    @staticmethod
    def get_notifier() -> NotificationInterface:
        return NovuNotifier() 