from decimal import Decimal
from typing import Optional

from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.availability.models import ExperienceAvailability
from apps.bookings.models import Booking
from apps.reviews.models import Review
from apps.reviews.services import traveler_can_review
from core.decorators import guide_required

from .forms import ExperienceForm
from .models import Category, Experience
from .services.distance import calculate_distance_km
from .services.geocoding import geocode_experience_location


GEOCODING_FIELDS = ("location", "city", "island", "province", "region", "country")


def _location_fields_changed(original_values, cleaned_data):
    for field_name in GEOCODING_FIELDS:
        before = (original_values.get(field_name) or "").strip()
        after = (cleaned_data.get(field_name) or "").strip()
        if before != after:
            return True
    return False


def _apply_geocoding_if_available(exp):
    coordinates = geocode_experience_location(exp)
    if not coordinates:
        return False

    latitude, longitude = coordinates
    exp.latitude = Decimal(str(latitude))
    exp.longitude = Decimal(str(longitude))
    exp.save(update_fields=["latitude", "longitude"])
    return True


def _extract_filters(request):
    return {
        "q": request.GET.get("q", "").strip(),
        "category": request.GET.get("category", "").strip(),
        "island": request.GET.get("island", "").strip(),
        "city": request.GET.get("city", "").strip(),
        "min_price": request.GET.get("min_price", "").strip(),
        "max_price": request.GET.get("max_price", "").strip(),
        "max_duration": request.GET.get("max_duration", "").strip(),
        "sort": request.GET.get("sort", "recent").strip(),
        "near_me": request.GET.get("near_me", "").strip(),
        "user_lat": request.GET.get("user_lat", "").strip(),
        "user_lng": request.GET.get("user_lng", "").strip(),
        "max_km": request.GET.get("max_km", "").strip(),
    }


def _parse_float(value: str, *, min_value: float, max_value: float) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if parsed < min_value or parsed > max_value:
        return None
    return parsed


def _extract_near_me_payload(filters):
    near_me_raw = (filters.get("near_me") or "").lower()
    near_me_requested = near_me_raw in {"1", "true", "yes", "on"}

    if not near_me_requested:
        return {
            "requested": False,
            "active": False,
            "user_lat": None,
            "user_lng": None,
            "max_km": None,
            "error": "",
        }

    user_lat = _parse_float(filters.get("user_lat"), min_value=-90.0, max_value=90.0)
    user_lng = _parse_float(filters.get("user_lng"), min_value=-180.0, max_value=180.0)
    max_km = _parse_float(filters.get("max_km"), min_value=0.1, max_value=20000.0)

    if user_lat is None or user_lng is None:
        return {
            "requested": True,
            "active": False,
            "user_lat": None,
            "user_lng": None,
            "max_km": max_km,
            "error": "No se pudo activar Cerca de mí porque la ubicación no es válida.",
        }

    return {
        "requested": True,
        "active": True,
        "user_lat": user_lat,
        "user_lng": user_lng,
        "max_km": max_km,
        "error": "",
    }


def _order_experiences_by_distance(experiences, *, user_lat, user_lng, max_km=None):
    georeferenced = list(experiences.exclude(latitude__isnull=True).exclude(longitude__isnull=True))
    non_georeferenced = list(experiences.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True)))

    ranked = []
    for exp in georeferenced:
        distance_km = calculate_distance_km(user_lat, user_lng, exp.latitude, exp.longitude)
        if distance_km is None:
            non_georeferenced.append(exp)
            continue

        if max_km is not None and distance_km > max_km:
            continue

        exp.distance_km = round(distance_km, 1)
        ranked.append((distance_km, exp))

    ranked.sort(key=lambda item: item[0])
    ordered = [exp for _, exp in ranked] + non_georeferenced
    return ordered


def _apply_common_experience_filters(experiences, filters):
    if filters["q"]:
        q_value = filters["q"]
        experiences = experiences.filter(
            Q(title__icontains=q_value)
            | Q(description__icontains=q_value)
            | Q(location__icontains=q_value)
            | Q(country__icontains=q_value)
            | Q(region__icontains=q_value)
            | Q(province__icontains=q_value)
            | Q(island__icontains=q_value)
            | Q(city__icontains=q_value)
            | Q(tags__icontains=q_value)
            | Q(guide__username__icontains=q_value)
            | Q(category__name__icontains=q_value)
        )

    if filters["category"]:
        experiences = experiences.filter(category__slug=filters["category"])

    if filters["island"]:
        experiences = experiences.filter(island__iexact=filters["island"])

    if filters["city"]:
        experiences = experiences.filter(city__iexact=filters["city"])

    if filters["min_price"]:
        try:
            experiences = experiences.filter(price__gte=float(filters["min_price"]))
        except ValueError:
            pass

    if filters["max_price"]:
        try:
            experiences = experiences.filter(price__lte=float(filters["max_price"]))
        except ValueError:
            pass

    if filters["max_duration"]:
        try:
            experiences = experiences.filter(duration_minutes__lte=int(filters["max_duration"]))
        except ValueError:
            pass

    return experiences


