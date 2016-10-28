from django.db import models

#################################################
## Topic, Term and Doc are the three primary models
class Topic(models.Model):
    topic = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50)
    score = models.FloatField(null=True)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)

class Term(models.Model):    
    term = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)

class Doc(models.Model):
    doc = models.AutoField(primary_key=True)
    title = models.TextField()
    content = models.TextField()
    UT = models.CharField(max_length=30)
    PY = models.IntegerField()
    run_id = models.IntegerField(db_index=True)
    
    def word_count(self):
        return len(str(self.content).split())

#################################################
## DocAuthor holds the authors in a doc
class DocAuthors(models.Model):
    doc = models.ForeignKey('Doc',null=True)
    author = models.CharField(max_length=60)
    run_id = models.IntegerField(db_index=True)

#################################################
## TopicYear holds per year topic totals
class TopicYear(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    PY = models.IntegerField()
    score = models.FloatField()
    count = models.FloatField()
    run_id = models.IntegerField(db_index=True)

#################################################
## DocTopic and TopicTerm map contain topic scores
## for docs and topics respectively

class DocTopic(models.Model):
    doc = models.ForeignKey('Doc', null=True)
    topic = models.ForeignKey('Topic',null=True)
    score = models.FloatField()
    scaled_score = models.FloatField()
    run_id = models.IntegerField(db_index=True)

class TopicTerm(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    term = models.ForeignKey('Term',null=True)
    score = models.FloatField()
    run_id = models.IntegerField(db_index=True)


#################################################
## Not sure what this does????????
class DocTerm(models.Model):
    doc = models.IntegerField()
    term = models.IntegerField()
    score = models.FloatField()

#################################################
## RunStats and Settings....
class RunStats(models.Model):
    run_id = models.IntegerField(primary_key=True)
    start = models.DateTimeField()
    batch_count = models.IntegerField()
    last_update = models.DateTimeField()
    topic_titles_current = models.NullBooleanField()
    topic_scores_current = models.NullBooleanField()
    topic_year_scores_current = models.NullBooleanField()

class Settings(models.Model):
    run_id = models.IntegerField()
    doc_topic_score_threshold = models.FloatField()
    doc_topic_scaled_score = models.BooleanField()
