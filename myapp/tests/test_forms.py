import pytest
from django.test import RequestFactory
from myapp.Forms import SignUpForm, LoginForm, PostForm
from myapp.models import User
from .factories import UserFactory


@pytest.mark.django_db
class TestSignUpForm:
    def test_valid_signup_creates_user_with_hashed_password(self):
        form_data = {
            "username": "new_cinephile",
            "email": "cinephile@example.com",
            "password": "SecurePassword123!",
        }
        form = SignUpForm(data=form_data)
        assert form.is_valid(), form.errors

        user = form.save()
        assert user.username == "new_cinephile"
        assert user.email == "cinephile@example.com"
        assert user.check_password("SecurePassword123!")
        assert User.objects.filter(username="new_cinephile").exists()

    def test_signup_rejects_duplicate_email(self):
        # Create an existing user with the same email
        UserFactory(username="first_user", email="shared@example.com")

        form_data = {
            "username": "second_user",
            "email": "shared@example.com",
            "password": "SecurePassword123!",
        }
        form = SignUpForm(data=form_data)
        assert not form.is_valid()
        assert "email" in form.errors
        assert "This email is already registered" in form.errors["email"]


@pytest.mark.django_db
class TestLoginForm:
    def test_valid_credentials_authenticate(self):
        # Create a user with a known password
        UserFactory(username="active_user", password="KnownPassword456!")

        request = RequestFactory().post("/login/")
        form_data = {
            "username": "active_user",
            "password": "KnownPassword456!",
        }
        form = LoginForm(request=request, data=form_data)
        assert form.is_valid(), form.errors
        authenticated_user = form.get_user()
        assert authenticated_user.username == "active_user"

    def test_invalid_credentials_rejected(self):
        UserFactory(username="valid_user", password="CorrectPassword123!")

        request = RequestFactory().post("/login/")
        form_data = {
            "username": "valid_user",
            "password": "WrongPassword999!",
        }
        form = LoginForm(request=request, data=form_data)
        assert not form.is_valid()
        assert "__all__" in form.errors


class TestPostForm:
    def test_valid_post_form(self):
        form_data = {
            "content": "A thoughtful review of the film.",
            "spoiler": False,
        }
        form = PostForm(data=form_data)
        assert form.is_valid(), form.errors