def experience_list(request):
    # Público: solo experiencias activas de guías verificados
    experiences = (
        Experience.objects.filter(
            is_active=True,
            guide__guide_profile__verification_status="verified",
        )
        .select_related("guide", "category")
    )

    categories = Category.objects.all()
    filters = _extract_filters(request)
    near_me_payload = _extract_near_me_payload(filters)

    # ¿Hay filtros activos? (para cambiar el empty state)
    has_filters = any(
        [
            filters["q"],
            filters["category"],
            filters["island"],
            filters["city"],
            filters["min_price"],
            filters["max_price"],
            filters["max_duration"],
            filters["sort"] != "recent",
            near_me_payload["requested"],
        ]
    )

    experiences = _apply_common_experience_filters(experiences, filters)

    # Ordenación por distancia (phase 1 en Python) o por criterios existentes.
    if near_me_payload["active"]:
        experiences = _order_experiences_by_distance(
            experiences,
            user_lat=near_me_payload["user_lat"],
            user_lng=near_me_payload["user_lng"],
            max_km=near_me_payload["max_km"],
        )
    else:
        if filters["sort"] == "price_asc":
            experiences = experiences.order_by("price", "-created_at")
        elif filters["sort"] == "price_desc":
            experiences = experiences.order_by("-price", "-created_at")
        elif filters["sort"] == "duration_asc":
            experiences = experiences.order_by("duration_minutes", "-created_at")
        elif filters["sort"] == "duration_desc":
            experiences = experiences.order_by("-duration_minutes", "-created_at")
        elif filters["sort"] == "popular":
            experiences = experiences.annotate(
                bookings_count=Count(
                    "bookings",
                    filter=Q(bookings__status__in=[Booking.Status.PENDING, Booking.Status.ACCEPTED]),
                )
            ).order_by("-bookings_count", "-created_at")
        else:
            experiences = experiences.order_by("-created_at")

    context = {
        "experiences": experiences,
        "categories": categories,
        "has_filters": has_filters,
        "filters": filters,
        "near_me_requested": near_me_payload["requested"],
        "near_me_active": near_me_payload["active"],
        "near_me_error": near_me_payload["error"],
    }
    return render(request, "experiences/list.html", context)

@guide_required
def my_experiences(request):
    experiences = (
        Experience.objects.filter(guide=request.user)
        .select_related("guide", "category")
    )

    categories = Category.objects.all()
    filters = _extract_filters(request)

    has_filters = any(
        [
            filters["q"],
            filters["category"],
            filters["island"],
            filters["city"],
            filters["min_price"],
            filters["max_price"],
            filters["max_duration"],
            filters["sort"] != "recent",
        ]
    )

    experiences = _apply_common_experience_filters(experiences, filters)

    # Ordenación (igual estilo que list)
    if filters["sort"] == "price_asc":
        experiences = experiences.order_by("price", "-created_at")
    elif filters["sort"] == "price_desc":
        experiences = experiences.order_by("-price", "-created_at")
    elif filters["sort"] == "duration_asc":
        experiences = experiences.order_by("duration_minutes", "-created_at")
    elif filters["sort"] == "duration_desc":
        experiences = experiences.order_by("-duration_minutes", "-created_at")
    else:
        experiences = experiences.order_by("-created_at")

    context = {
        "experiences": experiences,
        "categories": categories,
        "has_filters": has_filters,
        "filters": filters,
    }
    return render(request, "experiences/my_list.html", context)


@guide_required
def experience_create(request):
    if request.method == "POST":
        form = ExperienceForm(request.POST, request.FILES)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.guide = request.user
            exp.save()

            geocoded = _apply_geocoding_if_available(exp)
            if geocoded:
                messages.success(request, "Experiencia creada correctamente.")
            else:
                messages.warning(
                    request,
                    "Experiencia creada correctamente, pero no se pudieron resolver las coordenadas automáticamente por ahora.",
                )

            return redirect("experiences:list")
    else:
        form = ExperienceForm()

    return render(request, "experiences/create.html", {"form": form})


def experience_detail(request, pk):
    exp = get_object_or_404(
        Experience.objects.select_related("guide", "category", "availability"),
        pk=pk,
    )

    availability = getattr(exp, "availability", None)

    # Esto es lo que te evita el RelatedObjectDoesNotExist en template
    gp = getattr(exp.guide, "guide_profile", None)

    public_reviews = (
        Review.objects.filter(experience=exp, status=Review.Status.PUBLISHED)
        .select_related("traveler")
        .order_by("-created_at")
    )

    review_stats = public_reviews.aggregate(
        avg=Avg("rating"),
        count=Count("id"),
    )

    can_review = False
    if request.user.is_authenticated:
        can_review = traveler_can_review(traveler=request.user, experience=exp)

    return render(
        request,
        "experiences/detail.html",
        {
            "exp": exp,
            "gp": gp,
            "availability": availability,
            "public_reviews": public_reviews,
            "review_stats": review_stats,
            "can_review": can_review,
        },
    )


@guide_required
def experience_edit(request, pk):
    exp = get_object_or_404(Experience, pk=pk, guide=request.user)
    original_location_values = {field: getattr(exp, field, "") for field in GEOCODING_FIELDS}

    availability, _ = ExperienceAvailability.objects.get_or_create(experience=exp)

    if request.method == "POST":
        form = ExperienceForm(request.POST, request.FILES, instance=exp)
        if form.is_valid():
            exp = form.save()

            if _location_fields_changed(original_location_values, form.cleaned_data):
                geocoded = _apply_geocoding_if_available(exp)
                if geocoded:
                    messages.success(request, "Experiencia actualizada.")
                else:
                    messages.warning(
                        request,
                        "Experiencia actualizada, pero no se pudieron actualizar las coordenadas automáticamente.",
                    )
            else:
                messages.success(request, "Experiencia actualizada.")

            return redirect("experiences:detail", pk=exp.pk)
    else:
        form = ExperienceForm(instance=exp)

    return render(request, "experiences/edit.html", {
        "form": form,
        "exp": exp,
        "availability": availability,
    })


@guide_required
def experience_delete(request, pk):
    exp = get_object_or_404(Experience, pk=pk, guide=request.user)

    if request.method == "POST":
        exp.delete()
        messages.success(request, "Experiencia eliminada.")
        return redirect("experiences:list")

    return render(request, "experiences/delete.html", {"exp": exp})
