from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from nltk import ngrams
from django.contrib.postgres.fields import ArrayField
import uuid
from random import randint
import cities
from django.db.models.signals import post_save
from django.dispatch import receiver
import tmv_app
import uuid
import os

from .validators import *
# Create your models here.

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
    technology     = models.ForeignKey('Technology', null=True)

    def __str__(self):
      return self.name

class Project(models.Model):

    ROLE_CHOICES = (
        ('OW', 'Owner'),
        ('AD', 'Admin'),
        ('RE', 'Reviewer'),
        ('VE', 'Viewer')
    )

    title = models.TextField(null=True)
    description = models.TextField(null=True)
    users = models.ManyToManyField(User, through='ProjectRoles')
    queries = models.IntegerField(default=0)
    docs = models.IntegerField(default=0)
    tms = models.IntegerField(default=0)
    role = models.CharField(max_length=2, choices=ROLE_CHOICES, null=True)

    def __str__(self):
      return self.title

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


class DocProject(models.Model):
    doc = models.ForeignKey('Doc', on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    relevant = models.BooleanField(default=False)

class Query(models.Model):

    TYPE_CHOICES = (
        ('DE','Default'),
        ('SB','Snowballing Backward'),
        ('SF','Snowballing Forward'),
        ('MN','Manual Add')
    )

    project = models.ForeignKey(Project, null=True)
    qtype       = models.CharField(max_length=2, choices=TYPE_CHOICES, default='DE')
    type        = models.TextField(null=True, verbose_name="Query Type", default="default")
    title       = models.TextField(null=True, verbose_name="Query Title")
    text        = models.TextField(null=True, verbose_name="Query Text")
    database    = models.CharField(max_length=6,null=True, verbose_name="Query database")
    date        = models.DateTimeField(auto_now_add=True,verbose_name="Query Date")
    r_count     = models.IntegerField(null=True, verbose_name="Query Results Count")
    creator     = models.ForeignKey(User,null=True, verbose_name="Query Creator", related_name="user_creations")
    upload_link = models.ForeignKey('EmailTokens', null=True)
    users       = models.ManyToManyField(User)
    criteria    = models.TextField(null=True)
    #snowball    = models.IntegerField(null=True, verbose_name="Snowball ID")
    snowball    = models.ForeignKey(SnowballingSession, null=True, verbose_name="Snowball ID")
    step        = models.IntegerField(null=True, verbose_name="Snowball steps")
    substep     = models.IntegerField(null=True, verbose_name="Snowball query substeps")
    dlstat      = models.CharField(max_length=6,null=True, verbose_name="Query download status")
    technology  = models.ForeignKey('Technology', null=True)
    innovation  = models.ForeignKey('Innovation', null=True)

    def __str__(self):
      return self.title





class Technology(models.Model):
    name = models.TextField(null = True, verbose_name="Technology Name")
    description = models.TextField(null=True, verbose_name="Technology Description")
    project = models.ForeignKey(Project, null=True)
    ndocs = models.IntegerField(null=True)
    nqs = models.IntegerField(null=True)

    def __str__(self):
      return self.name

class Innovation(models.Model):
    name = models.TextField(null = True, verbose_name="Innovation Name")
    description = models.TextField(null=True, verbose_name="Innovation Description")

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
    query = models.ForeignKey('Query',null=True, verbose_name="TagQuery")

    def __str__(self):
      return self.title

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

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    type = models.TextField(null=True,default="default")

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class UT(models.Model):
    UT = models.CharField(max_length=30,db_index=True,primary_key=True, verbose_name='Document ID')

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

    UT = models.OneToOneField(UT)
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
    tilength = models.IntegerField(null=True)
    content = models.TextField(null=True)
    PY = models.IntegerField(null=True,db_index=True)
    first_author = models.TextField(null=True, verbose_name='First Author')
    authors = models.TextField(null=True, verbose_name='All Authors')
    users = models.ManyToManyField(User, through='DocOwnership')
    journal = models.ForeignKey('JournalAbbrev',null=True)

    technology = models.ManyToManyField('Technology',db_index=True)
    innovation = models.ManyToManyField('Innovation',db_index=True)
    category = models.ManyToManyField('SBSDocCategory')
    source = models.TextField(null=True)
    wos = models.BooleanField(default=False)
    scopus = models.BooleanField(default=False)
    uploader = models.ForeignKey(User, null=True, related_name="uploaded_docs", on_delete=models.CASCADE, verbose_name="Uploader")
    date = models.DateTimeField(null=True)
    ymentions = ArrayField(models.IntegerField(),null=True)
    cities = models.ManyToManyField('cities.City')

    citation_objects = models.BooleanField(default=False,db_index=True)

    duplicated = models.BooleanField(default=False)
    relevant = models.BooleanField(default=False)
    projects = models.ManyToManyField(Project, through='DocProject')

    primary_topic = models.ManyToManyField('tmv_app.Topic')

    def __str__(self):

      return self.UT.UT


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


class DocFile(models.Model):
    doc = models.OneToOneField(Doc)
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
    doc = models.ForeignKey(Doc)
    bigram = models.ForeignKey(Bigram)
    n = models.IntegerField(null=True)

class Network(models.Model):
    title = models.TextField(unique=True)
    type = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    query = models.ForeignKey(Query)


class NetworkProperties(models.Model):
    doc = models.ForeignKey(Doc)
    network = models.ForeignKey(Network)
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
    referent = models.ForeignKey(Doc, null=True)
    docmatches = models.IntegerField(null=True)

class JournalAbbrev(models.Model):
    fulltext = models.TextField(unique=True,db_index=True)
    abbrev = models.TextField(unique=True,null=True)


class CDO(models.Model):
    doc = models.ForeignKey(Doc)
    citation = models.ForeignKey(Citation)




class BibCouple(models.Model):
    doc1 = models.ForeignKey(Doc, related_name="node1")
    doc2 = models.ForeignKey(Doc, related_name="node2")
    cocites = models.IntegerField(default=0)


class AR(models.Model):
    ar = models.IntegerField(unique=True)
    start = models.IntegerField(null=True)
    end = models.IntegerField(null=True)
    name = models.TextField(null=True)

    def __str__(self):
      return str(self.ar)

class WG(models.Model):
    ar = models.ForeignKey(AR)
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
    doc = models.ForeignKey(Doc,null=True)
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
    category = models.ForeignKey(Technology,null=True)
    email = models.TextField()
    AU = models.TextField()
    docset = models.TextField(null=True)
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
    referent = models.ForeignKey(Doc, null=True, on_delete=models.CASCADE, related_name="document")

    def shingle(self):
        return set(s for s in ngrams(self.title.lower().split(),2))

    class Meta:
        unique_together = ('seed', 'seedquery', 'text',)



class Note(models.Model):
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Notemaker")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    date = models.DateTimeField()
    text = models.TextField(null=True)
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

    Status = (
        (UNRATED, 'Unrated'),
        (YES, 'Yes'),
        (NO, 'No'),
        (MAYBE, 'Maybe'),
        (OTHERTECH, 'Other Technology'),
        (YESYES, 'Tech Relevant & Innovation Relevant'),
        (YESNO, 'Tech Relevant & Innovation Irrelevant'),
        (NOYES, 'Tech Irrelevant & Innovation Relevant'),
        (NONO, 'Tech Irrelevant & Innovation Irrelevant'),
    )

    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Reviewer")
    query = models.ForeignKey(Query, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, null=True)
    relevant = models.IntegerField(
        choices=Status,
        default=0,
        db_index=True,
        verbose_name="Relevance"
    )
    date     = models.DateTimeField(null=True,default=timezone.now,verbose_name="Rating Date")



class DocAuthInst(models.Model):
    doc = models.ForeignKey('Doc',null=True, verbose_name="Author - Document")
    surname = models.CharField(max_length=60, null=True)
    initials = models.CharField(max_length=10, null=True)
    AU = models.CharField(max_length=60, db_index=True, null=True, verbose_name="Author")
    AF = models.CharField(max_length=60, db_index=True, null=True, verbose_name="Author Full Name")
    institution = models.CharField(max_length=250, db_index=True, verbose_name="Institution Name")
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
    doc = models.ForeignKey('Doc',null=True)
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
    so = models.CharField(
        null=True,
        max_length=250,
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
