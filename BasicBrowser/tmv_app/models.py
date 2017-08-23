from django.db import models
from django.contrib.postgres.fields import ArrayField
import scoping

#################################################
## Below are some special model variants for hlda
## method

class HTopic(models.Model):
    topic = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', null=True)
    title = models.CharField(max_length=80, null=True)
    n_docs = models.IntegerField(null=True)
    n_words = models.IntegerField(null=True)
    scale = models.FloatField(null=True)
    run_id = models.IntegerField(null=True, db_index=True)

class HTopicTerm(models.Model):
    topic = models.ForeignKey('HTopic')
    term = models.ForeignKey('Term')
    count = models.IntegerField()
    run_id = models.IntegerField(null=True, db_index=True)

class HDocTopic(models.Model):
    #doc = models.ForeignKey('Doc')
    doc = models.ForeignKey('scoping.Doc', null=True)
    topic = models.ForeignKey('HTopic')
    level = models.SmallIntegerField()
    score = models.FloatField(null=True)
    run_id = models.IntegerField(null=True, db_index=True)




#################################################
## Topic, Term and Doc are the three primary models
class Topic(models.Model):
    title = models.CharField(max_length=80)
    score = models.FloatField(null=True)
    size = models.IntegerField(null=True)
    growth = models.FloatField(null=True)
    run_id = models.ForeignKey('RunStats',db_index=True)
    year = models.IntegerField(null=True)
    primary_dtopic = models.ManyToManyField('DynamicTopic')
    top_words = ArrayField(models.TextField(),null=True)

    def __unicode__(self):
        return str(self.title)

class DynamicTopic(models.Model):
    title = models.CharField(null=True, max_length=80)
    score = models.FloatField(null=True)
    size = models.IntegerField(null=True)
    run_id = models.ForeignKey('RunStats',db_index=True)
    top_words = ArrayField(models.TextField(),null=True)
    l5ys = models.FloatField(null=True)
    l1ys = models.FloatField(null=True)

    def __unicode__(self):
        return str(self.title)

class TopicDTopic(models.Model):
    topic = models.ForeignKey('Topic', null=True)
    dynamictopic = models.ForeignKey('DynamicTopic',null=True)
    score = models.FloatField(null=True)

class TopicCorr(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    topiccorr = models.ForeignKey('Topic',null=True, related_name='Topiccorr')
    score = models.FloatField(null=True)
    ar = models.IntegerField(default=-1)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)

class Term(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    run_id = models.ManyToManyField('RunStats')

    def __unicode__(self):
        return str(self.title)

#################################################
## Docs are all in scoping now!

#################################################
## TopicYear holds per year topic totals
class TopicYear(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    PY = models.IntegerField()
    score = models.FloatField()
    year_share = models.FloatField(null=True)
    count = models.FloatField()
    run_id = models.IntegerField(db_index=True)

#################################################
## TopicYear holds per year topic totals
class DynamicTopicYear(models.Model):
    topic = models.ForeignKey('DynamicTopic',null=True)
    PY = models.IntegerField()
    score = models.FloatField(null=True)
    count = models.FloatField(null=True)
    year_share = models.FloatField(null=True)
    run_id = models.IntegerField(db_index=True)

class TopicARScores(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    ar = models.ForeignKey('scoping.AR',null=True)
    score = models.FloatField(null=True)

#################################################
## Separate topicyear for htopic
class HTopicYear(models.Model):
    topic = models.ForeignKey('HTopic',null=True)
    PY = models.IntegerField()
    score = models.FloatField()
    count = models.FloatField()
    run_id = models.IntegerField(db_index=True)

#################################################
## DocTopic and TopicTerm map contain topic scores
## for docs and topics respectively

class DocTopic(models.Model):
    #doc = models.ForeignKey(Doc, null=True)
    doc = models.ForeignKey('scoping.Doc', null=True)
    topic = models.ForeignKey('Topic',null=True)
    score = models.FloatField()
    scaled_score = models.FloatField()
    run_id = models.IntegerField(db_index=True)

class TopicTerm(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    term = models.ForeignKey('Term',null=True)
    PY = models.IntegerField(db_index=True,null=True)
    score = models.FloatField()
    run_id = models.IntegerField(db_index=True)

class DynamicTopicTerm(models.Model):
    topic = models.ForeignKey('DynamicTopic', null=True)
    term = models.ForeignKey('Term', null=True)
    PY = models.IntegerField(db_index=True, null=True)
    score = models.FloatField()
    run_id = models.IntegerField(db_index=True)



#################################################
## Not sure what this does???????? not actually used,
## but should it be? Yes this is useful
class DocTerm(models.Model):
    doc = models.IntegerField()
    term = models.IntegerField()
    score = models.FloatField()

#################################################
## RunStats and Settings....
class RunStats(models.Model):
    run_id = models.IntegerField(primary_key=True)
    parent_run_id = models.IntegerField(null=True)
    query = models.ForeignKey('scoping.Query', null=True)
    start = models.DateTimeField()
    batch_count = models.IntegerField()
    last_update = models.DateTimeField()
    topic_titles_current = models.NullBooleanField()
    topic_scores_current = models.NullBooleanField()
    topic_year_scores_current = models.NullBooleanField()
    docs_seen = models.IntegerField(null=True)
    notes = models.TextField(null=True)
    LDA = 'LD'
    HLDA = 'HL'
    DTM = 'DT'
    NMF = 'NM'
    BDT = 'BD'
    METHOD_CHOICES = (
        (LDA, 'lda'),
        (HLDA, 'hlda'),
        (DTM, 'dtm'),
        (NMF,'nmf'),
        (BDT,'BleiDTM')
    )
    method = models.CharField(
        max_length=2,
        choices=METHOD_CHOICES,
        default=LDA,
    )
    error = models.FloatField(null=True, default = 0)
    errortype = models.TextField(null=True)
    iterations = models.IntegerField(null=True)
    max_features = models.IntegerField(null=True)
    max_topics = models.IntegerField(null=True)
    ngram = models.IntegerField(null=True)
    term_count = models.IntegerField(null=True)
    dthreshold = models.FloatField(null=True)

class Settings(models.Model):
    run_id = models.IntegerField()
    doc_topic_score_threshold = models.FloatField()
    doc_topic_scaled_score = models.BooleanField()
