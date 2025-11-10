from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import *
from .Forms import *
def login_view(request):
    if request.method == 'POST':
        login_form = LoginForm(request,data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            login(request,user)
            return redirect('home')
    else:
        login_form = LoginForm(request)

    return render(request, 'myapp/login.html', {"form":login_form})

def signUp_view(request):
    if request.method == "POST":
        signup_form = SignUpForm(request.POST)
        if signup_form.is_valid():
            user = signup_form.save()
            login(request, user)
            return redirect('home')
    else:
        signup_form = SignUpForm()
    return render(request, 'myapp/signup.html', {"form":signup_form})
