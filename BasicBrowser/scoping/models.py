from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from nltk import ngrams
from django.contrib.postgres.fields import ArrayField
import uuid
from random import randint
import cities
from django.db.models.signals import post_save, m2m_changed, pre_delete
from django.dispatch import receiver
from django.urls import reverse
import tmv_app
import uuid
import difflib
from sklearn.metrics import cohen_kappa_score
import os
from .validators import *
import scoping
from django.db import transaction
from celery import current_app
from scoping.utils import utils
import re
# Create your models here.

def get_notnull_fields(model):
    not_null_fields = []
    for f in model._meta.get_fields():
        if not f.null:
            not_null_fields.append(f)
    return not_null

class SnowballingSession(models.Model):

    INPROGRESS = 0
    COMPLETED  = 1

    Status = (
        (INPROGRESS, 'In progress'),
        (COMPLETED,  'Completed'),
    )


    name           = models.TextField(null=True, unique=True, verbose_name="SB Name")
    initial_pearls = models.TextField(null=True,              verbose_name="SB Initial Pearls")
    date           = models.DateTimeField(                    verbose_name="SB Date")
    #    completed      = models.BooleanField(verbose_name="Is SB Completed")
    status         = models.IntegerField(
                         choices      = Status,
                         default      = 0,
                         db_index     = True,
                         verbose_name = "SB Status")
    working        = models.BooleanField(default=False)
    working_pb2    = models.BooleanField(default=False) # This a marker for when the last step is going on
    users          = models.ManyToManyField(User)
    database       = models.CharField(max_length=6,null=True, verbose_name="Query database")
    category     = models.ForeignKey('Category', on_delete=models.CASCADE, null=True)

    def __str__(self):
      return self.name

class Project(models.Model):

    title = models.TextField(null=True)
    description = models.TextField(null=True)
    users = models.ManyToManyField(User, through='ProjectRoles')
    queries = models.IntegerField(default=0)
    docs = models.IntegerField(default=0)
    reldocs = models.IntegerField(default=0)
    tms = models.IntegerField(default=0)

    def __str__(self):
      return self.title



class StudyEffect(models.Model):

    GROUPS = [
        (5, "General variables"),
        (6, "Difference of means"),
        (1,"Coefficient"),
        (7,"Uncertainty"),
        (2,"Significance"),
        (3,"Sample size"),
        (4,"Study scope"),

    ]


    doc = models.ForeignKey('Doc',on_delete=models.CASCADE)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)



    ## User entered fields

    #g1
    coefficient = models.FloatField(null=True, blank=True)
    coefficient.group = 1

    direction = (
        (1,'Increase'),
        # definitely not neutral?
        (-1,'Decrease')
    )
    effect_direction=models.IntegerField(choices=direction)
    effect_direction.group = 1

    #g7
    coefficient_sd = models.FloatField(null=True, blank=True)
    coefficient_sd.group = 7
    coefficient_sd_type = models.TextField(null=True, blank=True)
    coefficient_sd_type.group=7

    #g2
    significance_test = models.TextField()
    significance_test.group = 2
    test_statistic = models.FloatField(null=True, blank=True)
    test_statistic.group=2
    test_statistic_df = models.IntegerField(null=True, blank=True)
    test_statistic_df.group=2
    p_value = models.FloatField()
    p_value.group=2

    tail_choices = (
        (1,"one-tailed"),
        (2,"two-tailed")
    )
    test_tails = models.IntegerField(choices=tail_choices)
    test_tails.group=2

    #g3 - sample size
    total_sample_size = models.PositiveIntegerField(null=True, blank=True)
    total_sample_size.group=3
    treatment_sample_size = models.PositiveIntegerField(null=True, blank=True)
    treatment_sample_size.group=3
    control_sample_size = models.PositiveIntegerField(null=True, blank=True)
    control_sample_size.group=3

    #g4 Study variables
    geographic_scope = models.TextField()
    geographic_scope.group=4
    geographic_location = models.TextField(null=True,blank=True)
    geographic_location.group=4
    aggregation_level = models.TextField(null=True, blank=True)
    aggregation_level.group=4
    controls = models.ManyToManyField('Controls')
    controls.group=4

    #g5 General

    page = models.PositiveSmallIntegerField()
    page.group=5
    statistical_technique = models.TextField()
    statistical_technique.group=5

    dependent_variable = models.TextField()
    dependent_variable.group=5



    treated_mean = models.FloatField(null=True, blank=True)
    treated_mean.group=6
    control_mean = models.FloatField(null=True, blank=True)
    control_mean.group=6
    diff_mean = models.FloatField(null=True, blank=True)
    diff_mean.group=6

    treated_sd = models.FloatField(null=True, blank=True)
    treated_sd.group=6
    control_sd = models.FloatField(null=True, blank=True)
    control_sd.group=6
    pooled_sd = models.FloatField(null=True, blank=True)
    pooled_sd.group=6


    #Choices? Predefined?


    # Regions etc from django cities?


    def __str__(self):
        if self.coefficient is not None:
            return str(self.coefficient)
        elif self.diff_mean is not None:
            return str(self.diff_mean)
        else:
            return "page {}".format(self.page)


    ## Intervention
