from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("new/<int:experience_id>/", views.create_booking, name="create"),
    path("my/", views.traveler_bookings, name="traveler_list"),
    path("received/", views.guide_bookings, name="guide_list"),
    path("<int:pk>/", views.booking_detail, name="detail"),
    path("<int:pk>/accept/", views.accept_booking, name="accept"),
    path("<int:pk>/reject/", views.reject_booking, name="reject"),
    path("<int:pk>/request-change/", views.request_booking_change, name="request_change"),
    path("<int:pk>/request-cancel/", views.request_booking_cancel, name="request_cancel"),
    path("<int:pk>/change/<str:decision>/", views.decide_change_request, name="guide_change_decide"),
    path("<int:pk>/cancel/<str:decision>/", views.decide_cancel_request, name="guide_cancel_decide"),
]
