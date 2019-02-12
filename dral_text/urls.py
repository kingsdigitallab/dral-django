from django.urls import path
from . import views

urlpatterns = [
    path('strings/', views.view_upload_occurrences),
]
