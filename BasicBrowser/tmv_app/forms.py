from django import forms
from .models import *
from django.core.validators import MaxValueValidator

from tmv_app.models import *
import scoping.models as sm

class topicAssessmentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        max_value = kwargs.pop('max_value',None)
        super(topicAssessmentForm, self).__init__(*args, **kwargs)
        self.fields["docs"] = forms.IntegerField(max_value=max_value)
    users = forms.ModelMultipleChoiceField(queryset=sm.User.objects.all(),widget=forms.CheckboxSelectMultiple())
    docs = forms.IntegerField()#widget=forms.NumberInput(attrs={'type':'range', 'step': '1'}))
