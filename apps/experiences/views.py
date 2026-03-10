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
    }


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
        ]
    )

    experiences = _apply_common_experience_filters(experiences, filters)

    # Ordenación
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
            messages.success(request, "Experiencia creada correctamente.")
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
            "gp": gp,  # ✅ pásalo al template
            "availability": availability,
            "public_reviews": public_reviews,
            "review_stats": review_stats,
            "can_review": can_review,
        },
    )


@guide_required
def experience_edit(request, pk):
    exp = get_object_or_404(Experience, pk=pk, guide=request.user)

    # asegura que exista siempre (así el template puede mostrar resumen/CTA sin ifs raros)
    availability, _ = ExperienceAvailability.objects.get_or_create(experience=exp)

    if request.method == "POST":
        form = ExperienceForm(request.POST, request.FILES, instance=exp)
        if form.is_valid():
            form.save()
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
