from django.urls import path

from apps.insights import views

app_name = 'insights'

urlpatterns = [
    path('calendar/', views.calendar_view, name='calendar'),
]
