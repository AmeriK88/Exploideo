from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoiceSequence

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "status", "customer_email", "total", "currency", "issued_at", "created_at")
    list_filter = ("status", "currency", "year")
    search_fields = ("number", "customer_email", "customer_name")
    inlines = [InvoiceItemInline]

@admin.register(InvoiceSequence)
class InvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ("year", "last_number")
