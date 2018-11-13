from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

class Command(BaseCommand):
    def handle(self, *args, **options):
        print("\n\n#########\n\n")
        print("searching for tweets from the api")
        call_command('api_searches')
        print("\n\n#########\n\n")
        print("collecting users and their tweets from the api")
        call_command('hydrate_users')
        print("\n\n#########\n\n")
        print("using twint to scrape searches")
        call_command('scrape_searches', weeks = 200)
        print("\n\n#########\n\n")
        print("hydratomg empty tweets with the api")
        call_command('hydrate_tweets')
