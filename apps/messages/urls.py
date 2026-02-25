from django.urls import path
from apps.messages import views

app_name = "messages"

urlpatterns = [
    # Listar/abrir conversación por booking
    path("booking/<int:booking_id>/", views.conversation_detail, name="conversation_detail"),
    # Enviar mensaje
    path("booking/<int:booking_id>/send/", views.send_message_view, name="send_message"),
]