from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
import os
import psutil

class Command(BaseCommand):
    def handle(self, *args, **options):

        pid = os.getpid()

        for p in psutil.process_iter():
            if "refresh_searches" in p.cmdline() and p.pid != pid:
                print(p)
                print(p.cmdline())
                print("Scraping is already running... skipping for today")
                return


        print("\n\n#########\n\n")
        print("using twint to scrape searches")
        call_command('scrape_searches', 500)
