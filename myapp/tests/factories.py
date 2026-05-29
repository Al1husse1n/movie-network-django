import factory
from factory.django import DjangoModelFactory

from myapp.models import Community, CommunityPost, Message, User, UserRating


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")
    bio = factory.Faker("sentence")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or "DefaultPass123!"
        self.set_password(raw_password)
        if create:
            self.save()


class CommunityFactory(DjangoModelFactory):
    class Meta:
        model = Community

    name = factory.Sequence(lambda n: f"Community_{n}")
    admin = factory.SubFactory(UserFactory)
    visibility = "public"


class CommunityPostFactory(DjangoModelFactory):
    class Meta:
        model = CommunityPost

    poster = factory.SubFactory(UserFactory)
    community = factory.SubFactory(CommunityFactory)
    content = factory.Faker("sentence")
    spoiler = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        community = kwargs.get("community")
        poster = kwargs.get("poster")
        if community and poster:
            if not community.members.filter(id=poster.id).exists():
                community.members.add(poster)
        return super()._create(model_class, *args, **kwargs)


class MessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    sender = factory.SubFactory(UserFactory)
    receiver = factory.SubFactory(UserFactory)
    content = factory.Faker("sentence")


class UserRatingFactory(DjangoModelFactory):
    class Meta:
        model = UserRating

    user = factory.SubFactory(UserFactory)
    movie = factory.LazyFunction(lambda: {"id": 100, "title": "Inception"})
    rating = 8.5
