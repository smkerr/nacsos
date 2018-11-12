from twitter.models import *
from rest_framework import serializers

class UserSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = User
        fields = '__all__'

class StatusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = Status
        fields = '__all__'

class TwitterSearchSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    class Meta:
        model = TwitterSearch
        fields = '__all__'
