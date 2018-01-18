from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
import cities.models

class Search(models.Model):
    title = models.TextField()
    text = models.TextField()
    creator = models.ForeignKey(
        User,
        null=True,
        verbose_name="Query Creator",
        #related_name="user_creations",
        #reverse_n
    )

class Parl(models.Model):
    LEVEL_CHOICES = (
        ('N','National'),
        ('R','Regional')
    )
    country = models.ForeignKey(cities.models.Country)
    region = models.ForeignKey(cities.models.Region, null=True)
    level = models.CharField(max_length=1, choices=LEVEL_CHOICES)

class ParlSession(models.Model):
    parliament = models.ForeignKey(Parl)
    n = models.IntegerField()
    years = ArrayField(models.IntegerField())
    total_seats = models.IntegerField()

class Document(models.Model):
    parlsession = models.ForeignKey(ParlSession)
    date = models.DateField(null=True)
    parl_period = models.IntegerField(null=True)
    search_matches = models.ManyToManyField(Search)
    doc_type = models.TextField()

class Party(models.Model):
    name = models.TextField()

class Person(models.Model):
    surname = models.TextField()
    first_name = models.TextField()
    dob = models.DateField(null=True)

class Utterance(models.Model):
    document = models.ForeignKey(Document)
    speaker = models.ForeignKey(Person)

class Paragraph(models.Model):
    utterance = models.ForeignKey(Utterance)
    text = models.TextField()

class Constituency(models.Model):
    country = models.ForeignKey(cities.models.Country)
    region = models.ForeignKey(cities.models.Region, null=True)
    parliament = models.ForeignKey(Parl)
    has_coal = models.BooleanField()

class SeatResult(models.Model):
    parlsession = models.ForeignKey(ParlSession)
    person = models.ForeignKey(Person)
    party = models.ForeignKey(Party)
    constituency = models.ForeignKey(Constituency)
    total_votes_cast = models.FloatField()
    votes_received = models.FloatField()
    incumbent = models.BooleanField()
    majority = models.FloatField()

class SeatSum(models.Model):
    parlsession = models.ForeignKey(ParlSession)
    party = models.ForeignKey(Party)
    seats = models.IntegerField()
    government = models.BooleanField()
    majority = models.BooleanField()

class Post(models.Model):
    title = models.TextField()
    person = models.ForeignKey(Person)
    party = models.ForeignKey(Party)
    parlsession = models.ForeignKey(ParlSession)
    years = ArrayField(models.IntegerField())
    start_date = models.DateField()
    end_date = models.DateField()

class Interjection(models.Model):
    paragraph = models.ForeignKey(Paragraph)
    parties = models.ManyToManyField(Party)
    persons = models.ManyToManyField(Person)






# Create your models here.
