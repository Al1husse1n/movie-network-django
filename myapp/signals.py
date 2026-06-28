import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message, Review
from .utils_broadcast import broadcast_to_group

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Review)
def on_review_created(sender, instance, created, **kwargs):
    if not created:
        return
    if not getattr(instance, "user", None):
        return

    movie_title = (
        instance.movie.title if instance.movie else (instance.show.name if instance.show else "")
    )

    for follower in instance.user.followers.all():
        broadcast_to_group(
            f"notifications_user_{follower.id}",
            {
                "type": "notify",
                "payload": {
                    "kind": "review_created",
                    "actor": instance.user.username,
                    "movie_title": movie_title,
                    "review_id": instance.id,
                },
            },
        )


@receiver(post_save, sender=Message)
def on_message_created(sender, instance, created, **kwargs):
    if not created:
        return
    if not getattr(instance, "receiver_id", None):
        return

    actor = instance.sender.username if getattr(instance, "sender", None) else ""
    preview = (instance.content or "")[:80]

    broadcast_to_group(
        f"notifications_user_{instance.receiver_id}",
        {
            "type": "notify",
            "payload": {
                "kind": "new_message",
                "actor": actor,
                "preview": preview,
                "message_id": instance.id,
            },
        },
    )
