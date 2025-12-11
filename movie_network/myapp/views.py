from django.shortcuts import render, redirect
from django.contrib.auth import login,logout
from django.contrib.auth.decorators import login_required
from .models import *
from .Forms import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

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

def logout_view(request):
    logout(request)
    return redirect('myapp:login')

@login_required
def home_view(request):
    current_user = request.user
    communities = current_user.communities.all()
    return render(request,'myapp/home.html',{"communities":communities})

@csrf_exempt
@login_required
def get_community(request,communityId):
    try:
        community = Community.objects.get(pk=communityId)
        if request.method == "GET":
            posts = community.posts.all()
            data = {f"p{post.id}":post.serialize() for post in posts}
            return JsonResponse(data)
    except Community.DoesNotExist:
        return JsonResponse({"error": "Community not found."}, status=404)
    except Exception as e:      
        return JsonResponse({"error": str(e)}, status=500)
    
@csrf_exempt
@login_required
def compose_post(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    try:
        data = json.loads(request.body)
        current_user = request.user
        community = Community.objects.get(pk=data.get("communityId"))
        CommunityPost.objects.create(
            poster=current_user,
            content=data.get('content'),
            community=community,
            spoiler = bool(data.get('spoiler'))
        )
        return JsonResponse({"message":f"You posted on {community.name}"}, status=201)
    except Exception as e:
        return JsonResponse({"error":str(e)}, status=500)




