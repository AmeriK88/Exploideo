import math


EARTH_RADIUS_KM = 6371.0


def calculate_distance_km(lat1, lng1, lat2, lng2):
    """Return great-circle distance in km, or None when any coordinate is invalid."""
    try:
        latitude_1 = float(lat1)
        longitude_1 = float(lng1)
        latitude_2 = float(lat2)
        longitude_2 = float(lng2)
    except (TypeError, ValueError):
        return None

    phi_1 = math.radians(latitude_1)
    phi_2 = math.radians(latitude_2)
    delta_phi = math.radians(latitude_2 - latitude_1)
    delta_lambda = math.radians(longitude_2 - longitude_1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c