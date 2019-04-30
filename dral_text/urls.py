from django.urls import path
from . import views

urlpatterns = [
    path('strings/', views.view_upload_occurrences),
    path('sentences/', views.view_upload_sentences),
    path('clean/', views.view_clean_data),
]
