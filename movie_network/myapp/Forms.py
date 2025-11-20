from .models import *
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm

class SignUpForm(UserCreationForm):
    email = forms.EmailField()
    class Meta: 
        model = User
        fields = ['username', 'email','password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered")
        return email
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
       
        
        if commit:
            user.save()
        return user
    
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        label='',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Password'
        })
    )

class PostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ['content', 'spoiler']
        widgets = {
            'content':forms.Textarea(attrs={
                'class':'form-control'
            }),
            'spoiler':forms.RadioSelect(attrs={
                'class':'form-check-input'
            })
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Type your message here...'
            })
        }

class Top5ShowsForm(forms.Form):
    show1 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #1'
        })
    )
    show2 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #2'
        })
    )
    show3 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #3'
        })
    )
    show4 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #4'
        })
    )
    show5 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #5'
        })
    )

class Top5MoviesForm(forms.Form):
    movie1 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #1'
        })
    )
    movie2 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #2'
        })
    )
    movie3 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #3'
        })
    )
    movie4 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #4'
        })
    )
    movie5 = forms.CharField(
        required=False,
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':'Rank #5'
        })
    )

class PickOfTheWeekForm(forms.Form):    #check if it is show or movie in view
    pick = forms.CharField(
        widget= forms.TextInput(attrs={
            'class':'form-control',
            'placeholder':"Your Pick of the Week..."
        })
    )
    
