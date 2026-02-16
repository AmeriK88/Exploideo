from django.urls import path
from .views import invoice_detail_by_booking, invoice_detail, my_invoices

app_name = "billing"

urlpatterns = [
    path("booking/<int:booking_pk>/", invoice_detail_by_booking, name="invoice_by_booking"),
    path("<int:pk>/", invoice_detail, name="invoice_detail"),
    path("mine/", my_invoices, name="my_invoices"),
]
