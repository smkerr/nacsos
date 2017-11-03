from django import forms
from .models import *

from tmv_app.models import *


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



class TopicModelForm(forms.ModelForm):
    class Meta:
        model = (RunStats)
        exclude = (
            'topic',
            'dynamictopic',
            'term',
            'run_id',
            'query',
            'process_id',
            'start',
            'batch_count',
            'last_update',
            'topic_titles_current',
            'topic_scores_current',
            'topic_year_scores_current',
            'nmf_time',
            'tfidf_time',
            'db_time',
            'status',
            'parent_run_id',
            'docs_seen',
            'notes',
            'method',
            'error',
            'errortype',
            'iterations',
            'max_topics',
            'term_count',
            'dthreshold'
        )
        #fields = ('K','alpha','limit','ngram','min_freq','max_df','max_features','max_iterations')
