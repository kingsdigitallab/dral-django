from django.urls import path
from . import views

urlpatterns = [
    path('import/', views.view_import, name='data_management'),
    path('import/strings/', views.view_upload_occurrences),
    path('import/sentences/', views.view_upload_sentences),
    path('import/texts/', views.view_upload_texts),
    path('import/remove/', views.view_clean_data),

    path('api/v1/occurrences/', views.view_occurrences_api,
         name='api_occurrences'),
]
