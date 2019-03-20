from django.db import models
from django.contrib.postgres.fields import ArrayField
import scoping, parliament
from django.contrib.auth.models import User
import numpy as np
import random


class MinMaxFloat(models.FloatField):
    """
    A float field with a minimum and a maximum
    """
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
    """
    A model for hierarchical topics
    """
    topic = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    title = models.CharField(max_length=80, null=True)
    n_docs = models.IntegerField(null=True)
    n_words = models.IntegerField(null=True)
    scale = models.FloatField(null=True)
    run_id = models.IntegerField(null=True, db_index=True)

class HTopicTerm(models.Model):
    """
    Links hierarchical topics to terms
    """
    topic = models.ForeignKey('HTopic', on_delete=models.CASCADE)
    term = models.ForeignKey('Term', on_delete=models.CASCADE)
    count = models.IntegerField()
    run_id = models.IntegerField(null=True, db_index=True)


#################################################
## Topic, Term and Doc are the three primary models
class Topic(models.Model):
    """
    The default topic object. The title is usually set according to the top words
    It is linked to
    """
    title = models.CharField(max_length=80)
    score = models.FloatField(null=True)
    share = models.FloatField(null=True)
    growth = models.FloatField(null=True)
    run_id = models.ForeignKey('RunStats',db_index=True, on_delete=models.CASCADE)
    year = models.IntegerField(null=True)
    period = models.ForeignKey('TimePeriod', on_delete=models.CASCADE,null=True)
    primary_dtopic = models.ManyToManyField('DynamicTopic')
    top_words = ArrayField(models.TextField(),null=True)
    primary_wg = models.IntegerField(null=True)
    wg_prop = models.FloatField(null=True)
    ipcc_coverage = models.FloatField(null=True)

    wg_1 = models.FloatField(null=True)
    wg_2 = models.FloatField(null=True)
    wg_3 = models.FloatField(null=True)


    def create_wordintrusion(self,user):
        real_words = self.topicterm_set.order_by('-score')[:5]

        scores = np.array(TopicTerm.objects.filter(topic__run_id=self.run_id).values_list('score', flat=True))
        q99 = np.quantile(scores, 0.99)
        q50 = np.quantile(scores, 0.5)
        terms = set(Term.objects.filter(
            topicterm__score__gt=q99,topicterm__topic__run_id=self.run_id
        ).values_list('pk',flat=True))
        bad_terms = Term.objects.filter(
            pk__in=terms,
            topicterm__score__lt=q50,
            topicterm__topic=self
        )
        if bad_terms.exists():
            bad_term = bad_terms[random.randint(0,bad_terms.count()-1)]
        else:
            bad_term = Term.objects.filter(topicterm__topic=self).order_by('topicterm__score')[0]
        word_intrusion = WordIntrusion(
            topic=self,
            user=user,
            intruded_word=bad_term
        )
        word_intrusion.save()
        for w in real_words:
            word_intrusion.real_words.add(w.term)

    def __unicode__(self):
        return str(self.title)

    def __str__(self):
        return str(self.title)

class WordIntrusion(models.Model):
    """
    Used to assess topic quality, in a given topic, can a user identify the
    intruding word
    """
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    real_words = models.ManyToManyField('Term')
    intruded_word = models.ForeignKey('Term', on_delete=models.CASCADE, related_name="intruding_topic")
    score = models.IntegerField(null=True)

class TopicIntrusion(models.Model):
    """
    Used to assess topic quality, in a given document, can a user identify the
    intruding topic
    """
    doc = models.ForeignKey('scoping.Doc', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    real_topics = models.ManyToManyField('Topic')
    intruded_topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name="intruding_doc")
    score = models.IntegerField(null=True)


class DynamicTopic(models.Model):
    title = models.CharField(null=True, max_length=80)
    score = models.FloatField(null=True)
    share = models.FloatField(null=True)
    size = models.IntegerField(null=True)
    run_id = models.ForeignKey('RunStats', on_delete=models.CASCADE,db_index=True)
    top_words = ArrayField(models.TextField(),null=True)
    l5ys = models.FloatField(null=True)
    l1ys = models.FloatField(null=True)
    primary_wg = models.IntegerField(null=True)
    ipcc_time_score = models.FloatField(null=True)
    ipcc_coverage = models.FloatField(null=True)
    ipcc_score = models.FloatField(null=True)
    ipcc_share = models.FloatField(null=True)
    wg_prop = models.FloatField(null=True)

    wg_1 = models.FloatField(null=True)
    wg_2 = models.FloatField(null=True)
    wg_3 = models.FloatField(null=True)

    def __unicode__(self):
        return str(self.title)


    def __str__(self):
        return str(self.title)