class DocMetaCoding(models.Model):
    doc = models.ForeignKey('Doc', on_delete=models.CASCADE)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    assignment_time = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(null=True)
    finish_time = models.DateTimeField(null=True)

    coded = models.BooleanField(default=False)


class Controls(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    name = models.TextField()


class Intervention(models.Model):
    effect = models.ForeignKey(StudyEffect, on_delete=models.CASCADE)
    intervention_subtypes = models.ManyToManyField('InterventionSubType')
    framing_unit = models.TextField(null=True)
    timing = models.TextField(null=True)
    payment = models.TextField(null=True)
    granularity = models.TextField(null=True)
    medium = models.TextField(null=True)
    duration = models.IntegerField(null=True, help_text="weeks")
    followup = models.IntegerField(null=True)

    def __str__(self):
        itypes = self.intervention_subtypes.all().values_list('name',flat=True)
        return "Intervention - {}".format("; ".join(itypes))


class PopCharField(models.Model):
    project = models.ForeignKey('Project',on_delete=models.CASCADE)
    name = models.TextField()
    unit = models.TextField(null=True, blank=True)
    numeric = models.BooleanField(default=False)

    def __str__(self):
        x = "{} - {}".format(self.name, self.unit)
        if self.numeric:
            x+=" (numeric)"
        return x

class PopChar(models.Model):
    effect = models.ForeignKey(StudyEffect, on_delete=models.CASCADE)
    field = models.ForeignKey(PopCharField, on_delete=models.CASCADE)
    value = models.FloatField(null=True)
    str_value = models.TextField(null=True)




class InterventionType(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    name = models.TextField()

    def __str__(self):
      return self.name

class InterventionSubType(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    interventiontype = models.ForeignKey(InterventionType,on_delete=models.CASCADE)
    name = models.TextField()
    def __str__(self):
      return self.name

class ProjectChoice(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    field = models.TextField()
    name = models.TextField()


class ProjectRoles(models.Model):

    ROLE_CHOICES = (
        ('OW', 'Owner'),
        ('AD', 'Admin'),
        ('RE', 'Reviewer'),
        ('VE', 'Viewer')
    )

    project= models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=2, choices=ROLE_CHOICES)

    def __str__(self):
      return self.role

class Duplicate(models.Model):
    original = models.ForeignKey('Doc', on_delete=models.CASCADE, related_name='duplicate')
    copy = models.ForeignKey('Doc', on_delete = models.CASCADE, related_name='duplicated_by')
    project = models.ForeignKey('Project', on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

class DocProject(models.Model):

    UNRATED = 0
    YES = 1
    NO = 2
    MIXED = 3

    Relevance = (
        (UNRATED, 'Unrated'),
        (YES, 'Yes'),
        (NO, 'No'),
        (MIXED, 'Mixed'),
    )

    doc = models.ForeignKey('Doc', on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    relevant = models.IntegerField(default=0, choices=Relevance)

    class Meta:
        unique_together = ("doc","project")

class ExclusionCriteria(models.Model):
    project= models.ForeignKey('Project', on_delete=models.CASCADE)
    name = models.TextField()

class Exclusion(models.Model):
    doc = models.ForeignKey('Doc', on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    reason = models.TextField()
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    date = models.DateTimeField(auto_now_add=True)

@receiver(post_save, sender=Exclusion)
def exclude_doc(sender, instance, **kwargs):
    dp = DocProject.objects.get(
        doc=instance.doc,
        project=instance.project
    )
    dp.relevant=2
    dp.save()

@receiver(pre_delete, sender=Exclusion)
def unexclude_doc(sender,instance,**kwargs):
    dp = DocProject.objects.get(
        doc=instance.doc,
        project=instance.project
    )
    dp.relevant=0
    dos = DocOwnership.objects.filter(
        query__project=instance.project,
        doc=instance.doc
    )
    for do in dos:
        if dp.relevant == 0:
            dp.relevant=do.relevant
        elif dp.relevant != do.relevant:
            dp.relevant = 3
    dp.save()


class Query(models.Model):

    TYPE_CHOICES = (
        ('DE','Default'),
        ('SB','Snowballing Backward'),
        ('SF','Snowballing Forward'),
        ('MN','Manual Add')
    )

    DB_CHOICES = (
        ('WoS','Web of Science'),
        ('Scopus','Scopus'),
        ('intern','Internal'),
        ('pop','Publish or Perish'),
        ('ebsco', 'EBSCO'),
        ('jstor', 'JSTOR'),
    )


    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    qtype       = models.CharField(max_length=2, choices=TYPE_CHOICES, default='DE')
    type        = models.TextField(null=True, verbose_name="Query Type", default="default")
    title       = models.TextField(null=True, verbose_name="Query Title")
    text        = models.TextField(null=True, verbose_name="Query Text")
    database    = models.CharField(max_length=6,null=True, verbose_name="Query database", choices=DB_CHOICES)
    date        = models.DateTimeField(auto_now_add=True,verbose_name="Query Date")
    r_count     = models.IntegerField(null=True, verbose_name="Query Results Count")
    creator     = models.ForeignKey(User, on_delete=models.CASCADE, null=True, verbose_name="Query Creator", related_name="user_creations")
    upload_link = models.ForeignKey('EmailTokens', on_delete=models.CASCADE, null=True)
    users       = models.ManyToManyField(User)
    criteria    = models.TextField(null=True)
    #snowball    = models.IntegerField(null=True, verbose_name="Snowball ID")
    snowball    = models.ForeignKey(SnowballingSession, on_delete=models.CASCADE, null=True, verbose_name="Snowball ID")
    step        = models.IntegerField(null=True, verbose_name="Snowball steps")
    substep     = models.IntegerField(null=True, verbose_name="Snowball query substeps")
    dlstat      = models.CharField(max_length=6,null=True, verbose_name="Query download status")
    category  = models.ForeignKey('Category', on_delete=models.CASCADE, null=True)
    innovation  = models.ForeignKey('Innovation', on_delete=models.CASCADE, null=True)
    query_file = models.FileField(upload_to='queries/',null=True)
    queries = models.ManyToManyField("self",symmetrical=False)


    def __str__(self):
      return self.title

    def get_absolute_url(self):
        return reverse('scoping:doclist', kwargs={'pid':self.project.pk, 'qid': self.pk})

    def save(self, *args, **kw):
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        super(Query, self).save(*args, **kw)
        if old:
            if old.category != self.category:
                # reassign/assign category to docs
                dcs = DocCat.objects.filter(
                    doc__query=old,
                    category=old.category,
                )
                dcs.filter(user_inherited=False,user_tagged=False).delete()
                for dc in dcs.filter(user_tagged=True) | dcs.filter(user_inherited=True):
                    dc.query_tagged=False
                    dc.save()
                dcs = []
                for d in Doc.objects.filter(query=self):
                    dc, created = DocCat.objects.get_or_create(
                        doc=d,
                        category=self.category
                    )
                    dc.query_tagged=True

                pass



class Category(models.Model):
    name = models.TextField(null = True, verbose_name="Category Name")
    level = models.IntegerField(default=1)
    description = models.TextField(null=True, verbose_name="Category Description")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    ndocs = models.IntegerField(null=True)
    nqs = models.IntegerField(null=True)
    group = models.TextField(null = True, verbose_name="Broad Category Name")
    parent_category = models.ForeignKey('self', related_name='child_category',on_delete=models.CASCADE, null=True,blank=True)

    def __str__(self):
      return self.name

class DocUserCat(models.Model):
    doc = models.ForeignKey('Doc', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add=True)

class Innovation(models.Model):
    name = models.TextField(null = True, verbose_name="Innovation Name")
    description = models.TextField(null=True, verbose_name="Innovation Description")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    ndocs = models.IntegerField(null=True)
    nqs = models.IntegerField(null=True)

    def __str__(self):
      return self.name

class SBSDocCategory(models.Model):
    name        = models.TextField(null=True, verbose_name="SBS Document Category Name")
    description = models.TextField(null=True, verbose_name="SBS Document Category Description")

    def __str__(self):
      return self.name

class Tag(models.Model):
    title = models.TextField(null=True, verbose_name="Tag Title")
    text = models.TextField(null=True, verbose_name="Tag Text")
    query = models.ForeignKey('Query',null=True, on_delete=models.CASCADE, verbose_name="TagQuery")
    document_linked = models.BooleanField(default=True)

    all_docs = models.IntegerField(default=0, verbose_name="all docs")
    a_docs = models.IntegerField(default=0, verbose_name="assigned docs")
    seen_docs = models.IntegerField(default=0)
    rel_docs = models.IntegerField(default=0)
    irrel_docs = models.IntegerField(default=0)
    relevance = models.FloatField(default=0)
    users = models.IntegerField(default=0)
    cohens_kappa = models.FloatField(null=True)
    ratio = models.FloatField(null=True)


    def update_tag(self):
        users = User.objects.filter(docownership__tag=self).distinct()
        self.all_docs = self.doc_set.count()
        self.a_docs = self.docownership_set.distinct('doc_id').count()
        self.seen_docs = self.docownership_set.filter(
            relevant__gt=0
        ).distinct('doc_id').count()
        self.rel_docs = self.docownership_set.filter(
            relevant=1
        ).distinct('doc_id').count()
        self.irrel_docs = self.docownership_set.filter(
            relevant=2
        ).distinct('doc_id').count()
        try:
            self.relevance = self.rel_docs/self.seen_docs
        except:
            self.relevance = 0
        self.users = users.count()
        ## Measure scores
        ## start off with all docs
        tdocs = Doc.objects.filter(docownership__tag=self).distinct()
        scores = []
        ## Filter out those ones which have been rated by more than one person
        for u in users:
            utdocs = tdocs.filter(
                docownership__user=u,
                docownership__relevant__gt=0,
                docownership__tag=self
            ).distinct()
            if utdocs.count()>0:
                scores.append([])
                tdocs = utdocs
                u.rated=True
            else:
                u.rated=False
        i = 0
        for u in users:
            if u.rated:
                l = tdocs.filter(
                    docownership__user=u
                ).order_by('pk').values_list(
                    'docownership__relevant',flat=True
                )
                scores[i] = list(l)
                i+=1
        dscores = [None] + scores
        if len(scores) == 2:
            self.ratio = round(difflib.SequenceMatcher(*dscores).ratio(),2)
            self.cohen_kappa = cohen_kappa_score(*scores)
        else:
            self.cohen_kappa = None
            self.ratio = None
        self.save()

    def __str__(self):
      return self.title

class UserTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    a_docs = models.IntegerField(default=0, verbose_name="assigned docs")
    seen_docs = models.IntegerField(default=0)
    rel_docs = models.IntegerField(default=0)
    irrel_docs = models.IntegerField(default=0)
    relevance = models.FloatField(default=0)

    def update_usertag(self):
        dos = DocOwnership.objects.filter(
            user=self.user,
            tag=self.tag
        )
        self.a_docs = dos.count()
        self.seen_docs = dos.filter(
            relevant__gt=0
        ).count()
        self.rel_docs = dos.filter(
            relevant=1
        ).count()
        self.irrel_docs = dos.filter(
            relevant=2
        ).count()
        try:
            self.relevance = self.rel_docs/self.seen_docs
        except:
            self.relevance = 0
        self.save()
        #pass user to handle_update_tag, and update the user whose do it was. These objects will need to be created

def random_doc(q=None):
    if q is not None:
        docs = Doc.objects.filter(query=q)
    else:
        docs = Doc.objects.all()
    c = docs.count()
    return docs[randint(0,c-1)]

class DocManager(models.Manager):
    def random(self):
        count = self.aggregate(count=models.Count('UT'))['count']
        random_index = randint(0, count - 1)
        return self.all()[random_index]

class Institution(models.Model):
    name = models.TextField()
    email_ending = models.TextField()

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    type = models.TextField(null=True,default="default")
    institution = models.ForeignKey('Institution', on_delete=models.CASCADE, null=True)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class UT(models.Model):
    UT = models.CharField(max_length=30,db_index=True,primary_key=True, verbose_name='Document ID')
    sid = models.CharField(max_length=50,db_index=True,verbose_name='Scopus_id',null=True)

class DocCat(models.Model):

    doc = models.ForeignKey('Doc',on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    updated = models.DateTimeField(auto_now_add=True)
    docusercats = models.ManyToManyField('DocUserCat')

    user_inherited = models.BooleanField(default=False)
    user_tagged = models.BooleanField(default=False)
    query_tagged = models.BooleanField(default=False)

@receiver(post_save, sender=DocUserCat)
def handle_cat_doc(sender, instance, **kwargs):
    dc, created = DocCat.objects.get_or_create(
        doc=instance.doc,
        category=instance.category
    )
    dc.save()
    dc.docusercats.add(instance)

@receiver(pre_delete,sender=DocUserCat)
def handle_uncat_doc(sender, instance, **kwargs):
    dc, created = DocCat.objects.get_or_create(
        doc=instance.doc,
        category=instance.category
    )
    if created:
        dc.delete()
    if dc.docusercats.count() > 1:
        dc.docusercats.remove(instance)
    else:
        print("bla")
        if not dc.user_inherited:
            print("del")
            dc.docusercats.remove(instance)
            dc.delete()
        else:
            dc.docusercats.remove(instance)
            dc.user_tagged=False
            dc.save()


class Doc(models.Model):
    random = DocManager

    DTYPE_CHOICES = (
        ('AR','Article'),
        ('RE','Review'),
        ('BC','Book Chapter'),
        ('BK','Book'),
        ('WP','Working Paper')
    )

    DTYPE_CHOICES = (
        ('AR','Article'),
        #('RE','Review'),
        ('RP', 'Report'),
        ('BC','Book Chapter'),
        ('BK','Book'),
        ('WP','Working Paper')
    )

    UT = models.OneToOneField(UT, on_delete=models.CASCADE)
    url = models.URLField(null=True, max_length=500)
    dtype = models.CharField(
        max_length=2,
        null=True,
        choices = DTYPE_CHOICES,
        verbose_name = "Document Type",
        help_text = "Tell us what type of document you are adding"
    )

    #UT = models.CharField(max_length=30,db_index=True,primary_key=True, verbose_name='Document ID')
    query = models.ManyToManyField('Query')
    tag = models.ManyToManyField('Tag')
    title = models.TextField(null=True)
    alternative_titles = ArrayField(models.TextField(), null=True)
    tilength = models.IntegerField(null=True)
    content = models.TextField(null=True)
    fulltext = models.TextField(null=True)
    PY = models.IntegerField(null=True,db_index=True)
    first_author = models.TextField(null=True, verbose_name='First Author')
    authors = models.TextField(null=True, verbose_name='All Authors')
    users = models.ManyToManyField(User, through='DocOwnership')
    journal = models.ForeignKey('JournalAbbrev', on_delete=models.CASCADE, null=True)

    category = models.ManyToManyField('Category',db_index=True, through='DocCat')
    innovation = models.ManyToManyField('Innovation',db_index=True)
    sbscategory = models.ManyToManyField('SBSDocCategory')
    source = models.TextField(null=True)
    wos = models.BooleanField(default=False)
    scopus = models.BooleanField(default=False)
    uploaded = models.BooleanField(default=False)

    uploader = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="uploaded_docs", verbose_name="Uploader")
    date = models.DateTimeField(null=True)
    ymentions = ArrayField(models.IntegerField(),null=True)
    cities = models.ManyToManyField('cities.City')

    citation_objects = models.BooleanField(default=False,db_index=True)

    duplicated = models.BooleanField(default=False)
    relevant = models.BooleanField(default=False)
    projects = models.ManyToManyField(Project, through='DocProject')

    #primary_topic = models.ManyToManyField('tmv_app.Topic', on_delete=models.SET_NULL)

    def __str__(self):

      return self.UT.UT

    def authorlist(self):
        das = self.docauthinst_set.order_by('AU','position').distinct('AU').values_list('id',flat=True)
        unique = self.docauthinst_set.filter(id__in=das).order_by('position')
        return unique

    def citation(self):
        used = set()
        das = self.docauthinst_set.order_by('AU','position').distinct('AU').values_list('id',flat=True)
        unique = self.docauthinst_set.filter(id__in=das).order_by('position').values_list('AU',flat=True)
        return ", ".join(unique) + ' (' + str(self.PY) + ') ' + self.title

    def ti_word_count(self):
        return len(str(self.title).split())

    def word_count(self):
        return len(str(self.content).split())

    def shingle(self):
        return set(s for s in ngrams(self.title.lower().split(),2))

    def find_duplicates(self,ids,j_thresh,limit_y=False):
        comparison_docs = Doc.objects.filter(id__in=ids)
        if limit_y:
            comparison_docs = comparison_docs.filter(PY=self.PY)
        for d in comparison_docs:
            j = utils.jaccard(self.shingle(),d.shingle())
            if j > j_thresh:
                return (d,j)
        return (False, 0)

    def reassign_doc(self, doc):
        '''When there's a duplicate, merge all info and put the doc into an archive '''

        return

    def highlight_fields(self,q,fields):
        if q is not None:
            if q.__class__ == scoping.models.Project:
                qs = q.query_set.exclude(database="intern")
            elif q.queries.exists():
                qs = []
                for q1 in q.queries.all():
                    if q1.queries.exists():
                        for q2 in q1.queries.all():
                            if q2.queries.exists():
                                for q3 in q2.queries.all():
                                    qs.append(q3)
                            else:
                                qs.append(q2)
                    else:
                        qs.append(q1)
            else:
                qs = [q]
            words = utils.get_query_words(qs)
        else:
            words = set()
        d = {}
        for f in fields:
            doc = self
            for fpart in f.split("__"):
                doc = getattr(doc,fpart)
            s = doc
            if isinstance(s,str):
                d[f] = ""
                if f=="wosarticle__di":
                    if s in words:
                        s = '<span class="t1">{}</span>'.format(s)
                else:
                    for w in sorted(list(words),key=len, reverse=True):
                        #s = re.sub(w,'<span class="t1">{}</span>'.format(w),s)
                        s = utils.ihighlight(w,s)
            d[f] = s
        d["authors"] = list(self.docauthinst_set.order_by('position').values())
        for a in d["authors"]:
            for w in sorted(list(words),key=len, reverse=True):
                a["institution"] = utils.ihighlight(w,a["institution"])



        return d
    def delete(self, *args, **kwargs):
        self.UT.delete()
        return super(self.__class__, self).delete(*args, **kwargs)

class DocSection(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    title = models.TextField()
    n = models.IntegerField()

class DocPar(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    text = models.TextField()
    n = models.IntegerField()
    section = models.ForeignKey(DocSection, on_delete=models.CASCADE, null=True)
    tag = models.ManyToManyField(Tag)
    category = models.ManyToManyField('Category',db_index=True)

    # xml paragraph properties
    endColor = models.CharField(null=True, max_length=50)
    endFont = models.CharField(null=True, max_length=50)
    endFontsize = models.FloatField(null=True)
    maxX = models.FloatField(null=True)
    maxY = models.FloatField(null=True)
    minX = models.FloatField(null=True)
    minY = models.FloatField(null=True)
    mostCommonColor = models.CharField(null=True, max_length=50)
    mostCommonFont = models.CharField(null=True, max_length=50)
    mostCommonFontsize = models.FloatField(null=True)
    page = models.IntegerField(null=True)
    role = models.CharField(null=True, max_length=50)
    imputed_role = models.CharField(null=True, max_length=50)
    startColor = models.CharField(null=True, max_length=50)
    startFont = models.CharField(null=True, max_length=50)
    startFontsize = models.FloatField(null=True)
    height = models.FloatField(null=True)
    width = models.FloatField(null=True)
    text_length = models.IntegerField(null=True)

class DocStatement(models.Model):
    par = models.ForeignKey(DocPar, on_delete=models.CASCADE, null=True)
    text = models.TextField()
    start = models.IntegerField(null=False)
    end = models.IntegerField(null=False)
    category = models.ManyToManyField('Category',db_index=True)
    text_length = models.IntegerField(null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

class DocFile(models.Model):
    doc = models.OneToOneField(Doc, on_delete=models.CASCADE)
    file = models.FileField(validators=[validate_pdf])


@receiver(models.signals.post_delete, sender=DocFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `MediaFile` object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)

class Bigram(models.Model):
    stem1 = models.TextField(db_index=True)
    word1 = models.TextField()
    word2 = models.TextField()
    stem2 = models.TextField()
    pos = models.IntegerField(db_index=True)

class DocBigram(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE )
    bigram = models.ForeignKey(Bigram, on_delete=models.CASCADE)
    n = models.IntegerField(null=True)

class Network(models.Model):
    title = models.TextField(unique=True)
    type = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    query = models.ForeignKey(Query, on_delete=models.CASCADE)

class NetworkProperties(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    value = models.IntegerField(null=True)
    fvalue = models.FloatField(null=True)

class Citation(models.Model):
    au = models.TextField(null=True)
    py = models.IntegerField(null=True)
    so = models.TextField(null=True)
    vl = models.IntegerField(null=True)
    bp = models.IntegerField(null=True)
    doi = models.TextField(null=True,unique=True,db_index=True)
    ftext = models.TextField(db_index=True)
    alt_text = ArrayField(models.TextField(),null=True)
    ## Link the citation to the document it refers to if possible
    referent = models.ForeignKey(Doc, on_delete=models.CASCADE, null=True)
    docmatches = models.IntegerField(null=True)

class JournalAbbrev(models.Model):
    fulltext = models.TextField(unique=True,db_index=True)
    abbrev = models.TextField(unique=True,null=True)

class CDO(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    citation = models.ForeignKey(Citation, on_delete=models.CASCADE)

class BibCouple(models.Model):
    doc1 = models.ForeignKey(Doc, on_delete=models.CASCADE, related_name="node1")
    doc2 = models.ForeignKey(Doc, on_delete=models.CASCADE, related_name="node2")
    cocites = models.IntegerField(default=0)

class AR(models.Model):
    ar = models.IntegerField(unique=True)
    start = models.IntegerField(null=True)
    end = models.IntegerField(null=True)
    name = models.TextField(null=True)

    def __str__(self):
      return str(self.ar)

class WG(models.Model):
    ar = models.ForeignKey(AR, on_delete=models.CASCADE)
    wg = models.IntegerField()

    def __str__(self):
      return "AR"+str(self.ar)+" WG"+str(self.wg)

class IPCCRef(models.Model):
    authors = models.TextField()
    year = models.IntegerField()
    text = models.TextField()
    words = ArrayField(models.TextField(),null=True)
    ar = models.ManyToManyField('AR')
    wg = models.ManyToManyField('WG')
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE, null=True)
    chapter = models.TextField(null=True)

    def shingle(self):
        return set(s for s in ngrams(self.text.lower().split(".")[0].split(),2))

class KW(models.Model):
    kwtype_choices = (
        (0,'author'), # wosarticle.de
        (1,'auto_wos'), # wosarticle.kwp
    )
    text = models.TextField(db_index=True)
    doc = models.ManyToManyField(Doc)
    ndocs = models.IntegerField(default=0)
    kwtype = models.IntegerField(choices=kwtype_choices,null=True)

class WC(models.Model):
    text = models.TextField()
    doc = models.ManyToManyField(Doc)
    oecd = models.TextField(null=True)
    oecd_fos = models.TextField(null=True)
    oecd_fos_text = models.TextField(null=True)

class EmailTokens(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE ,null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    email = models.TextField()
    AU = models.TextField()
    docset = models.TextField(null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    id = models.UUIDField(primary_key=True,default=uuid.uuid4)
    sent = models.BooleanField(default=False)
    sent_other_tech = models.BooleanField(default=False)
    sent_other_project = models.BooleanField(default=False)
    clicked = models.IntegerField(default=0)
    valid_docs = models.IntegerField(default=0)

#    class Meta:
#        unique_together = ["email","AU"]
#        index_together = ["email","AU"]

class URLs(models.Model):
    url = models.TextField(unique=True,db_index=True)

class DocRel(models.Model):
    seed = models.ForeignKey(Doc, on_delete=models.CASCADE, related_name="parent")
    seedquery = models.ForeignKey(Query, on_delete=models.CASCADE, null=True)
    relation = models.IntegerField()
    text = models.TextField(null=True)
    title = models.TextField(null=True)
    au = models.TextField(null=True)
    PY = models.IntegerField(null=True)
    journal =  models.TextField(null=True)
    link = models.TextField(null=True)
    url = models.TextField(null=True)
    doi = models.TextField(null=True)
    hasdoi = models.BooleanField(default=False)
    docmatch_q = models.BooleanField(default=False)
    timatch_q = models.BooleanField(default=False)
    indb = models.IntegerField(null=True,default=0)
    sametech = models.IntegerField(null=True,default=0)
    referent = models.ForeignKey(Doc, on_delete=models.CASCADE, null=True, related_name="document")

    def shingle(self):
        return set(s for s in ngrams(self.title.lower().split(),2))

    class Meta:
        unique_together = ('seed', 'seedquery', 'text',)

class NoteManager(models.Manager):
    def prelevant(self,pid):
        pn = list(self.model.objects.filter(
            project__id=pid
        ).values_list('pk',flat=True))
        tn = list(self.model.objects.filter(
            tag__query__project__id=pid
        ).values_list('pk',flat=True))
        return self.model.objects.filter(pk__in=set(pn+tn))

class Note(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE,null=True)
    par = models.ForeignKey(DocPar, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Notemaker")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    objects = NoteManager()
    date = models.DateTimeField(auto_now_add=True)
    text = models.TextField(null=True)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, null=True)
    class Meta:
        ordering = ['date']

    def __str__(self):
      return self.text



class DocOwnership(models.Model):

    UNRATED = 0
    YES = 1
    NO = 2
    MAYBE = 3
    OTHERTECH = 4
    YESYES = 5
    YESNO = 6
    NOYES = 7
    NONO = 8
    BADLYPARSED = 9

    Status = (
        (UNRATED, 'Unrated'),
        (YES, 'Yes'),
        (NO, 'No'),
        (MAYBE, 'Maybe'),
        (OTHERTECH, 'Other Category'),
        (YESYES, 'Tech Relevant & Innovation Relevant'),
        (YESNO, 'Tech Relevant & Innovation Irrelevant'),
        (NOYES, 'Tech Irrelevant & Innovation Relevant'),
        (NONO, 'Tech Irrelevant & Innovation Irrelevant'),
        (BADLYPARSED, 'Badly Parsed')
    )

    doc = models.ForeignKey(Doc, on_delete=models.CASCADE, null=True)
    docpar = models.ForeignKey(DocPar, on_delete=models.CASCADE, null=True)
    document_linked = models.BooleanField(default=True)
    title_only = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Reviewer")
    query = models.ForeignKey(Query, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, null=True)
    order = models.IntegerField(null=True)
    relevant = models.IntegerField(
        choices=Status,
        default=0,
        db_index=True,
        verbose_name="Relevance"
    )
    date     = models.DateTimeField(null=True,default=timezone.now,verbose_name="Rating Date")
    start = models.DateTimeField(null=True,verbose_name="Rating Date")
    finish = models.DateTimeField(null=True,verbose_name="Rating Date")

@receiver(post_save, sender=DocOwnership)
def docownership_update(sender, instance, **kwargs):
    if instance.relevant > 0:
        from scoping.tasks import handle_update_tag
        transaction.on_commit(lambda: current_app.send_task('scoping.tasks.handle_update_tag', args=(instance.tag.pk,)))

def create_docproj(sender,instance,**kwargs):
    #print("fired!")
    pk_set = kwargs['pk_set']
    if kwargs['action'] != "post_add":
        return
    if len(pk_set) == 0:
        return
    q = Query.objects.get(pk=list(pk_set)[0])
    d = instance
    dp, created = DocProject.objects.get_or_create(
        doc=d,project=q.project
    )

m2m_changed.connect(create_docproj,sender=Doc.query.through)

@receiver(post_save, sender=DocOwnership)
def update_docproj(sender, instance, **kwargs):
    p = instance.query.project
    if instance.doc is not None:
        d = instance.doc
    else:
        d = instance.docpar.doc
    if d is None:
        print(instance.id)
    if p is None:
        return
    dp, created = DocProject.objects.get_or_create(project=p,doc=d)
    if dp.relevant == 0:
        dp.relevant=instance.relevant
        dp.save()
    elif dp.relevant != instance.relevant:
        dp.relevant = 3
        dp.save()


class DocAuthInst(models.Model):
    doc = models.ForeignKey('Doc', on_delete=models.CASCADE,null=True, verbose_name="Author - Document")
    surname = models.CharField(max_length=90, null=True)
    initials = models.CharField(max_length=10, null=True)
    AU = models.CharField(max_length=90, db_index=True, null=True, verbose_name="Author")
    AF = models.CharField(max_length=90, db_index=True, null=True, verbose_name="Author Full Name")
    institution = models.TextField(db_index=True, verbose_name="Institution Name")
    position = models.IntegerField(verbose_name="Author Position")

    class Meta:
        unique_together = ('doc', 'AU','AF','institution','position')

    def __str__(self):
        return self.AU

    def save(self, *args, **kwargs):
        if self.surname and self.initials:
            self.AU = self.surname + ", " + self.initials
        super(DocAuthInst, self).save(*args, **kwargs)

# A simple form of the table below, just to store the dois as we parse them

class DocReferences(models.Model):
    doc = models.ForeignKey('Doc', on_delete=models.CASCADE,null=True)
    refdoi = models.CharField(null=True, max_length=150, verbose_name="DOI")
    refall = models.TextField(null=True, verbose_name="All reference information") #in case we want to use this later...

    def __str__(self):
      return self.doc

#class DocCites(models.Model):
#    doc = models.ForeignKey('Doc',null=True, related_name='doc')
#    reference = models.ForeignKey('Doc',null=True, related_name='ref')

##############################################
## Article holds more WoS type information for each doc
class WoSArticleManager(models.Manager):
    def get_by_natural_key(self, first_name, last_name):
        return self.get(first_name=first_name, last_name=last_name)

class WoSArticle(models.Model):
    doc = models.OneToOneField(
        'Doc',
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name='Document ID'
    )

    ts = models.TextField(null=True, verbose_name="Title Abstract Keyword")

    pt = models.CharField(null=True, max_length=50, verbose_name="Publication Type") # pub type
    ti = models.TextField(null=True, verbose_name="Title")
    ab = models.TextField(null=True, verbose_name="Abstract")
    py = models.IntegerField(null=True, verbose_name="Year")
    ar = models.CharField(null=True, max_length=100, verbose_name="Article Number") # Article number
    bn = models.CharField(null=True, max_length=100, verbose_name="ISBN") # ISBN
    bp = models.CharField(null=True, max_length=50, verbose_name="Beginning Page") # beginning page
    c1 = models.TextField(null=True, verbose_name="Author Address") # author address
    cl = models.TextField(null=True, verbose_name="Conference Location") # conf location
    cr = ArrayField(models.TextField(), verbose_name="Cited References", null=True)
    cr_scopus = ArrayField(models.TextField(), verbose_name="Cited References", null=True)
    ct = models.TextField(null=True, verbose_name="Conference Title") # conf title
    de = models.TextField(null=True, verbose_name="Author Keywords") # keywords - separate table?
    di = models.CharField(null=True, db_index=True, max_length=250, verbose_name="DOI") # DOI
    dt = models.CharField(null=True, max_length=50, verbose_name="Document Type") # doctype
    em = models.TextField(null=True, verbose_name="E-mail Address",db_index=True) #email
    ep = models.CharField(null=True, max_length=50, verbose_name="Ending Page") # last page
    fn = models.CharField(null=True, max_length=250, verbose_name="File Name") # filename?
    fu = models.TextField(null=True, verbose_name="Funding Agency and Grant Number") #funding agency + grant number
    fx = models.TextField(null=True, verbose_name="Funding Text") # funding text
    ga = models.CharField(null=True, max_length=100, verbose_name="Document Delivery Number") # document delivery number
    ho = models.TextField(null=True, verbose_name="Conference Host") # conference host
    #ID = models.TextField() # keywords plus ??
    iss = models.CharField(null=True, max_length=100, verbose_name="Issue")
    ad = models.TextField(null=True, verbose_name="Institution (unlinked to author")
    kwp = models.TextField(null=True, verbose_name="Keywords Plus")
    j9 = models.CharField(null=True, max_length=30, verbose_name="29-Character Source Abbreviation") # 29 char source abbreviation
    ji = models.CharField(null=True, max_length=100, verbose_name="ISO Source Abbreviation") # ISO source abbrev
    la = models.CharField(null=True, max_length=100, verbose_name="Language") # Language
    nr = models.IntegerField(null=True, verbose_name="Cited Reference Count") # number of references
    pa = models.TextField(null=True, verbose_name="Publisher Address") # pub address
    pd = models.CharField(null=True, max_length=50, verbose_name="Publication Date") # pub month
    pg = models.IntegerField(null=True, verbose_name="Page Count") # page count
    pi = models.TextField(null=True, verbose_name="Publisher City") # pub city
    pu = models.TextField(null=True, verbose_name="Publisher") # publisher
    rp = models.TextField(null=True, verbose_name="Reprint Address") # reprint address
    sc = models.TextField(null=True, verbose_name="Subject Category") # subj category
    se = models.TextField(null=True, verbose_name="Book Series Title") # book series title
    si = models.TextField(null=True, verbose_name="Special Issue") # special issue
    sn = models.CharField(null=True, max_length=80, verbose_name="ISSN") # ISSN
    so = models.TextField(
        null=True,
        #max_length=250,
        verbose_name="Publication Name",
        help_text="Enter the name of the journal or the title of the book"
    ) # publication name
    sp = models.TextField(null=True, verbose_name="Conference Sponsors") # conf sponsors
    su = models.TextField(null=True, verbose_name="Supplement") # supplement
    tc = models.IntegerField(null=True, verbose_name="Times Cited") # times cited
    vl = models.CharField(null=True, max_length=50, verbose_name="Volume")
    wc = ArrayField(models.TextField(),null=True, verbose_name="Web of Science Category")

    def __str__(self):
      return self.ti
