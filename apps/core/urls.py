from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('health/live/', views.health_live, name='health_live'),
    path('health/ready/', views.health_ready, name='health_ready'),
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
