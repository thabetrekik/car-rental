from django.urls import path
from .views import (
    admin_panel,
    client_delete,
    client_edit,
    client_page,
    dashboard,
    finance_page,
    reservation_notifications,
    maintenance_delete,
    maintenance_page,
    reservation_delete,
    reservation_page,
    vehicle_page,
    vehicle_delete,
    vehicle_edit,
)

urlpatterns = [
    path("", admin_panel, name="panel_admin"),
    path("dashboard/", dashboard, name="dashboard"),
    path("finance/", finance_page, name="finance_page"),
    path("clients/", client_page, name="client_page"),
    path("clients/<int:client_id>/edit/", client_edit, name="client_edit"),
    path("clients/<int:client_id>/delete/", client_delete, name="client_delete"),
    path("vehicles/", vehicle_page, name="vehicle_page"),
    path("vehicles/<int:vehicle_id>/edit/", vehicle_edit, name="vehicle_edit"),
    path("vehicles/<int:vehicle_id>/delete/", vehicle_delete, name="vehicle_delete"),
    path("maintenance/", maintenance_page, name="maintenance_page"),
    path("maintenance/<int:maintenance_id>/delete/", maintenance_delete, name="maintenance_delete"),
    path("reservations/", reservation_page, name="reservation_page"),
    path("reservations/notifications/", reservation_notifications, name="reservation_notifications"),
    path("reservations/<int:reservation_id>/delete/", reservation_delete, name="reservation_delete"),
]
