from django.shortcuts import render, redirect
from django.contrib.auth import login,logout
from django.contrib.auth.decorators import login_required
from .models import *
from .Forms import *
def login_view(request):
    if request.method == 'POST':
        login_form = LoginForm(request=request,data=request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            login(request,user)
            return redirect('myapp:home')
    else:
        login_form = LoginForm(request=request)

    return render(request, 'myapp/login.html', {"form":login_form})

def signUp_view(request):
    if request.method == "POST":
        signup_form = SignUpForm(request.POST)
        if signup_form.is_valid():
            user = signup_form.save()
            login(request, user)
            return redirect('myapp:home')
    else:
        signup_form = SignUpForm()
    return render(request, 'myapp/signup.html', {"form":signup_form})

@login_required
def home_view(request):
    current_user = request.user
    communities = current_user.communities.all()
    if request.method == "POST":
         if request.POST.get("submit") == "post":
             content = request.POST.get("compose-post")
             post = CommunityPost.objects.create(
                 poster = current_user,
                 content = content,
                 community = Community.objects.get(name="5 star")
             )
         elif request.POST.get("submit") == "select-community":
            community_id = request.POST.get("community")
            community = Community.objects.get(id=community_id)  
            posts = community.posts.all()
            return render(request,'myapp/home.html',{"communities":communities, "posts":posts})
    return render(request,'myapp/home.html',{"communities":communities})

def logout_view(request):
    logout(request)
    return redirect('myapp:login')
