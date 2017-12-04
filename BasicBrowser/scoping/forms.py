from django import forms
from .models import *

from tmv_app.models import *


class ProjectForm(forms.ModelForm):
    class Meta:
        model = (Project)
        fields = ('title', 'description',)


class NewDoc(forms.ModelForm):

    url = forms.URLField(
        required=False,
        help_text="If there is a url pointing to this document, please provide it here"
    )

    class Meta:
        model = (Doc)
        fields = ('dtype','url',)

class DocForm2(forms.ModelForm):

    py = forms.IntegerField(
        #initial=2017,
        label="Year Published",
        help_text="Leave as 0 if unpublished"
    )
    so = forms.CharField(
        label="Source Title",
        help_text="Enter the journal or book title",
        required=False
    )
    doc = forms.IntegerField()
    class Meta:
        model = (WoSArticle)
        fields = ('doc','ti','ab','py','so',)

    def __init__(self,*args,**kwargs):
        so = kwargs.pop('so',False)
        super(DocForm2, self).__init__(*args, **kwargs)
        self.fields['doc'].widget = forms.HiddenInput()
        if so:
            self.fields['so'].required = True


class AuthorForm(forms.ModelForm):
    class Meta:
        model = (DocAuthInst)
        fields = ('position','surname','initials',)

    def __init__(self,*args,**kwargs):
        super(AuthorForm, self).__init__(*args, **kwargs)
        self.fields['position'].widget = forms.HiddenInput()


class UploadDocFile(forms.ModelForm):
    doc = forms.IntegerField()
    class Meta:
        model = (DocFile)
        fields = ('doc','file',)
    def __init__(self,*args,**kwargs):
        super(UploadDocFile, self).__init__(*args, **kwargs)
        self.fields['doc'].widget = forms.HiddenInput()

class DeleteDocField(forms.Form):
    delete = forms.IntegerField()
    def __init__(self,*args,**kwargs):
        super(DeleteDocField, self).__init__(*args, **kwargs)
        self.fields['delete'].widget = forms.HiddenInput()

class ValidatePasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='You need to enter your password to do this. It cannot be undone',
    )
    widgets = {
        'password': forms.PasswordInput()
    }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ValidatePasswordForm, self).__init__(*args,**kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError('Invalid password')
        return password

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
            'empty_topics',
            'topic_scores_current',
            'topic_year_scores_current',
            'nmf_time',
            'tfidf_time',
            'db_time',
            'status',
            'parent_run_id',
            'docs_seen',
            'notes',
            #'method',
            'error',
            'errortype',
            'iterations',
            'max_topics',
            'term_count',
            'dthreshold'
        )
        #fields = ('K','alpha','limit','ngram','min_freq','max_df','max_features','max_iterations')
