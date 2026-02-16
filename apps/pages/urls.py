from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    #path("", views.home_view, name="home"),
    path("", views.landing_view, name="home"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("dashboard/profile/", views.profile_view, name="profile"),
    path("dashboard/guide/", views.guide_dashboard, name="guide_dashboard"),
    path("dashboard/traveler/", views.traveler_dashboard, name="traveler_dashboard"),
    path("privacy-policy/", views.privacy_policy_view, name="privacy_policy"),
    path("terms-and-conditions/", views.terms_and_conditions_view, name="terms_and_conditions"),
    path("cookie-policy/", views.cookie_policy_view, name="cookie_policy"),
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
]
