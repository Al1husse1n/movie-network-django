from unittest.mock import AsyncMock, patch

import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import Client

from movie_network.asgi import application
from myapp.consumers import _check_community_exists
from myapp.routing import websocket_urlpatterns
from myapp.tests.factories import CommunityFactory, UserFactory


@database_sync_to_async
def create_user_and_session():
    user = UserFactory()
    client = Client()
    client.force_login(user)
    session_key = client.cookies["sessionid"].value
    return user, session_key


@database_sync_to_async
def create_community():
    user = UserFactory()
    return CommunityFactory(admin=user)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestNotificationConsumer:
    async def test_connect_authenticated_success(self):
        user, session_key = await create_user_and_session()
        communicator = WebsocketCommunicator(
            application,
            "/ws/notifications/",
            headers=[(b"cookie", f"sessionid={session_key}".encode("latin1"))],
        )

        connected, _ = await communicator.connect()
        assert connected is True

        # Verify group membership by sending a notification through the group
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"notifications_user_{user.id}",
            {
                "type": "notify",
                "payload": {"text": "Welcome back!", "badge": 1},
            },
        )
        response = await communicator.receive_json_from(timeout=2)
        assert response == {
            "type": "notification",
            "payload": {"text": "Welcome back!", "badge": 1},
        }

        await communicator.disconnect()

    async def test_connect_unauthenticated_rejected(self):
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        connected, close_code = await communicator.connect()

        assert connected is False
        assert close_code == 4001
        await communicator.disconnect()

    async def test_group_send_receives_notification(self):
        user, session_key = await create_user_and_session()
        communicator = WebsocketCommunicator(
            application,
            "/ws/notifications/",
            headers=[(b"cookie", f"sessionid={session_key}".encode("latin1"))],
        )

        connected, _ = await communicator.connect()
        assert connected is True

        channel_layer = get_channel_layer()
        notification_data = {
            "title": "New Review",
            "actor": "cinephile99",
            "unread_count": 5,
        }
        await channel_layer.group_send(
            f"notifications_user_{user.id}",
            {
                "type": "notification",
                "payload": notification_data,
            },
        )

        response = await communicator.receive_json_from(timeout=2)
        assert response["type"] == "notification"
        assert response["payload"] == notification_data

        # Sending message from client is a no-op
        await communicator.send_json_to({"action": "ping"})
        assert await communicator.receive_nothing() is True

        await communicator.disconnect()

    async def test_connect_exception_handling(self):
        _, session_key = await create_user_and_session()
        communicator = WebsocketCommunicator(
            application,
            "/ws/notifications/",
            headers=[(b"cookie", f"sessionid={session_key}".encode("latin1"))],
        )

        channel_layer = get_channel_layer()
        with patch.object(
            channel_layer,
            "group_add",
            new=AsyncMock(side_effect=RuntimeError("Channel layer boom")),
        ):
            connected, _ = await communicator.connect()
            assert connected is False

        await communicator.disconnect()

    async def test_disconnect_exception_handling(self):
        _, session_key = await create_user_and_session()
        communicator = WebsocketCommunicator(
            application,
            "/ws/notifications/",
            headers=[(b"cookie", f"sessionid={session_key}".encode("latin1"))],
        )

        connected, _ = await communicator.connect()
        assert connected is True

        channel_layer = get_channel_layer()
        with patch.object(
            channel_layer,
            "group_discard",
            new=AsyncMock(side_effect=RuntimeError("Discard boom")),
        ):
            # Disconnect should not raise an unhandled exception
            await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestCommunityFeedConsumer:
    async def test_connect_valid_community_accepted(self):
        community = await create_community()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/community/{community.id}/",
        )

        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    async def test_connect_non_existent_community_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            "/ws/community/999999/",
        )

        connected, close_code = await communicator.connect()
        assert connected is False
        assert close_code == 4004
        await communicator.disconnect()

    async def test_group_send_receives_feed_event(self):
        community = await create_community()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/community/{community.id}/",
        )

        connected, _ = await communicator.connect()
        assert connected is True

        channel_layer = get_channel_layer()
        event_payload = {
            "post_id": 42,
            "title": "Thoughts on Inception",
            "author": "nolan_fan",
        }
        await channel_layer.group_send(
            f"community_{community.id}",
            {
                "type": "feed_event",
                "event_type": "post_created",
                "payload": event_payload,
            },
        )

        response = await communicator.receive_json_from(timeout=2)
        assert response == {
            "type": "post_created",
            "payload": event_payload,
        }

        # Also test with post_deleted
        await channel_layer.group_send(
            f"community_{community.id}",
            {
                "type": "feed_event",
                "event_type": "post_deleted",
                "payload": {"post_id": 42},
            },
        )
        response_deleted = await communicator.receive_json_from(timeout=2)
        assert response_deleted == {
            "type": "post_deleted",
            "payload": {"post_id": 42},
        }

        # Client receive is a no-op
        await communicator.send_json_to({"action": "new_post"})
        assert await communicator.receive_nothing() is True

        await communicator.disconnect()

    async def test_connect_exception_handling(self):
        community = await create_community()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/community/{community.id}/",
        )

        channel_layer = get_channel_layer()
        with patch.object(
            channel_layer,
            "group_add",
            new=AsyncMock(side_effect=RuntimeError("Channel layer boom")),
        ):
            connected, _ = await communicator.connect()
            assert connected is False

        await communicator.disconnect()

    async def test_disconnect_exception_handling(self):
        community = await create_community()
        communicator = WebsocketCommunicator(
            application,
            f"/ws/community/{community.id}/",
        )

        connected, _ = await communicator.connect()
        assert connected is True

        channel_layer = get_channel_layer()
        with patch.object(
            channel_layer,
            "group_discard",
            new=AsyncMock(side_effect=RuntimeError("Discard boom")),
        ):
            await communicator.disconnect()

    async def test_check_community_exists_helper(self):
        community = await create_community()
        assert await _check_community_exists(community.id) is True
        assert await _check_community_exists(999999) is False
        assert await _check_community_exists("invalid-pk-type") is False
        assert await _check_community_exists(None) is False


class TestWebSocketRouting:
    def test_routing_patterns_count(self):
        assert len(websocket_urlpatterns) == 2

    def test_routing_notifications_pattern(self):
        pattern = websocket_urlpatterns[0]
        match = pattern.pattern.match("ws/notifications/")
        assert match is not None
        remaining, args, kwargs = match
        assert remaining == ""
        assert kwargs == {}

    def test_routing_community_pattern(self):
        pattern = websocket_urlpatterns[1]
        match = pattern.pattern.match("ws/community/42/")
        assert match is not None
        remaining, args, kwargs = match
        assert remaining == ""
        assert kwargs == {"community_id": "42"}

    def test_routing_invalid_url_does_not_match(self):
        pattern_notif = websocket_urlpatterns[0]
        pattern_comm = websocket_urlpatterns[1]
        assert pattern_notif.pattern.match("ws/unknown/") is None
        assert pattern_comm.pattern.match("ws/community/invalid/") is None
