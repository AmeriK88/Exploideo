from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from apps.profiles.forms import GuideProfileForm, TravelerProfileForm
from django.db.models import Count, Q, Sum

from apps.experiences.models import Experience, Category
from apps.bookings.models import Booking
from apps.reviews.models import Review

from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import NewsletterSubscriber


def home_view(request):
    featured_experiences = (
        Experience.objects
        .filter(is_active=True)
        .select_related("guide", "category")
        .order_by("-created_at")[:6]
    )

    home_reviews = (
        Review.objects
        .filter(status=Review.Status.PUBLISHED)
        .select_related("traveler", "experience", "experience__guide")
        .order_by("-created_at")[:6]
    )

    return render(request, "pages/home.html", {
        "featured_experiences": featured_experiences,
        "home_reviews": home_reviews,
    })


@login_required
def dashboard_redirect(request):
    if request.user.is_guide():
        return redirect("pages:guide_dashboard")
    return redirect("pages:traveler_dashboard")


@login_required
def guide_dashboard(request):
    if not request.user.is_guide():
        return redirect("pages:dashboard")

    today = timezone.localdate()
    since = today - timedelta(days=30)

    experiences_qs = Experience.objects.filter(guide=request.user, is_active=True)
    experiences_count = experiences_qs.count()

    guide_bookings_qs = Booking.objects.filter(experience__guide=request.user)

    bookings_30d = guide_bookings_qs.filter(created_at__date__gte=since).count()

    # Pendientes “de acción” para el guía (NUEVO)
    pending_new = guide_bookings_qs.filter(status=Booking.Status.PENDING).count()
    pending_change = guide_bookings_qs.filter(status=Booking.Status.CHANGE_REQUESTED).count()
    pending_cancel = guide_bookings_qs.filter(status=Booking.Status.CANCEL_REQUESTED).count()

    pending_total = pending_new + pending_change + pending_cancel

    revenue_30d = (
        guide_bookings_qs.filter(
            status=Booking.Status.ACCEPTED,
            created_at__date__gte=since,
        )
        .aggregate(total=Sum("total_price"))["total"]
        or Decimal("0.00")
    )

    # “No vistas” por el guía (ya lo tenías)
    unseen_guide_bookings = guide_bookings_qs.filter(seen_by_guide=False).count()

    # Reservas recientes: puedes priorizar las que requieren acción arriba (opcional)
    recent_bookings = (
        guide_bookings_qs.select_related("experience", "traveler")
        .order_by("-created_at")[:8]
    )

    reviews_total = Review.objects.filter(
        experience__guide=request.user,
        status=Review.Status.PUBLISHED,
    ).count()

    kpis = {
        "experiences": experiences_count,
        "bookings_30d": bookings_30d,

        # Aquí cambiamos pending para que sea “pendientes totales”
        "pending": pending_total,

        # Si quieres mostrar desglose en el template
        "pending_new": pending_new,
        "pending_change": pending_change,
        "pending_cancel": pending_cancel,

        "revenue_30d": revenue_30d,
        "reviews": reviews_total,
    }

    return render(
        request,
        "pages/guide_dashboard.html",
        {
            "kpis": kpis,
            "unseen_guide_bookings": unseen_guide_bookings,
            "recent_bookings": recent_bookings,
        },
    )


