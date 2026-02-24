from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'todos', views.TodoViewSet, basename='todo')
router.register(r'todolists', views.TodoListViewSet, basename='todolist')
router.register(r'agents', views.AgentViewSet, basename='agent')
router.register(r'extensions', views.ExtensionViewSet, basename='extension')

urlpatterns = [
    path('', include(router.urls)),
]
