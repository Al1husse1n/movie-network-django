from django.core.management.base import BaseCommand, CommandError

from myapp.tasks import send_user_digest


class Command(BaseCommand):
    help = "Dispatches send_user_digest task for a specific user ID."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=int,
            required=True,
            help="ID of the user to send the test digest to.",
        )

    def handle(self, *args, **options):
        user_id = options.get("user")
        if not user_id:
            raise CommandError("--user argument is required.")

        result = send_user_digest.delay(user_id)
        self.stdout.write(
            self.style.SUCCESS(
                f"Dispatched send_user_digest for user {user_id}. Task ID: {result.id}"
            )
        )
