from django.shortcuts import render,redirect
from django.contrib.auth.forms import UserCreationForm
# Create your views here.
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required	

def home(request):
	if request.method == "POST":
		form= UserCreationForm(request.POST)
		if form.is_valid():
			form.save()
			return redirect('login_url')
	else:
		form = UserCreationForm()
	return render(request,'home.html',{'form':form});

@login_required
def dashboardView(request):
	return render(request,'dashboard.html')