from django.urls import path
from .views import OrganizationAPI
urlpatterns = [
    path('', OrganizationAPI.as_view()),
    path('create/', OrganizationAPI.as_view()),
]
