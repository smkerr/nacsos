from django.db import models
import parliament.models as pmodels
from django.contrib.postgres.fields import JSONField

# Create your models here.

class TwitterBaseModel(models.Model):

    api_got = models.BooleanField(default=False)
    scrape_got = models.BooleanField(default=False)

    id = models.BigIntegerField(primary_key=True)
    created_at = models.DateTimeField()
    lang = models.CharField(max_length=10)
    entities = JSONField()

    fetched = models.DateTimeField(u'Fetched', null=True, blank=True)


class User(TwitterBaseModel):

    ## Extra fields
    mdb_name = models.CharField(max_length=50)
    person = models.ForeignKey(pmodels.Person, on_delete=models.SET_NULL)
    monitoring = models.BooleanField(default=False)
    earliest = models.DateTimeField(null=True)
    latest = models.DateTimeField(null=True)

    ## ID
    id = models.BigIntegerField(primary_key=True,db_index=True)

    screen_name = models.CharField(u'Screen name', max_length=50, unique=True)

    name = models.CharField(u'Name', max_length=100)
    description = models.TextField(u'Description')
    location = models.CharField(u'Location', max_length=100)
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
    profile_background_color = models.CharField(max_length=6)
    profile_banner_url = models.URLField(max_length=300, null=True)
    profile_image_url = models.URLField(max_length=300, null=True)
    profile_image_url_https = models.URLField(max_length=300)
    url = models.URLField(max_length=300, null=True)

    profile_link_color = models.CharField(max_length=6)
    profile_sidebar_border_color = models.CharField(max_length=6)
    profile_sidebar_fill_color = models.CharField(max_length=6)
    profile_text_color = models.CharField(max_length=6)

    favorites_count = models.PositiveIntegerField()
    followers_count = models.PositiveIntegerField()
    friends_count = models.PositiveIntegerField()
    listed_count = models.PositiveIntegerField()
    statuses_count = models.PositiveIntegerField()
    utc_offset = models.IntegerField(null=True)

    followers = ManyToMany('User', versions=True)

    objects = models.Manager()
    remote = UserManager(methods={
        'get': 'get_user',
    })

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.friends_count < 0:
            log.warning('Negative value friends_count=%s set to 0 for user ID %s' % (self.friends_count, self.id))
            self.friends_count = 0
        super(User, self).save(*args, **kwargs)

    @property
    def slug(self):
        return self.screen_name

    def parse(self):
        self._response['favorites_count'] = self._response.pop('favourites_count', None)
        self._response.pop('status', None)
        super(User, self).parse()

    def fetch_followers(self, **kwargs):
        return User.remote.fetch_followers_for_user(user=self, **kwargs)

    def get_followers_ids(self, **kwargs):
        return User.remote.get_followers_ids_for_user(user=self, **kwargs)

    def fetch_statuses(self, **kwargs):
        return Status.remote.fetch_for_user(user=self, **kwargs)


class Status(TwitterBaseModel):

    # Twitter ID
    id = models.BigIntegerField(primary_key=True,db_index=True)

    author = models.ForeignKey('User', related_name='statuses')

    text = models.TextField()

    favorited = models.BooleanField(default=False)
    retweeted = models.BooleanField(default=False)
    truncated = models.BooleanField(default=False)

    source = models.CharField(max_length=100)
    source_url = models.URLField(null=True)

    favorites_count = models.PositiveIntegerField()
    retweets_count = models.PositiveIntegerField()
    replies_count = models.PositiveIntegerField(null=True)

    in_reply_to_status = models.ForeignKey('Status', null=True, related_name='replies')
    in_reply_to_user = models.ForeignKey('User', null=True, related_name='replies')

    favorites_users = ManyToMany('User', related_name='favorites')
    retweeted_status = models.ForeignKey('Status', null=True, related_name='retweets')

    place = JSONField(null=True)
    # format the next fields doesn't clear
    contributors = JSONField(null=True)
    coordinates = JSONField(null=True)
    geo = JSONField(null=True)

    objects = models.Manager()
    remote = StatusManager(methods={
        'get': 'get_status',
    })

    def __unicode__(self):
        return u'%s: %s' % (self.author, self.text)

    @property
    def slug(self):
        return '/%s/status/%d' % (self.author.screen_name, self.pk)

    def _substitute(self, old_instance):
        super(Status, self)._substitute(old_instance)
        self.replies_count = old_instance.replies_count

    def parse(self):
        self._response['favorites_count'] = self._response.pop('favorite_count', 0)
        self._response['retweets_count'] = self._response.pop('retweet_count', 0)

        self._response.pop('user', None)
        self._response.pop('in_reply_to_screen_name', None)
        self._response.pop('in_reply_to_user_id_str', None)
        self._response.pop('in_reply_to_status_id_str', None)

        self._get_foreignkeys_for_fields('in_reply_to_status', 'in_reply_to_user')

        super(Status, self).parse()

    def fetch_retweets(self, **kwargs):
        return Status.remote.fetch_retweets(status=self, **kwargs)

    def fetch_replies(self, **kwargs):
        return Status.remote.fetch_replies(status=self, **kwargs)
