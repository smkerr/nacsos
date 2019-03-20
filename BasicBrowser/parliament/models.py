from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
import cities.models
import scoping


##########################
## Political Structure

class Parl(models.Model):
    """
    Describes parliaments
    """
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
    """
    Describes parliamentary periods
    """
    parliament = models.ForeignKey(Parl, on_delete=models.CASCADE)
    n = models.IntegerField()
    years = ArrayField(models.IntegerField(),null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    total_seats = models.IntegerField(null=True)

    def __str__(self):
        return "{} - {}".format(self.parliament,self.n)


class Party(models.Model):
    """
    Describes political parties
    """
    name = models.TextField()
    alt_names = ArrayField(models.TextField(),null=True)
    parliament = models.ForeignKey(Parl, on_delete=models.CASCADE,null=True)
    colour = models.CharField(max_length=7, null=True)

    def __str__(self):
        if self is None:
            return("NA")
        return self.name.upper()

class Person(models.Model):
    """
    Describes a speaker in parliament, including information on names, active parliamentary periods and biographical details
    """
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
    active_country = models.ForeignKey(cities.models.Country,on_delete=models.CASCADE, related_name='person_active',
                                           null=True,verbose_name="Country in which the person is active in politics")
    positions = ArrayField(models.TextField(), null=True)

    ## Bio
    dob = models.DateField(null=True)
    year_of_birth = models.IntegerField(null=True)
    place_of_birth = models.TextField(null=True)
    country_of_birth = models.ForeignKey(cities.models.Country, on_delete=models.CASCADE,
                                         related_name='person_birth', null=True)
    date_of_death = models.DateField(null=True)

    gender = models.IntegerField(null=True,choices=GENDERS)
    family_status = models.TextField(null=True)
    religion = models.TextField(null=True)
    occupation = models.TextField(null=True)
    short_bio = models.TextField(null=True)

    party = models.ForeignKey(Party, on_delete=models.CASCADE, null=True)

    information_source = models.TextField(default="")

    def __str__(self):
        if self.clean_name:
            return self.clean_name
        else:
            return "{} {}".format(self.first_name, self.surname)

    def save(self, *args, **kwargs):
        if not self.id and not self.alt_surnames:
            surnames_list = self.surname.split(" ")
            if len(surnames_list) > 1:
                self.alt_surnames = [self.surname, surnames_list[-1]]
            else:
                self.alt_surnames = [self.surname]

        if not self.id and not self.alt_first_names:
            firstnames_list = self.first_name.split(" ")
            if len(firstnames_list) > 1:
                self.alt_first_names = [self.first_name] + firstnames_list
            else:
                self.alt_first_names = [self.first_name]

        if not self.id and not self.clean_name:
            self.clean_name = "{} {}".format(self.first_name, self.surname).strip()
            if self.title:
                self.clean_name = self.title + " " + self.clean_name
            if self.ortszusatz:
                self.clean_name = self.clean_name + " ({})".format(self.ortszusatz)

        super(Person, self).save(*args, **kwargs)

class SpeakerRole(models.Model):
    """
    Describes role of the speaker :model:`parliament.Person` in parliament
    """
    name = models.TextField()
    alt_names = ArrayField(models.TextField(), null=True)


##################################
## Texts

class Document(models.Model):
    """
    A model for parliamentary plenary sessions
    """
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE )
    sitting = models.IntegerField(null=True)
    date = models.DateField(null=True)
    #parl_period = models.IntegerField(null=True)
    search_matches = models.ManyToManyField('Search')
    doc_type = models.TextField()
    text_source = models.TextField(default="")
    creation_date = models.DateTimeField(auto_now_add=True,verbose_name="Date of entry creation")

    def __str__(self):
        return "{}, {}/{}, {}".format(self.doc_type, self.parlperiod.n, self.sitting, self.date)

