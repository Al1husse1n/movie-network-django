import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast_to_group(group_name, event):
    """Fire-and-forget broadcast. Logs failures but never raises.

    event must be a dict like {"type": "feed_event", "event_type": "...", "payload": {...}}
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(group_name, event)
    except Exception as exc:
        logger.warning("Broadcast to %s failed: %s", group_name, exc)
