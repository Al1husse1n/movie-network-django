from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Community, CommunityPost, Message, User


class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ["name", "visibility"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "e.g. Film Noir Society",
                    "maxlength": 50,
                    "required": True,
                }
            ),
            "visibility": forms.Select(attrs={"class": "input"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 3:
            raise forms.ValidationError("Community name must be at least 3 characters.")
        if Community.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("A community with that name already exists.")
        return name


class SignUpForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "password"]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "username-input",
                    "placeholder": "",
                }
            ),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": ""}),
            "password": forms.PasswordInput(attrs={"class": "form-control", "placeholder": ""}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            user.set_password(raw_password)
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )


class PostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ["content", "spoiler"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-control"}),
            "spoiler": forms.RadioSelect(attrs={"class": "form-check-input"}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Type your message here...",
                }
            )
        }


class Top5ShowsForm(forms.Form):
    show1 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #1"}),
    )
    show2 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #2"}),
    )
    show3 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #3"}),
    )
    show4 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #4"}),
    )
    show5 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #5"}),
    )


class Top5MoviesForm(forms.Form):
    movie1 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #1"}),
    )
    movie2 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #2"}),
    )
    movie3 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #3"}),
    )
    movie4 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #4"}),
    )
    movie5 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Rank #5"}),
    )


class PickOfTheWeekForm(forms.Form):  # check if it is show or movie in view
    pick = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Your Pick of the Week..."}
        )
    )