class Utterance(models.Model):
    """
    A model for speeches in parliament, associated with one :model:`parliament.Person`
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    speaker = models.ForeignKey(Person, on_delete=models.CASCADE)
    speaker_role = models.ForeignKey(SpeakerRole, null=True, on_delete=models.SET_NULL)
    search_matches = models.ManyToManyField('Search')

    @property
    def paragraph_texts(self):
        return ' '.join([x.text for x in self.paragraph_set.all()])

class Paragraph(models.Model):
    """
    A model for paragraphs within an utterance
    """
    utterance = models.ForeignKey(Utterance, on_delete=models.CASCADE)
    text = models.TextField()
    search_matches = models.ManyToManyField('Search')
    word_count = models.IntegerField(null=True)
    char_len = models.IntegerField(null=True)

    class Meta:
        ordering = ['id']

class Interjection(models.Model):
    """
    A model for interjections by others to a speech, associated with a :model:`parliament.Paragraph`
    """

    APPLAUSE = 1
    SPEECH = 2
    OBJECTION = 3
    AMUSEMENT = 4
    LAUGHTER = 5
    OUTCRY = 6
    OTHER = 7


    REACTION_CHOICES = (
        (APPLAUSE,'Applause'),
        (SPEECH, 'Speech'),
        (OBJECTION, 'Objection'),
        (AMUSEMENT, 'Amusement'),
        (LAUGHTER, 'Laughter'),
        (OUTCRY, 'Outcry'),
        (OTHER, 'Other')
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
        OUTCRY: 'em-loudspeaker',
        OTHER: 'em em-grey_question'
    }
    @property
    def emoji(self):
        return self.EMOJIS[self.type]




###################################
## Election results


class Constituency(models.Model):
    """
    A model describing the constituency of a :model:`parliament.Person`, or which area they represent
    """
    name = models.TextField(null=True)
    number = models.IntegerField(null=True)
    region = models.ForeignKey(cities.models.Region, on_delete=models.CASCADE, null=True)
    parliament = models.ForeignKey(Parl, on_delete=models.CASCADE)
    has_coal = models.NullBooleanField(null=True)
    def __str__(self):
        return "Wahlkreis {}: {} ({})".format(self.number, self.name, self.region)

class PartyList(models.Model):
    """
    A model describing members on the party list of each political party for each parliamentary period

    Specific to German parliamentary electoral process
    """
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
    """
    A model linking a :model:`parliament.Person` to membership on :model:`parliament.PartyList`
    """
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    list = models.ForeignKey(PartyList, on_delete=models.CASCADE)
    # position = models

class Seat(models.Model):
    """
    A model describing how a :model:`Person` is elected into parliament

    Specific to German parliamentary electoral process

    Election can be through direct mandate from a :model:`parliament.Constituency`, via the :model:`parliament.PartyList`, or the Volksammer, an artefact from German reunificiation that is no longer in use today.
    """

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
    """
    A model describing the voting results for the elector's first vote in a federal election

    The first vote allows the elector to directly elect a :model:`parliament.Person`
    into a :model:`parliament.Constituency` for a :model:`parliament.ParlPeriod`

    Specific to German parliamentary electoral process
    """
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    votes = models.IntegerField(null=True)
    votes_cast = models.IntegerField(null=True)
    eligible_votes = models.IntegerField(null=True)
    majority = models.FloatField(null=True)
    proportion = models.FloatField(null=True)

class ConstituencyVote2(models.Model):
    """
    A model describing the voting results for the elector's second vote in a federal election

    The second vote allows the elector to vote for a political party for a :model:`parliament.ParlPeriod`, whose candidates are put together through the :model:`parliament.PartyList`. This determines who is elected into parliament from :model:`parliament.ListMembership`

    Specific to German parliamentary electoral process
    """
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    constituency = models.ForeignKey(Constituency, on_delete=models.CASCADE)
    list = models.ForeignKey(PartyList, on_delete=models.CASCADE)
    votes = models.IntegerField()
    votes_cast = models.IntegerField(null=True)
    eligible_votes = models.IntegerField(null=True)
    proportion = models.FloatField(null=True)


class SeatSum(models.Model):
    """
    A model describing the total sum of seats held by a :model:`parliament.Party` for a :model:`parliament.ParlPeriod`
    """
    parlperiod = models.ForeignKey(ParlPeriod, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    seats = models.IntegerField()
    government = models.BooleanField()
    majority = models.BooleanField()

class Post(models.Model):
    """
    A model describing the position that a :model:`parliament.Person` holds in parliament
    """
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
    """
    A model containing the results of a keyword search for either :model:`parliament.Utterance` or :model:`parliament.Paragraph` objects that contain the keyword
    """
    title = models.TextField()
    text = models.TextField()
    parliament = models.ForeignKey(Parl, on_delete=models.CASCADE, null=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, null=True)
    speaker_regions = models.ManyToManyField(cities.models.Region)
    start_date = models.DateField(null=True,verbose_name="Earliest date for search")
    stop_date = models.DateField(null=True,verbose_name="Latest date for search")
    document_source = models.TextField(null=True, verbose_name="Regex for text_source field of document")

    creation_date = models.DateTimeField(auto_now_add=True,verbose_name="Date of Search creation")
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Query Creator",
        #related_name="user_creations",
        #reverse_n
    )
    par_count=models.IntegerField(null=True,verbose_name="Number of paragraph objects")
    utterance_count=models.IntegerField(null=True,verbose_name="Number of utterance objects")

    PARAGRAPH = 1
    UTTERANCE = 2

    OBJECT_TYPES = ((PARAGRAPH,'Paragraph'),
                    (UTTERANCE, 'Utterance'))

    search_object_type = models.IntegerField(choices=OBJECT_TYPES, default=PARAGRAPH)
    project = models.ForeignKey('scoping.Project', on_delete=models.CASCADE, null=True)
