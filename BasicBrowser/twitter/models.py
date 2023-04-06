from django.db import models
import parliament.models as pmodels
#import scoping.models as smodels
#rom scoping.models import Project
import scoping
# Create your models here.

class TwitterBaseModel(models.Model):

    api_got = models.BooleanField(default=False)
    scrape_got = models.BooleanField(default=False)

    id = models.BigIntegerField(primary_key=True)
    created_at = models.DateTimeField(null=True, db_index=True)
    lang = models.CharField(max_length=10, null=True, db_index=True)
    entities = models.JSONField(null=True)

    fetched = models.DateTimeField(u'Fetched', null=True, blank=True)


class User(TwitterBaseModel):

    ## Extra fields
    scrape_fetched = models.DateTimeField(u'Fetched', null=True, blank=True)
    until = models.DateTimeField(null=True)
    since = models.DateTimeField(null=True)

    mdb_name = models.CharField(max_length=50)
    person = models.OneToOneField(pmodels.Person, null=True, on_delete=models.SET_NULL)
    monitoring = models.BooleanField(default=False)
    earliest = models.DateTimeField(null=True)
    latest = models.DateTimeField(null=True)

    screen_name = models.CharField(u'Screen name', max_length=50)

    name = models.CharField(u'Name', max_length=200)
    description = models.TextField(u'Description')
    location = models.CharField(u'Location', max_length=200)
    time_zone = models.CharField(u'Time zone', max_length=100, null=True)

    contributors_enabled = models.BooleanField(u'Contributors enabled', default=False)
    default_profile = models.BooleanField(u'Default profile', default=False)
    default_profile_image = models.BooleanField(u'Default profile image', default=False)
    follow_request_sent = models.BooleanField(u'Follow request sent', default=False)
    following = models.BooleanField(u'Following', default=False)
    geo_enabled = models.BooleanField(u'Geo enabled', default=False)
    is_translator = models.BooleanField(u'Is translator', default=False)
    notifications = models.BooleanField(u'Notifications', default=False)
    profile_use_background_image = models.BooleanField(u'Profile use background image', default=False)
    protected = models.BooleanField(u'Protected', default=False)
    verified = models.BooleanField(u'Verified', default=False)

    profile_background_image_url = models.URLField(max_length=300, null=True)
    profile_background_image_url_https = models.URLField(max_length=300, null=True)
    profile_background_tile = models.BooleanField(default=False)
    profile_background_color = models.CharField(max_length=6, null=True)
    profile_banner_url = models.URLField(max_length=300, null=True)
    profile_image_url = models.URLField(max_length=300, null=True)
    profile_image_url_https = models.URLField(max_length=300, null=True)
    url = models.URLField(max_length=300, null=True)

    profile_link_color = models.CharField(max_length=6, null=True)
    profile_sidebar_border_color = models.CharField(max_length=6, null=True)
    profile_sidebar_fill_color = models.CharField(max_length=6, null=True)
    profile_text_color = models.CharField(max_length=6, null=True)

    favourites_count = models.PositiveIntegerField(default=0)
    followers_count = models.PositiveIntegerField(default=0)
    friends_count = models.PositiveIntegerField(default=0)
    listed_count = models.PositiveIntegerField(default=0)
    statuses_count = models.PositiveIntegerField(default=0)
    utc_offset = models.IntegerField(null=True)

    followers = models.ManyToManyField('User')

    def __unicode__(self):
        return self.name

    def __str__(self):
        return f"{self.name} - @{self.screen_name}"

class Status(TwitterBaseModel):

    author = models.ForeignKey('User', related_name='statuses', on_delete=models.SET_NULL, null=True)

    text = models.TextField(null=True, db_index=True)

    favorited = models.BooleanField(default=False)
    retweeted = models.BooleanField(default=False)
    truncated = models.BooleanField(default=False)

    source = models.CharField(max_length=300, null=True)
    source_url = models.URLField(null=True)

    favorites_count = models.PositiveIntegerField(default=0,null=True)
    retweets_count = models.PositiveIntegerField(default=0, null=True)
    replies_count = models.PositiveIntegerField(default=0,null=True)

    in_reply_to_status = models.ForeignKey('Status', null=True, related_name='replies', on_delete=models.SET_NULL)
    in_reply_to_user = models.ForeignKey('User', null=True, related_name='replies', on_delete=models.SET_NULL)

    favorites_users = models.ManyToManyField('User', related_name='favorites')
    retweeted_status = models.ForeignKey('Status', null=True, related_name='retweets', on_delete=models.SET_NULL)

    retweeted_by = models.ManyToManyField('User')

    place = models.JSONField(null=True)
    # format the next fields doesn't clear
    contributors = models.JSONField(null=True)
    coordinates = models.JSONField(null=True)
    geo = models.JSONField(null=True)

    searches = models.ManyToManyField('TwitterSearch')
    tag = models.ManyToManyField('scoping.Tag')

    def __unicode__(self):
        return u'%s: %s' % (self.author, self.text)

class TwitterSearch(models.Model):

    string = models.TextField()
    scrape_fetched = models.DateTimeField(u'Fetched', null=True, blank=True)
    until = models.DateTimeField(null=True)
    since = models.DateTimeField(null=True)
    search_since = models.DateTimeField(null=True)
    search_until = models.DateTimeField(null=True)
    search_fullapi = models.BooleanField(default=False)
    project = models.ForeignKey('scoping.Project', on_delete=models.CASCADE, null=True, related_name = 'TwitterSearches')
    project_list = models.ManyToManyField('scoping.Project', related_name = 'plist_TwitterSearches')

class SearchProgress(models.Model):

    server = models.TextField(null=True)
    search_date = models.DateTimeField(null=True)
    user_date = models.DateTimeField(null=True)
