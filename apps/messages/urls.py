from django.urls import path
from . import views

app_name = "messages"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("booking/<int:booking_id>/", views.conversation_detail, name="conversation_detail"),
    path("booking/<int:booking_id>/send/", views.send_message_view, name="send_message"),
]