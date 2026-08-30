import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


# Built-in translation dictionary for Exploideo platform terms
DEFAULT_TRANSLATIONS_ES_EN: Dict[str, str] = {
    "Guías": "Guides",
    "Verificados": "Verified",
    "Disponibilidad": "Availability",
    "Fácil": "Easy",
    "Moderada": "Moderate",
    "Moderado": "Moderate",
    "Difícil": "Hard",
    "Apta para todos": "Suitable for everyone",
    "Menores acompañados": "Minors accompanied",
    "Sin menores": "No minors",
    "Guía verificado": "Verified guide",
    "Viajero": "Traveler",
    "Guía": "Guide",
    "Punto de encuentro": "Meeting point",
    "Ubicación visible": "Visible location",
    "Reservas abiertas": "Bookings open",
    "Reserva aceptada": "Booking accepted",
    "Reserva rechazada": "Booking rejected",
    "Reserva cancelada": "Booking canceled",
    "Borrador": "Draft",
    "Emitida": "Issued",
    "Anulada": "Void",
    "Ordinaria": "Standard",
    "Rectificativa": "Rectificative",
    "Aceptar": "Accept",
    "Rechazar": "Reject",
    "Configurar": "Settings",
    "Ver política": "View policy",
    "Cerrar": "Close",
    "Categoría": "Category",
    "Título": "Title",
    "Descripción": "Description",
    "Imagen": "Image",
    "Precio (€)": "Price (€)",
    "Duración (minutos)": "Duration (minutes)",
    "País": "Country",
    "Región": "Region",
    "Provincia": "Province",
    "Isla": "Island",
    "Ciudad": "City",
    "Dificultad": "Difficulty",
    "Modo de desplazamiento requerido": "Required transport mode",
    "Activa": "Active",
    "Nombre de usuario": "Username",
    "Correo electrónico": "Email",
    "Rol": "Role",
    "Entiendo que esta acción es permanente y desactiva mi cuenta.": "I understand that this action is permanent and disables my account.",
    'Escribe "ELIMINAR PERMANENTEMENTE" para confirmar': 'Type "ELIMINAR PERMANENTEMENTE" to confirm',
    "Esto evita eliminaciones accidentales.": "This prevents accidental deletions.",
    "Debes escribir exactamente: ELIMINAR PERMANENTEMENTE": "You must write exactly: ELIMINAR PERMANENTEMENTE",
    "Idiomas que hablas": "Languages you speak",
    "Biografía / Presentación": "Bio / Presentation",
    "Teléfono": "Phone",
    "Sitio web": "Website",
    "Foto de perfil": "Profile picture",
    "Acreditación de guía oficial": "Official guide license",
    "Seguro RC o documento de autónomo/empresa": "Liability insurance or registration document",
    "Nombre": "First name",
    "Apellidos": "Last name",
    "Nombre público": "Display name",
    "Idioma preferido": "Preferred language",
    "Lun": "Mon",
    "Mar": "Tue",
    "Mié": "Wed",
    "Jue": "Thu",
    "Vie": "Fri",
    "Sáb": "Sat",
    "Dom": "Sun",
    "Días de la semana permitidos": "Allowed days of the week",
    "Fecha inicio": "Start date",
    "Fecha fin": "End date",
    "Capacidad diaria (personas)": "Daily capacity (people)",
    "Max de excursiones (por día)": "Max excursions (per day)",
    "Max por reserva (personas)": "Max per booking (people)",
    "Calificación": "Rating",
    "Comentario": "Comment",
    "Cuenta tu experiencia...": "Share your experience...",
    "Activa": "Active",
    "Cerrada": "Closed",
    "Bloqueada": "Blocked",
    "Texto": "Text",
    "Sistema": "System",
    "Español": "Spanish",
    "English": "English",
    "Deutsch": "German",
    "Français": "French",
    "Italiano": "Italian",
    "Português": "Portuguese",
    "Nederlands": "Dutch",
    "Svenska": "Swedish",
    "Polski": "Polish",
    "Dansk": "Danish",
    "Suomi": "Finnish",
    "中文 (Chinese)": "Chinese",
    "Vehículo propio": "Own vehicle",
    "Bicicleta": "Bicycle",
    "A pie": "On foot",
    "Minibus": "Minibus",
    "Pendiente": "Pending",
    "Aceptada": "Accepted",
    "Rechazada": "Rejected",
    "Cancelada": "Canceled",
    "Cambio solicitado": "Change requested",
    "Cancelación solicitada": "Cancel requested",
    "Cargando…": "Loading…",
    "Procesando…": "Processing…",
    "Obteniendo tu ubicación...": "Getting your location...",
    "No se pudo obtener tu ubicación ahora. Puedes seguir usando filtros normales.": "Could not get your location now. You can continue using normal filters.",
    "Permiso de ubicación denegado. Puedes seguir filtrando de forma manual.": "Location permission denied. You can continue filtering manually.",
    "Tu ubicación no está disponible temporalmente. Inténtalo de nuevo en unos segundos.": "Your location is temporarily unavailable. Try again in a few seconds.",
    "La ubicación tardó demasiado. Inténtalo de nuevo.": "Location took too long. Try again.",
    "No se pudo activar Cerca de mí ahora mismo.": "Could not activate Near me right now.",
    "Este navegador no soporta geolocalización. Usa los filtros normales.": "This browser does not support geolocation. Use normal filters.",
    "Solicitud de reserva enviada": "Booking request sent",
    "Reserva aceptada": "Booking accepted",
    "Reserva rechazada": "Booking rejected",
    "Reserva cancelada": "Booking canceled",
    "Cambio de fecha rechazado": "Date change rejected",
    "Solicitud de cancelación rechazada": "Cancellation request rejected",
    "Solicitud de cancelación aceptada": "Cancellation request accepted",
    "Reserva cancelada por el viajero": "Booking canceled by traveler",
    "Descubre experiencias": "Discover experiences",
    "Explora rutas, volcanes, calas y planes únicos con guías locales.": "Explore routes, volcanoes, coves and unique plans with local guides.",
    "+ Crear experiencia": "+ Create experience",
    "Mostrando experiencias cerca de tu ubicación actual.": "Showing experiences near your current location.",
    "Ups… no encontramos nada 😅": "Oops… we found nothing 😅",
    "Prueba con otros términos o limpia los filtros.": "Try other terms or clear filters.",
    "Limpiar filtros": "Clear filters",
    "No hay experiencias activas todavía": "There are no active experiences yet",
    "Vuelve más tarde o ajusta los filtros.": "Come back later or adjust filters.",
    "Ver experiencias": "View experiences",
}


