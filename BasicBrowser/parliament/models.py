from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
import cities.models


##########################
## Political Structure

class Parl(models.Model):
    LEVEL_CHOICES = (
        ('N','National'),
        ('R','Regional')
    )
    country = models.ForeignKey(cities.models.Country, on_delete=models.CASCADE)
    region = models.ForeignKey(cities.models.Region, on_delete=models.CASCADE, null=True)
    level = models.CharField(max_length=1, choices=LEVEL_CHOICES)

    def __str__(self):
      return self.country.name + " - " + self.get_level_display()

class ParlPeriod(models.Model):
    parliament = models.ForeignKey(Parl, on_delete=models.CASCADE)
    n = models.IntegerField()
    years = ArrayField(models.IntegerField(),null=True)
    total_seats = models.IntegerField(null=True)

    def __str__(self):
        return "{} - {}".format(self.parliament,self.n)


class Party(models.Model):
    name = models.TextField()
    alt_names = ArrayField(models.TextField(),null=True)
    parliament = models.ForeignKey(Parl, on_delete=models.CASCADE,null=True)
    colour = models.CharField(max_length=7, null=True)

    def __str__(self):
        if self is None:
            return("NA")
        return self.name.upper()

class Person(models.Model):
    FEMALE = 1
    MALE = 2


    GENDERS = (
        (FEMALE,'Female'),
        (MALE, 'Male'),
    )


    #### Names
    surname = models.TextField()
    alt_surnames = ArrayField(models.TextField(),null=True)
    first_name = models.TextField()
    alt_first_names = ArrayField(models.TextField(),null=True)
    title = models.TextField(null=True)
    academic_title = models.TextField(null=True)
    ortszusatz = models.TextField(null=True)
    adel = models.TextField(null=True)
    prefix = models.TextField(null=True)

    clean_name = models.TextField(null=True)

    ## Parliamentary periods
    in_parlperiod = ArrayField(models.IntegerField(), null=True)

    ## Bio
    dob = models.DateField(null=True)
    year_of_birth = models.IntegerField(null=True)
    place_of_birth = models.TextField(null=True)
    country_of_birth = models.ForeignKey(cities.models.Country, on_delete=models.CASCADE,null=True)
    date_of_death = models.DateField(null=True)

    gender = models.IntegerField(null=True,choices=GENDERS)
    family_status = models.TextField(null=True)
    religion = models.TextField(null=True)
    occupation = models.TextField(null=True)
    short_bio = models.TextField(null=True)

    party = models.ForeignKey(Party, on_delete=models.CASCADE ,null=True)

    def __str__(self):
        return self.clean_name

##################################
## Texts

class Document(models.Model):
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE )
    sitting = models.IntegerField(null=True)
    date = models.DateField(null=True)
    #parl_period = models.IntegerField(null=True)
    search_matches = models.ManyToManyField('Search')
    doc_type = models.TextField()

    def __str__(self):
        return "{} - {} , {}".format(self.date, self.doc_type,self.parlperiod.n)

