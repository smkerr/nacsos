from django import forms
from .models import *
<<<<<<< HEAD
from tmv_app.models import *
=======
>>>>>>> 77aa37cd70683764d39ae069a81b0aa50822b9e2

class ProjectForm(forms.ModelForm):
    class Meta:
        model = (Project)
        fields = ('title', 'description',)

class ProjectRoleForm(forms.ModelForm):
    class Meta:
        model = (ProjectRoles)
        fields = ('user', 'role',)

class UpdateProjectRoleForm(forms.ModelForm):
    user = forms.CharField(disabled=True)
    class Meta:
        model = (ProjectRoles)
        fields = ('user', 'role',)
        #widgets = {'user': forms.HiddenInput()}
<<<<<<< HEAD


class TopicModelForm(forms.ModelForm):
    class Meta:
        model = (RunStats)
        fields = ('K','alpha','max_features','limit','max_iterations','ngram')
=======
>>>>>>> 77aa37cd70683764d39ae069a81b0aa50822b9e2
