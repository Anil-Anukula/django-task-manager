from django.shortcuts import render, redirect
from .serializers import TaskSerializer
from rest_framework import viewsets, permissions, filters
from .models import Task
from django_filters.rest_framework import DjangoFilterBackend
import requests
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError
import logging
from django.urls import reverse
# Create your views here.

TOKEN_KEY = "jwt_token"
logger = logging.getLogger(__name__)

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Validate passwords match
        if password != confirm_password:
            return render(request, "tasks/register.html", {"error": "Passwords do not match"})

        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            return render(request, "tasks/register.html", {"error": "Username already taken"})
        if User.objects.filter(email=email).exists():
            return render(request, "tasks/register.html", {"error": "Email already in use"})

        try:
            # Create user
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            login(request, user)  # Auto-login after registration
            return redirect("index")  # Redirect to task manager
        except IntegrityError:
            return render(request, "tasks/register.html", {"error": "Error creating user. Try again."})

    return render(request, "tasks/register.html")
# Store the token for session-based authentication


# Login View
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)
        if user is None:
            logger.warning(f"Login failed for username: {username}")
            return render(request, "tasks/login.html", {"error": "Invalid Credentials"})

        login(request, user)
        logger.info(f"User {username} authenticated successfully")

        # Fetch JWT token
        try:
            response = requests.post(request.build_absolute_uri(reverse("token_obtain_pair")), data={
                "username": username,
                "password": password
            }, timeout=30)
            response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        except requests.exceptions.RequestException as e:
            logger.error(f"JWT request error: {e}")
            return render(request, "tasks/login.html", {"error": "Server error. Try again later."})

        token = response.json().get("access")
        if not token:
            logger.error("JWT Token missing in API response")
            return render(request, "tasks/login.html", {"error": "Authentication failed"})

        request.session[TOKEN_KEY] = token
        request.session['user_id'] = user.id  # Store user ID

        return redirect("index")

    return render(request, "tasks/login.html")

# Logout View
def logout_view(request):
    request.session.flush()  # Clear session
    return redirect('login')

# Task Manager Page (Only Accessible if Authenticated)

def index(request):
    token = request.session.get(TOKEN_KEY)
    if not token:
        return redirect('login')  # Redirect to login if not authenticated

    # Fetch tasks from API with JWT token
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{settings.BASE_URL}/api/tasks/", headers=headers)

    if response.status_code == 200:
        tasks = response.json().get("results", [])  # Handle paginated response
        return render(request, 'tasks/index.html', {'tasks': tasks})

    return redirect('login')  # Redirect if token is invalid

class TaskViewset(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fileds = ['completed']
    search_fields = ['title', 'description']
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        

@login_required
def add_task(request):
    print("Current User:", request.user)  # Debugging
    print("Is Authenticated?", request.user.is_authenticated)  
    
    if request.method == "POST":
        if request.user.is_authenticated:
            user= request.user
            title = request.POST.get('title')
            Task.objects.create(title=title, user=user)
        
        return redirect('index')
    return redirect('login')

def complete_task(request, task_id):
    task = Task.objects.get(pk=task_id)
    task.completed = not task.completed
    task.save()
    return redirect('index')


def delete_task(request, task_id):
    task = Task.objects.get(pk=task_id)
    task.delete()
    return redirect('index')
        