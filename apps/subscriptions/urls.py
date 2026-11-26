from django.urls import path

from apps.subscriptions import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.subscription_list, name='list'),
    path('create/', views.subscription_create, name='create'),
    path('<int:pk>/', views.subscription_detail, name='detail'),
    path('<int:pk>/edit/', views.subscription_edit, name='edit'),
    path('<int:pk>/delete/', views.subscription_delete, name='delete'),
    path('<int:pk>/pause/', views.subscription_pause, name='pause'),
    path('<int:pk>/resume/', views.subscription_resume, name='resume'),
    path('<int:pk>/cancel/', views.subscription_cancel, name='cancel'),
    path('payments/<int:pk>/confirm/', views.confirm_payment, name='confirm_payment'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
]
