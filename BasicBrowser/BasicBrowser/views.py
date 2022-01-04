from django.http import HttpResponse
from django.template import loader
from django.apps import apps
from django.conf import settings
from django.conf import settings
from django.utils.module_loading import import_module

def index(request):
    template = loader.get_template('scoping/base_index.html')
    apps = [
        {'name': 'lotto','app_url': '/lotto'},
        {'name': 'scoping','app_url': '/scoping'},
        {'name': 'tmv_app','app_url': '/tmv_app/runs'}
        # {'name': 'parliament', 'app_url': '/parliament'}
    ]
    context = {
        'site_header': 'MCC-APSIS',
        'app_list': apps
    }
    return HttpResponse(template.render(context, request))

from django.contrib.auth import login, authenticate
from BasicBrowser.forms import UserCreationForm
from django.shortcuts import render, redirect

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('/')
    else:
        form = UserCreationForm()
    return render(request, 'scoping/signup.html', {'form': form})