@login_required
def traveler_dashboard(request):
    # Solo traveler
    if request.user.is_guide():
        return redirect("pages:dashboard")

    now = timezone.localtime()
    today = now.date()
    now_time = now.time()
    since = today - timedelta(days=30)

    categories = Category.objects.all()

    # Top experiencias (por reservas pending+accepted). Si no hay reservas, se ordena por created_at.
    top_experiences = (
        Experience.objects.filter(is_active=True)
        .select_related("guide", "category")
        .annotate(
            bookings_count=Count(
                "bookings",
                filter=Q(bookings__status__in=[Booking.Status.PENDING, Booking.Status.ACCEPTED]),
            )
        )
        .order_by("-bookings_count", "-created_at")[:6]
    )

    # Bookings del traveler
    traveler_bookings_qs = (
        Booking.objects
        .filter(traveler=request.user)
        .select_related("experience", "experience__guide")
    )

    # KPIs
    bookings_30d = traveler_bookings_qs.filter(created_at__date__gte=since).count()
    accepted = traveler_bookings_qs.filter(status=Booking.Status.ACCEPTED).count()
    rejected = traveler_bookings_qs.filter(status=Booking.Status.REJECTED).count()
    pending = traveler_bookings_qs.filter(status=Booking.Status.PENDING).count()

    spent_30d = (
        traveler_bookings_qs.filter(
            status=Booking.Status.ACCEPTED,
            created_at__date__gte=since,
        )
        .aggregate(total=Sum("total_price"))["total"]
        or Decimal("0.00")
    )

    unseen_traveler_bookings = traveler_bookings_qs.filter(seen_by_traveler=False).count()

    # Próxima reserva (incluye HOY si aún no ha empezado)
    base_next_qs = (
        traveler_bookings_qs
        .exclude(status__in=[Booking.Status.REJECTED, Booking.Status.CANCELED])
    )

    # 1) Si queda algo hoy (pickup_time >= ahora), esto manda
    today_next = (
        base_next_qs
        .filter(date=today, pickup_time__gte=now_time)
        .order_by("pickup_time", "created_at")
        .first()
    )

    # 2) Si no hay nada hoy, buscamos desde mañana en adelante
    future_next = (
        base_next_qs
        .filter(date__gt=today)
        .order_by("date", "pickup_time", "created_at")
        .first()
    )

    next_booking = today_next or future_next

    # Tabla reservas recientes
    recent_bookings = traveler_bookings_qs.order_by("-created_at")[:8]

    reviews_count = request.user.reviews.filter(status=Review.Status.PUBLISHED).count()

    kpis = {
        "bookings_30d": bookings_30d,
        "spent_30d": spent_30d,
        "accepted": accepted,
        "rejected": rejected,
        "pending": pending,
        "reviews": reviews_count,
    }

    return render(
        request,
        "pages/traveler_dashboard.html",
        {
            "categories": categories,
            "top_experiences": top_experiences,
            "kpis": kpis,
            "unseen_traveler_bookings": unseen_traveler_bookings,
            "next_booking": next_booking,
            "recent_bookings": recent_bookings,
        },
    )

@login_required
def profile_view(request):
    if request.user.is_guide():
        profile = request.user.guide_profile
        FormClass = GuideProfileForm
        template = "profiles/guide_edit.html"

        if request.method == "POST":
            form = FormClass(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Perfil actualizado correctamente.")
                return redirect("pages:profile")
        else:
            form = FormClass(instance=profile)

    else:
        profile = request.user.traveler_profile
        template = "profiles/traveler_edit.html"

        if request.method == "POST":
            form = TravelerProfileForm(
                request.POST,
                request.FILES,
                instance=profile,
                user=request.user,   # 👈 CLAVE
            )
            if form.is_valid():
                form.save()
                messages.success(request, "Perfil actualizado correctamente.")
                return redirect("pages:profile")
        else:
            form = TravelerProfileForm(
                instance=profile,
                user=request.user,   # 👈 CLAVE
            )

    return render(request, template, {"form": form, "profile": profile})


def privacy_policy_view(request):
    return render(request, "pages/privacy_policy.html")


def terms_and_conditions_view(request):
    return render(request, "pages/terms_and_conditions.html")


def cookie_policy_view(request):
    return render(request, "pages/cookie_policy.html")

@require_POST
def newsletter_subscribe(request):
    email = (request.POST.get("email") or "").strip().lower()
    source = (request.POST.get("source") or "footer").strip()

    region = (request.POST.get("region") or "").strip()
    island = (request.POST.get("island") or "").strip()
    role = (request.POST.get("role") or "").strip()
    is_official_guide = request.POST.get("is_official_guide") in ("1", "on", "true", "True")
    consent = request.POST.get("consent") in ("1", "on", "true", "True")

    if not consent:
        messages.error(request, "Necesitamos tu consentimiento para poder avisarte por email.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Ese email no parece válido.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    obj, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={
            "source": source,
            "region": region,
            "island": island,
            "role": role,
            "is_official_guide": is_official_guide,
            "consent": consent,
        },
    )

    # Si ya existía, puedes “enriquecer” el registro
    if not created:
        changed = False
        if source and obj.source != source:
            obj.source = source; changed = True
        if region and obj.region != region:
            obj.region = region; changed = True
        if island and obj.island != island:
            obj.island = island; changed = True
        if role and obj.role != role:
            obj.role = role; changed = True
        if is_official_guide and not obj.is_official_guide:
            obj.is_official_guide = True; changed = True
        if consent and not obj.consent:
            obj.consent = True; changed = True

        if changed:
            obj.save(update_fields=["source","region","island","role","is_official_guide","consent"])

    if created:
        messages.success(request, "¡Listo! Te avisaremos cuando haya novedades.")
    else:
        messages.info(request, "Ese email ya estaba registrado 😉 (si añadiste info extra, queda guardada)")

    return redirect(request.META.get("HTTP_REFERER", "/"))


def landing_view(request):
    return render(request, "pages/landing/landing.html")