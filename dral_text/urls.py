from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_import),
    path('strings/', views.view_upload_occurrences),
    path('sentences/', views.view_upload_sentences),
    path('remove/', views.view_clean_data),
]
