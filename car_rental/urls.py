"""
URL configuration for car_rental project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import (
    car_details_page,
    cars_page,
    client_documents_page,
    index,
    online_payment_page,
    reservation_history_page,
    reservation_page,
    workflow_page,
)

urlpatterns = [
    path('', index, name='index'),
    path('cars/', cars_page, name='cars'),
    path('workflow/', workflow_page, name='workflow'),
    path('cars/<int:vehicle_id>/', car_details_page, name='car_detail'),
    path('payments/<int:reservation_id>/', online_payment_page, name='online_payment'),
    path('documents/', client_documents_page, name='client_documents'),
    path('reservations/history/', reservation_history_page, name='reservation_history'),
    path('reservation/<int:vehicle_id>/', reservation_page, name='reservation'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('staff/', include('panel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
