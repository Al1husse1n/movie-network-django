import json
from unittest.mock import MagicMock, patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import Client

from movie_network.asgi import application
from myapp.models import Message, Review
from myapp.tests.factories import (
    CommunityFactory,
    MovieFactory,
    ReviewFactory,
    ShowFactory,
    UserFactory,
)
from myapp.utils_broadcast import broadcast_to_group


@pytest.mark.django_db
class TestBroadcastSignals:
    def test_review_created_broadcasts_to_followers(self):
        author = UserFactory()
        follower1 = UserFactory()
        follower2 = UserFactory()
        author.followers.add(follower1, follower2)

        movie = MovieFactory(title="Inception")

        with patch("myapp.signals.broadcast_to_group") as mock_broadcast:
            review = Review.objects.create(
                user=author,
                movie=movie,
                rating=9.0,
                body="Masterpiece!",
            )

            assert mock_broadcast.call_count == 2
            expected_payload = {
                "type": "notify",
                "payload": {
                    "kind": "review_created",
                    "actor": author.username,
                    "movie_title": "Inception",
                    "review_id": review.id,
                },
            }
            mock_broadcast.assert_any_call(f"notifications_user_{follower1.id}", expected_payload)
            mock_broadcast.assert_any_call(f"notifications_user_{follower2.id}", expected_payload)

    def test_review_created_for_show_broadcasts_to_followers(self):
        author = UserFactory()
        follower = UserFactory()
        author.followers.add(follower)

        show = ShowFactory(name="Breaking Bad")

        with patch("myapp.signals.broadcast_to_group") as mock_broadcast:
            review = Review.objects.create(
                user=author,
                show=show,
                rating=9.5,
                body="Greatest show ever!",
            )

            assert mock_broadcast.call_count == 1
            mock_broadcast.assert_called_once_with(
                f"notifications_user_{follower.id}",
                {
                    "type": "notify",
                    "payload": {
                        "kind": "review_created",
                        "actor": author.username,
                        "movie_title": "Breaking Bad",
                        "review_id": review.id,
                    },
                },
            )

    def test_review_updated_does_not_broadcast(self):
        author = UserFactory()
        follower = UserFactory()
        author.followers.add(follower)
        movie = MovieFactory()

        review = ReviewFactory(user=author, movie=movie)

        with patch("myapp.signals.broadcast_to_group") as mock_broadcast:
            review.body = "Updated review content"
            review.save()
            mock_broadcast.assert_not_called()

    def test_message_created_broadcasts_to_receiver(self):
        sender = UserFactory()
        receiver = UserFactory()
        with patch("myapp.signals.broadcast_to_group") as mock_broadcast:
            msg = Message.objects.create(
                sender=sender,
                receiver=receiver,
                content="Hello there! This is a test message for websocket broadcast notifications.",
            )

            assert mock_broadcast.call_count == 1
            mock_broadcast.assert_called_once_with(
                f"notifications_user_{receiver.id}",
                {
                    "type": "notify",
                    "payload": {
                        "kind": "new_message",
                        "actor": sender.username,
                        "preview": "Hello there! This is a test message for websocket broadcast notifications.",
                        "message_id": msg.id,
                    },
                },
            )

    def test_message_updated_does_not_broadcast(self):
        sender = UserFactory()
        receiver = UserFactory()
        msg = Message.objects.create(sender=sender, receiver=receiver, content="Hello")

        with patch("myapp.signals.broadcast_to_group") as mock_broadcast:
            msg.content = "Changed message"
            msg.save()
            mock_broadcast.assert_not_called()

    def test_review_without_user_does_not_broadcast(self):
        from myapp.signals import on_review_created

        instance = MagicMock()
        instance.user = None
        with patch("myapp.signals.broadcast_to_group") as mock_broadcast:
            on_review_created(sender=Review, instance=instance, created=True)
            mock_broadcast.assert_not_called()

    def test_message_without_receiver_does_not_broadcast(self):
        from myapp.signals import on_message_created

        instance = MagicMock()
        instance.receiver_id = None
        with patch("myapp.signals.broadcast_to_group") as mock_broadcast:
            on_message_created(sender=Message, instance=instance, created=True)
            mock_broadcast.assert_not_called()


class TestBroadcastHelper:
    def test_broadcast_to_group_swallows_channel_layer_exceptions(self):
        mock_layer = MagicMock()
        mock_layer.group_send = MagicMock(side_effect=RuntimeError("Channel layer is down!"))

        with patch("myapp.utils_broadcast.get_channel_layer", return_value=mock_layer):
            with patch(
                "myapp.utils_broadcast.async_to_sync", side_effect=RuntimeError("Async error")
            ):
                # Should log a warning and return cleanly without raising
                broadcast_to_group("community_1", {"type": "feed_event", "payload": {}})

    def test_broadcast_to_group_handles_none_channel_layer(self):
        with patch("myapp.utils_broadcast.get_channel_layer", return_value=None):
            # Should return cleanly without error
            broadcast_to_group("community_1", {"type": "feed_event", "payload": {}})


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestEndToEndBroadcast:
    async def test_compose_post_broadcasts_to_websocket_subscriber(self):
        """End-to-end: POST /compose/ broadcasts 'post_created' event to connected websocket subscriber."""

        @database_sync_to_async
        def setup_data():
            user = UserFactory()
            community = CommunityFactory(admin=user)
            return user, community

        user, community = await setup_data()

        communicator = WebsocketCommunicator(
            application,
            f"/ws/community/{community.id}/",
        )
        connected, _ = await communicator.connect()
        assert connected is True

        @database_sync_to_async
        def post_compose():
            client = Client()
            client.force_login(user)
            return client.post(
                "/compose/",
                data=json.dumps(
                    {
                        "content": "Live real-time feed test post!",
                        "communityId": community.id,
                        "spoiler": False,
                    }
                ),
                content_type="application/json",
            )

        response = await post_compose()
        assert response.status_code == 201

        message = await communicator.receive_json_from(timeout=3)
        assert message["type"] == "post_created"
        assert message["payload"]["content"] == "Live real-time feed test post!"
        assert message["payload"]["poster_username"] == user.username
        assert message["payload"]["community_id"] == community.id
        assert "post_time" in message["payload"]
        assert "post_id" in message["payload"]

        await communicator.disconnect()