class TimePeriod(models.Model):
    title = models.CharField(null=True, max_length=80)
    parlperiod = models.ForeignKey('parliament.ParlPeriod', null=True, on_delete=models.CASCADE)
    n = models.IntegerField()
    ys = ArrayField(models.IntegerField(),null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    def __str__(self):
        return str(self.title)


class TimeDocTotal(models.Model):
    period = models.ForeignKey(TimePeriod, on_delete=models.CASCADE)
    run = models.ForeignKey('RunStats', on_delete=models.CASCADE)
    n_docs = models.IntegerField(null=True)
    dt_score = models.FloatField(null=True)


class TimeDTopic(models.Model):
    period = models.ForeignKey(TimePeriod, on_delete=models.CASCADE)
    dtopic = models.ForeignKey('DynamicTopic', on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    share = models.FloatField(default=0)
    pgrowth = models.FloatField(null=True)
    pgrowthn = models.FloatField(null=True)
    ipcc_score = models.FloatField(null=True)
    ipcc_coverage=models.FloatField(null=True)
    ipcc_share = models.FloatField(null=True)


class TopicDTopic(models.Model):
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, null=True)
    dynamictopic = models.ForeignKey('DynamicTopic', on_delete=models.CASCADE,null=True)
    score = models.FloatField(null=True)

class TopicCorr(models.Model):
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE,null=True)
    topiccorr = models.ForeignKey('Topic', on_delete=models.CASCADE ,null=True, related_name='Topiccorr')
    score = models.FloatField(null=True)
    ar = models.IntegerField(default=-1)
    period = models.ForeignKey('TimePeriod', on_delete=models.CASCADE, null=True)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)

class DynamicTopicCorr(models.Model):
    topic = models.ForeignKey('DynamicTopic', on_delete=models.CASCADE,null=True)
    topiccorr = models.ForeignKey('DynamicTopic', on_delete=models.CASCADE,null=True, related_name='Topiccorr')
    score = models.FloatField(null=True)
    ar = models.IntegerField(default=-1)
    period = models.ForeignKey('TimePeriod', on_delete=models.CASCADE, null=True)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)


class Term(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    run_id = models.ManyToManyField('RunStats')

    def __unicode__(self):
        return str(self.title)
    def __str__(self):
        return str(self.title)

#################################################
## Docs are all in scoping now!

#################################################
## TopicYear holds per year topic totals
class TopicYear(models.Model):
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE,null=True)
    PY = models.IntegerField()
    score = models.FloatField(null=True)
    share = models.FloatField(null=True)
    count = models.FloatField(null=True)
    run_id = models.IntegerField(db_index=True)


class TopicARScores(models.Model):
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE,null=True)
    ar = models.ForeignKey('scoping.AR', on_delete=models.CASCADE,null=True)
    score = models.FloatField(null=True)
    share = models.FloatField(null=True)
    pgrowth = models.FloatField(null=True)
    pgrowthn = models.FloatField(null=True)

# connecting topic with time periods
class TopicTimePeriodScores(models.Model):
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE,null=True)
    period = models.ForeignKey('TimePeriod', on_delete=models.CASCADE,null=True)
    score = models.FloatField(null=True)
    share = models.FloatField(null=True)
    pgrowth = models.FloatField(null=True)
    pgrowthn = models.FloatField(null=True)


class DynamicTopicARScores(models.Model):
    topic = models.ForeignKey('DynamicTopic', on_delete=models.CASCADE,null=True)
    ar = models.ForeignKey('scoping.AR', on_delete=models.CASCADE,null=True)
    score = models.FloatField(null=True)
    share = models.FloatField(null=True)
    pgrowth = models.FloatField(null=True)
    pgrowthn = models.FloatField(null=True)


class DynamicTopicTimePeriodScores(models.Model):
    topic = models.ForeignKey('DynamicTopic', on_delete=models.CASCADE,null=True)
    period = models.ForeignKey('TimePeriod', on_delete=models.CASCADE,null=True)
    score = models.FloatField(null=True)
    share = models.FloatField(null=True)
    pgrowth = models.FloatField(null=True)
    pgrowthn = models.FloatField(null=True)


#################################################
## Separate topicyear for htopic
class HTopicYear(models.Model):
    topic = models.ForeignKey('HTopic', on_delete=models.CASCADE,null=True)
    PY = models.IntegerField()
    score = models.FloatField()
    count = models.FloatField()
    run_id = models.IntegerField(db_index=True)

#################################################
## DocTopic and TopicTerm map contain topic scores
## for docs and topics respectively


