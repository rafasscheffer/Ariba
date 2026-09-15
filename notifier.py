import logging

log = logging.getLogger(__name__)


def notify(title, message):
    try:
        from winotify import Notification

        Notification(
            app_id="Brasmo - Monitor Ariba",
            title=title,
            msg=message,
            duration="long",
        ).show()
        return True
    except Exception as exc:
        log.warning("Falha na notificacao Windows: %s", exc)
        return False
