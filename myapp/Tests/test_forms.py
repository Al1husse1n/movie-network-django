from myapp.Forms import *
from django.test import TestCase
from django.contrib.auth import get_user_model
class SignUpFormTest(TestCase):
    def test_form_validation(self):
        form_data = {
            "username":"ali",
            'email': "alilhussein@gmail.com",
            'bio':"I love anime!!",
            'password1': 'Asdqw123qwe',
            'password2': 'Asdqw123qwe'
        }
        form = SignUpForm(data = form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, "ali")

    def test_error(self):
        form_data = {
            "username":"ali",
            'email': "alilhusseingmail.com",
            'bio':"I love anime!!",
            'password1': '123',
            'password2': '123'
        }
        form = SignUpForm(data = form_data)
        self.assertIn('password2', form.errors)  #password too short
        self.assertIn('email', form.errors)  #Enter a valid email address

    def test_clean_email(self):
        form1_data = {
            "username":"ali",
            'email': "alilhussein@gmail.com",
            'bio':"I love anime!!",
            'password1': 'Asdqw123qwe',
            'password2': 'Asdqw123qwe'
        }
        form1 = SignUpForm(data = form1_data)
        user = form1.save()
        form2_data = {
            "username":"ali",
            'email': "alilhussein@gmail.com",
            'bio':"I love anime!!",
            'password1': 'Asdqw123qwe',
            'password2': 'Asdqw123qwe'
        }
        form2 = SignUpForm(data = form2_data)
        self.assertIn("email", form2.errors)

class LoginFormTest(TestCase):
    def test_authentication(self):
        form1_data = {
            "username":"ali",
            'email': "alilhussein@gmail.com",
            'bio':"I love anime!!",
            'password1': 'Asdqw123qwe',
            'password2': 'Asdqw123qwe'
        }
        form1 = SignUpForm(data = form1_data)
        self.assertTrue(form1.is_valid())
        user = form1.save()
        
        form2_data = {
            "username":"ali",
            'password':'Asdqw123qwe'
        }
            
        request = self.client.request().wsgi_request
        form2 = LoginForm(request=request, data=form2_data)
        self.assertTrue(form2.is_valid())

class PostFormTest(TestCase):
    def test_post_validation(self):
        form_data = {
            'content':"good",
            "spoiler":False
        }
        form = PostForm(data=form_data)
        self.assertTrue(form.is_valid())

class MessageFormTest(TestCase):
    def test_message_validation(self):
        User = get_user_model()
        sender = User.objects.create_user(username="s", email="s@example.com", password="Asdqw123qwe")
        receiver = User.objects.create_user(username="r", email="r@example.com", password="Asdqw123qwe")
        sender.followers.add(receiver)

        form_data = {"content": "hello"}
        form = MessageForm(data=form_data)
        form.instance.sender = sender
        form.instance.receiver = receiver

        self.assertTrue(form.is_valid(), form.errors)