class DocTopic(models.Model):
    #doc = models.ForeignKey(Doc, null=True)
    doc = models.ForeignKey('scoping.Doc', null=True, on_delete=models.CASCADE)
    par = models.ForeignKey('parliament.Paragraph',null=True, on_delete=models.CASCADE)
    ut = models.ForeignKey('parliament.Utterance',null=True, on_delete=models.CASCADE)
    topic = models.ForeignKey('Topic',null=True, on_delete=models.CASCADE)
    score = models.FloatField()
    scaled_score = models.FloatField()
    run_id = models.IntegerField(db_index=True)

class DocDynamicTopic(models.Model):
    doc = models.ForeignKey('scoping.Doc', null=True, on_delete=models.CASCADE)
    topic = models.ForeignKey('DynamicTopic',null=True, on_delete=models.CASCADE)
    score = models.FloatField()
    run_id = models.IntegerField(db_index=True)


class TopicTerm(models.Model):
    topic = models.ForeignKey('Topic',null=True, on_delete=models.CASCADE)
    term = models.ForeignKey('Term', on_delete=models.CASCADE,null=True)
    PY = models.IntegerField(db_index=True,null=True)
    score = models.FloatField()
    run_id = models.IntegerField(db_index=True)

class DynamicTopicTerm(models.Model):
    topic = models.ForeignKey('DynamicTopic', null=True, on_delete=models.CASCADE)
    term = models.ForeignKey('Term', on_delete=models.CASCADE, null=True)
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


class KFold(models.Model):
    model = models.ForeignKey('RunStats', on_delete=models.CASCADE)
    K = models.IntegerField()
    error = models.FloatField(null=True)


class TermPolarity(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    polarity = models.FloatField(null=True)
    POS = models.TextField(null=True)
    source = models.TextField()


#################################################
## RunStats and Settings....
class RunStats(models.Model):
    run_id = models.AutoField(primary_key=True)

    ##Inputs

    max_features = models.IntegerField(default=0, help_text = 'Maximum number of terms (0 = no limit)')
    min_freq = models.IntegerField(default=1, help_text = 'Minimum frequency of terms')
    max_df = MinMaxFloat(default=0.95, min_value=0.0, max_value=1.0)
    limit = models.IntegerField(null=True, default=0, help_text='Limit model to first x documents (leave as zero for no limit)')
    ngram = models.IntegerField(null=True, default=1, help_text='Length of feature n_gram')
    db = models.BooleanField(default=True, help_text='Record the results into the database? Or just run the model and record statistics?')

    fancy_tokenization = models.BooleanField(default=False, help_text='tokenize so that multiple word keywords remain whole')

    K = models.IntegerField(null=True, help_text='Number of topics')
    alpha = models.FloatField(null=True, default=0.01, help_text='Alpha parameter (try higher values in LDA, including > 1). Low (high) values indicate that documents should be composed of few (many) topics.')
    top_chain_var = models.FloatField(null=True, default=0.05, help_text='Chain var parameter for dtm')
    max_iter  = models.IntegerField(null=True, default=200, help_text='Maximum iterations')
    fulltext  = models.BooleanField(default=False, help_text='do analysis on fullText? (dependent on availability)')
    citations = models.BooleanField(default=False, help_text='scale term scores by citations?')

    # Additional information
    language=models.TextField(null=True)
    extra_stopwords = ArrayField(models.TextField(), null=True)

    query = models.ForeignKey('scoping.Query', null=True, on_delete=models.CASCADE)
    psearch = models.ForeignKey('parliament.Search',null=True, on_delete=models.CASCADE)

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
        (DTM, 'dnmf'),
        (NMF,'nmf'),
        (BDT,'BleiDTM')
    )
    method = models.CharField(
        max_length=2,
        choices=METHOD_CHOICES,
        default=NMF,
    )
    error = models.FloatField(null=True, default = 0)
    coherence = models.FloatField(null=True)
    errortype = models.TextField(null=True)

    empty_topics = models.IntegerField(null=True)

    iterations = models.IntegerField(null=True)

    max_topics = models.IntegerField(null=True)
    term_count = models.IntegerField(null=True)
    periods = models.ManyToManyField('TimePeriod')

    doc_topic_scaled_score = models.BooleanField(default=False)
    dt_threshold = models.FloatField(default = 0.0005 )
    dt_threshold_scaled = models.FloatField( default = 0.01)
    dyn_win_threshold = models.FloatField(default = 0.1 )

    def save(self, *args, **kwargs):
        if not self.parent_run_id:
            self.parent_run_id=self.run_id
        super(RunStats, self).save(*args, **kwargs)


class Settings(models.Model):
    run_id = models.IntegerField()
    doc_topic_score_threshold = models.FloatField()
    doc_topic_scaled_score = models.BooleanField()
