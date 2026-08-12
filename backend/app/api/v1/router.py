from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import auth, guests, properties, reports, reservations, tasks, units

api_router = APIRouter()

# Public
api_router.include_router(auth.router)

# Everything else requires a valid token.
protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(properties.router)
protected.include_router(units.property_units_router)
protected.include_router(units.units_router)
protected.include_router(guests.router)
protected.include_router(reservations.router)
protected.include_router(tasks.router)
protected.include_router(reports.router)

api_router.include_router(protected)
