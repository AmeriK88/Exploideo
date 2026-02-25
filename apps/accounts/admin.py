# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # 1) Mostrar role en el detalle (editar usuario)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "email")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas importantes", {"fields": ("last_login", "date_joined")}),
        ("Exploideo", {"fields": ("role",)}),
    )

    # 2) Mostrar role en el alta (crear usuario)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "role", "password1", "password2"),
        }),
    )

    # 3) Listado
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")

    # 4) Comodidades
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    list_editable = ("role",)  # opcional: editar role desde el listado