from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
import os
import psutil
import time

class Command(BaseCommand):
    def handle(self, *args, **options):

        pid = os.getpid()

        for p in psutil.process_iter():
            if "refresh_users" in p.cmdline() and p.pid != pid:
                print("Scraping is already running... skipping for today")
                time.sleep(3)
                return


        print("\n\n#########\n\n")
        print("using twint to scrape users")
        call_command('scrape_users', 500)
