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
    par_count=models.IntegerField(default=0,verbose_name="Paragraphs")

class Parl(models.Model):
    LEVEL_CHOICES = (
        ('N','National'),
        ('R','Regional')
    )
    country = models.ForeignKey(cities.models.Country)
    region = models.ForeignKey(cities.models.Region, null=True)
    level = models.CharField(max_length=1, choices=LEVEL_CHOICES)

    def __str__(self):
      return self.country.name + " - " + self.get_level_display()

class ParlSession(models.Model):
    parliament = models.ForeignKey(Parl)
    n = models.IntegerField()
    years = ArrayField(models.IntegerField(),null=True)
    total_seats = models.IntegerField(null=True)

class Document(models.Model):
    parlsession = models.ForeignKey(ParlSession)
    sitting = models.IntegerField(null=True)
    date = models.DateField(null=True)
    #parl_period = models.IntegerField(null=True)
    search_matches = models.ManyToManyField(Search)
    doc_type = models.TextField()

    def __str__(self):
        return "{} - {} , {}".format(self.date, self.doc_type,self.parlsession.n)

class Party(models.Model):
    name = models.TextField()
    parliament = models.ForeignKey(Parl,null=True)
    colour = models.CharField(max_length=7, null=True)

    def __str__(self):
        return self.name.upper()

class Person(models.Model):
    surname = models.TextField()
    first_name = models.TextField()
    clean_name = models.TextField(null=True)
    dob = models.DateField(null=True)
    party = models.ForeignKey(Party,null=True)

class Utterance(models.Model):
    document = models.ForeignKey(Document)
    speaker = models.ForeignKey(Person)

class Paragraph(models.Model):
    utterance = models.ForeignKey(Utterance)
    text = models.TextField()
    search_matches = models.ManyToManyField(Search)
    word_count = models.IntegerField(null=True)
    char_len = models.IntegerField(null=True)

    class Meta:
        ordering = ['id']

class Constituency(models.Model):
    name = models.TextField(null=True)
    number = models.IntegerField(null=True)
    country = models.ForeignKey(cities.models.Country)
    region = models.ForeignKey(cities.models.Region, null=True)
    parliament = models.ForeignKey(Parl)
    has_coal = models.BooleanField()

class SeatResult(models.Model):
    parlsession = models.ForeignKey(ParlSession)
    person = models.ForeignKey(Person)
    party = models.ForeignKey(Party)
    constituency = models.ForeignKey(Constituency)
    total_votes_cast = models.IntegerField()
    votes_received = models.IntegerField()
    incumbent = models.BooleanField()
    majority = models.FloatField()

class Seat(models.Model):
    parlsession = models.ForeignKey(ParlSession)


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

    APPLAUSE = 1
    SPEECH = 2
    OBJECTION = 3
    AMUSEMENT = 4
    OUTCRY = 5


    REACTION_CHOICES = (
        (APPLAUSE,'Applause'),
        (SPEECH, 'Speech'),
        (OBJECTION, 'Objection'),
        (AMUSEMENT, 'Laughter'),
        (OUTCRY, 'Outcry')
    )
    paragraph = models.ForeignKey(Paragraph)
    parties = models.ManyToManyField(Party)
    persons = models.ManyToManyField(Person)
    type = models.IntegerField(choices=REACTION_CHOICES)
    text = models.TextField(null=True)

    EMOJIS = {
        APPLAUSE:'em-clap',
        SPEECH:'em-speech_balloon',
        OBJECTION:'em-raised_hand_with_fingers_splayed',
        AMUSEMENT:'em-laughing',
        OUTCRY: ''
    }
    @property
    def emoji(self):
        return self.EMOJIS[self.type]




# Create your models here.