class Utterance(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    speaker = models.ForeignKey(Person, on_delete=models.CASCADE)

class Paragraph(models.Model):
    utterance = models.ForeignKey(Utterance, on_delete=models.CASCADE)
    text = models.TextField()
    search_matches = models.ManyToManyField('Search')
    word_count = models.IntegerField(null=True)
    char_len = models.IntegerField(null=True)

    class Meta:
        ordering = ['id']

class Interjection(models.Model):

    APPLAUSE = 1
    SPEECH = 2
    OBJECTION = 3
    AMUSEMENT = 4
    LAUGHTER = 5
    OUTCRY = 6


    REACTION_CHOICES = (
        (APPLAUSE,'Applause'),
        (SPEECH, 'Speech'),
        (OBJECTION, 'Objection'),
        (AMUSEMENT, 'Amusement'),
        (LAUGHTER, 'Laughter'),
        (OUTCRY, 'Outcry')
    )
    paragraph = models.ForeignKey(Paragraph, on_delete=models.CASCADE)
    parties = models.ManyToManyField(Party)
    persons = models.ManyToManyField(Person)
    type = models.IntegerField(choices=REACTION_CHOICES)
    text = models.TextField(null=True)

    EMOJIS = {
        APPLAUSE:'em-clap',
        SPEECH:'em-speech_balloon',
        OBJECTION:'em-raised_hand_with_fingers_splayed',
        AMUSEMENT:'em-grinning',
        LAUGHTER:'em-laughing',
        OUTCRY: ''
    }
    @property
    def emoji(self):
        return self.EMOJIS[self.type]




###################################
## Election results


class Constituency(models.Model):
    name = models.TextField(null=True)
    number = models.IntegerField(null=True)
    region = models.ForeignKey(cities.models.Region, on_delete=models.CASCADE, null=True)
    parliament = models.ForeignKey(Parl, on_delete=models.CASCADE)
    has_coal = models.NullBooleanField(null=True)
    def __str__(self):
        return "Wahlkreis {}: {} ({})".format(self.number, self.name, self.region)

class PartyList(models.Model):
    name = models.TextField(null=True)
    region = models.ForeignKey(cities.models.Region, on_delete=models.CASCADE,null=True)
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE,null=True)

    def __str__(self):
        return self.region.name
    # def __str__(self):
    #     if self is None:
    #         return None
    #     return self.name

class ListMembership(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    list = models.ForeignKey(PartyList, on_delete=models.CASCADE)
    position = models

class Seat(models.Model):

    DIRECT = 1
    LIST = 2
    VOLKSKAMMER = 3
    SEAT_TYPES = (
        (DIRECT,'Direct'),
        (LIST, 'List'),
        (VOLKSKAMMER, 'Volkskammer')
    )

    parlperiod=models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    occupant = models.ForeignKey(Person, on_delete=models.CASCADE)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, null=True)
    seat_type = models.IntegerField(choices=SEAT_TYPES,null=True)
    constituency = models.ForeignKey(Constituency, null=True, on_delete=models.CASCADE,)
    list = models.ForeignKey(PartyList, on_delete=models.CASCADE, null=True)



class ConstituencyVote1(models.Model):
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    votes = models.IntegerField(null=True)
    votes_cast = models.IntegerField(null=True)
    eligible_votes = models.IntegerField(null=True)
    majority = models.FloatField(null=True)
    proportion = models.FloatField(null=True)

class ConstituencyVote2(models.Model):
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    list = models.ForeignKey(PartyList, on_delete=models.CASCADE)
    votes = models.IntegerField()
    votes_cast = models.IntegerField(null=True)
    eligible_votes = models.IntegerField(null=True)
    proportion = models.FloatField(null=True)


class SeatSum(models.Model):
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    seats = models.IntegerField()
    government = models.BooleanField()
    majority = models.BooleanField()

class Post(models.Model):
    title = models.TextField()
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    cabinet = models.BooleanField(default=False)
    years = ArrayField(models.IntegerField())
    start_date = models.DateField()
    end_date = models.DateField()



################################
## Data interpretation
class Search(models.Model):
    title = models.TextField()
    text = models.TextField()
    party = models.ForeignKey(Party, on_delete=models.CASCADE, null=True)
    speaker_regions = models.ManyToManyField(cities.models.Region)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Query Creator",
        #related_name="user_creations",
        #reverse_n
    )
    par_count=models.IntegerField(default=0,verbose_name="Paragraphs")

    PARAGRAPH = 1
    UTTERANCE = 2

    OBJECT_TYPES = ((PARAGRAPH,'Paragraph'),
                    (UTTERANCE, 'Utterance'))

    search_object = models.IntegerField(choices=OBJECT_TYPES, default=PARAGRAPH)
