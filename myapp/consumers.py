import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


@database_sync_to_async
def _check_community_exists(community_id):
    from myapp.models import Community

    try:
        return Community.objects.filter(pk=community_id).exists()
    except (ValueError, TypeError):
        return False


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time user-specific notifications.

    Only authenticated users are allowed to connect. Messages are pushed from
    the server via the user's dedicated channel layer group.
    """

    async def connect(self):
        try:
            user = self.scope.get("user")
            if not user or user.is_anonymous or not getattr(user, "is_authenticated", False):
                logger.info("NotificationConsumer: Unauthenticated connection rejected")
                await self.close(code=4001)
                return

            self.user = user
            self.user_group_name = f"notifications_user_{user.id}"
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name,
            )
            await self.accept()
            logger.info(
                "NotificationConsumer connected for user %s (%s)", user.id, self.channel_name
            )
        except Exception as exc:
            logger.exception("Error in NotificationConsumer connect: %s", exc)
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "user_group_name") and self.user_group_name:
                await self.channel_layer.group_discard(
                    self.user_group_name,
                    self.channel_name,
                )
        except Exception as exc:
            logger.exception("Error in NotificationConsumer disconnect: %s", exc)
        finally:
            logger.info(
                "NotificationConsumer disconnected (%s, code=%s)",
                getattr(self, "channel_name", ""),
                close_code,
            )

    async def receive_json(self, content, **kwargs):
        # Notifications are push-only from the server
        pass

    async def notify(self, event):
        """Handler for 'notify' group messages."""
        payload = event.get("payload", {})
        await self.send_json(
            {
                "type": "notification",
                "payload": payload,
            }
        )

    # Alias in case group_send uses type='notification'
    notification = notify


class CommunityFeedConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time community feed events.

    Anyone can subscribe to feed updates for an existing community (read-only).
    """

    async def connect(self):
        try:
            route_kwargs = self.scope.get("url_route", {}).get("kwargs", {})
            self.community_id = route_kwargs.get("community_id")

            if not self.community_id or not await _check_community_exists(self.community_id):
                logger.info(
                    "CommunityFeedConsumer: Community %s does not exist, rejecting",
                    self.community_id,
                )
                await self.close(code=4004)
                return

            self.community_group_name = f"community_{self.community_id}"
            await self.channel_layer.group_add(
                self.community_group_name,
                self.channel_name,
            )
            await self.accept()
            logger.info(
                "CommunityFeedConsumer connected to %s (%s)",
                self.community_group_name,
                self.channel_name,
            )
        except Exception as exc:
            logger.exception("Error in CommunityFeedConsumer connect: %s", exc)
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "community_group_name") and self.community_group_name:
                await self.channel_layer.group_discard(
                    self.community_group_name,
                    self.channel_name,
                )
        except Exception as exc:
            logger.exception("Error in CommunityFeedConsumer disconnect: %s", exc)
        finally:
            logger.info(
                "CommunityFeedConsumer disconnected (%s, code=%s)",
                getattr(self, "channel_name", ""),
                close_code,
            )

    async def receive_json(self, content, **kwargs):
        # Broadcast is read-only; mutations are handled via HTTP API / views
        pass

    async def feed_event(self, event):
        """Handler for 'feed_event' group messages."""
        event_type = (
            event.get("event_type")
            or event.get("type_")
            or event.get("action")
            or event.get("event")
            or (
                event.get("payload", {}).get("type")
                if isinstance(event.get("payload"), dict)
                else None
            )
            or "post_created"
        )
        payload = event.get("payload", {})
        await self.send_json(
            {
                "type": event_type,
                "payload": payload,
            }
        )