def translate_po_content(content: str, lang: str) -> Tuple[str, int]:
    count = 0

    # Clean fuzzy markers first
    lines = []
    for line in content.splitlines():
        if line.strip() == "#, fuzzy":
            continue
        lines.append(line)
    clean_content = "\n".join(lines)

    def replace_empty_msgstr(match: re.Match) -> str:
        nonlocal count
        msgid_str = match.group(1).replace(r'\"', '"').replace(r'\n', '\n')
        
        # Header entry (msgid "") must not be touched
        if not msgid_str:
            return match.group(0)

        translated = DEFAULT_TRANSLATIONS_ES_EN.get(msgid_str, msgid_str)
        count += 1
        escaped_translated = translated.replace('\\', r'\\').replace('"', r'\"').replace('\n', r'\n')
        return f'msgid "{match.group(1)}"\nmsgstr "{escaped_translated}"'

    pattern = re.compile(r'msgid "([^"]*)"\nmsgstr ""')
    new_content = pattern.sub(replace_empty_msgstr, clean_content)
    return new_content, count


class Command(BaseCommand):
    help = "Translates missing (empty msgstr) entries in django.po files while preserving file formatting."

    def add_arguments(self, parser):
        parser.add_argument(
            "-l", "--language",
            default="en",
            help="Language code to translate missing messages for (default: 'en').",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate translation and display count without modifying PO files.",
        )

    def handle(self, *args, **options):
        lang = options["language"]
        dry_run = options["dry_run"]

        locale_dir = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES"
        po_file = locale_dir / "django.po"

        if not po_file.exists():
            raise CommandError(f"PO file not found at {po_file}. Run 'python manage.py makemessages -l {lang}' first.")

        content = po_file.read_text(encoding="utf-8")
        new_content, count = translate_po_content(content, lang)

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY-RUN] Would translate {count} entries in {po_file}."))
        else:
            po_file.write_text(new_content, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Successfully translated {count} missing entries in {po_file}."))
