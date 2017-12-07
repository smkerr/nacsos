from django.db import models
from django.contrib.postgres.fields import ArrayField
import scoping

class MinMaxFloat(models.FloatField):
    def __init__(self, min_value=None, max_value=None, *args, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        super(MinMaxFloat, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value' : self.max_value}
        defaults.update(kwargs)
        return super(MinMaxFloat, self).formfield(**defaults)

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


#################################################
## Topic, Term and Doc are the three primary models
class Topic(models.Model):
    title = models.CharField(max_length=80)
    score = models.FloatField(null=True)
    size = models.IntegerField(null=True)
    growth = models.FloatField(null=True)
    run_id = models.ForeignKey('RunStats',db_index=True)
    year = models.IntegerField(null=True)
    period = models.ForeignKey('TimePeriod',null=True)
    primary_dtopic = models.ManyToManyField('DynamicTopic')
    top_words = ArrayField(models.TextField(),null=True)
    primary_wg = models.IntegerField(null=True)
    wg_prop = models.FloatField(null=True)
    ipcc_coverage = models.FloatField(null=True)

    wg_1 = models.FloatField(null=True)
    wg_2 = models.FloatField(null=True)
    wg_3 = models.FloatField(null=True)


    def __unicode__(self):
        return str(self.title)


    def __str__(self):
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


    def __str__(self):
        return str(self.title)

class TimePeriod(models.Model):
    title = models.CharField(null=True, max_length=80)
    n = models.IntegerField()
    ys = ArrayField(models.IntegerField())

class TimeDocTotal(models.Model):
    period = models.ForeignKey(TimePeriod)
    run = models.ForeignKey('RunStats')
    n_docs = models.IntegerField(null=True)
    dt_score = models.FloatField(null=True)

class TimeDTopic(models.Model):
    period = models.ForeignKey(TimePeriod)
    dtopic = models.ForeignKey('DynamicTopic')
    score = models.FloatField(null=True)


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
    score = models.FloatField(null=True)
    year_share = models.FloatField(null=True)
    count = models.FloatField(null=True)
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
    share = models.FloatField(null=True)
    pgrowth = models.FloatField(null=True)
    pgrowthn = models.FloatField(null=True)


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
    run_id = models.AutoField(primary_key=True)

    ##Inputs

    max_features = models.IntegerField(default=0, help_text = 'Maximum number of terms')
    min_freq = models.IntegerField(default=1, help_text = 'Minimum frequency of terms')
    max_df = MinMaxFloat(default=0.95, min_value=0.0, max_value=1.0)
    limit = models.IntegerField(null=True, default=0, help_text='Limit model to first x documents (leave as zero for no limit)')
    ngram = models.IntegerField(null=True, default=1, help_text='Length of feature n_gram')
    db = models.BooleanField(default=True, help_text='Record the results into the database? Or just run the model and record statistics?')

    K = models.IntegerField(null=True, help_text='Number of topics')
    alpha = models.FloatField(null=True, default=0.01, help_text='Alpha parameter')
    max_iterations  = models.IntegerField(null=True, default=200, help_text='Maximum iterations')

    query = models.ForeignKey('scoping.Query', null=True)


    ## Progress
    process_id = models.IntegerField(null=True)
    start = models.DateTimeField(auto_now_add=True)
    batch_count = models.IntegerField(default=0)
    last_update = models.DateTimeField(auto_now_add=True)
    topic_titles_current = models.NullBooleanField(default=False)
    topic_scores_current = models.NullBooleanField(default=False)
    topic_year_scores_current = models.NullBooleanField(default=False)


    ## Time spent
    nmf_time = models.FloatField(default=0)
    tfidf_time = models.FloatField(default=0)
    db_time = models.FloatField(default=0)

    status_choices = (
        (0,'Not Started'),
        (1,'Running'),
        (2,'Interrupted'),
        (3,'Finished')
    )
    status = models.IntegerField(
        choices = status_choices,
        default = 0
    )


    parent_run_id = models.IntegerField(null=True)

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

    empty_topics = models.IntegerField(null=True)

    iterations = models.IntegerField(null=True)

    max_topics = models.IntegerField(null=True)
    term_count = models.IntegerField(null=True)
    periods = models.ManyToManyField('TimePeriod')

    dthreshold = models.FloatField(default = 0.0005 )

    def save(self, *args, **kwargs):
        if not self.parent_run_id:
            self.parent_run_id=self.run-id
        super(RunStats, self).save(*args, **kwargs)

class Settings(models.Model):
    run_id = models.IntegerField()
    doc_topic_score_threshold = models.FloatField()
    doc_topic_scaled_score = models.BooleanField()
