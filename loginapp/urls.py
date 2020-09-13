from django.conf.urls import url
from . import views
from django.contrib.auth.views import LoginView
from django.contrib import admin
from django.urls import path

urlpatterns = [
	
    path('',views.home,name='home'),
    path('dashboard/',views.dashboardView,name="dashboard"),
    path('login/',LoginView.as_view(),name="login_url"),

]
