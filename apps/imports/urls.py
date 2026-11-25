from django.urls import path

from apps.imports import views

app_name = 'imports'

urlpatterns = [
    path('upload/', views.upload_csv, name='upload'),
    path('review/<int:upload_id>/', views.review_candidates, name='review'),
    path('confirm/<int:candidate_id>/', views.confirm_candidate, name='confirm_candidate'),
    path('dismiss/<int:candidate_id>/', views.dismiss_candidate, name='dismiss_candidate'),
    path('bulk-confirm/<int:upload_id>/', views.bulk_confirm, name='bulk_confirm'),
    path('bulk-dismiss/<int:upload_id>/', views.bulk_dismiss, name='bulk_dismiss'),
    path('sample-csv/', views.sample_csv, name='sample_csv'),
]
