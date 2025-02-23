from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewset
from . import views

router = DefaultRouter()
router.register(r'tasks', TaskViewset)

urlpatterns = [
    path('api/', include(router.urls)),
    path("register/", views.register_view, name="register"),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path("", views.index, name="index"),
    path("add/", views.add_task, name="add_task"),
    path("complete/<int:task_id>", views.complete_task, name="complete_task"),
    path("delete/<int:task_id>", views.delete_task, name="delete_task"),
    
]
