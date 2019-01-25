from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from utils.utils import *
import os
from django.core.mail import send_mail, EmailMessage
from django.core.management import call_command
from django.core.validators import validate_email



class Command(BaseCommand):
    help = 'Create a new user'

    def add_arguments(self, parser):
        parser.add_argument('email',type=str)
        parser.add_argument('first_name',type=str)
        parser.add_argument('last_name',type=str)

    def handle(self, *args, **options):
        # Validate email
        try:
            validate_email(options['email'])
            email = options['email'].lower()
        except django.core.exceptions.ValidationError:
            return "You didn't enter a valid email address, please do that!!"

        # create or get the user
        u, created = User.objects.get_or_create(
            username=email
        )
        if not created:
            return "This email address already has an account!"

        pw = call_command('generate_password')

        message = f'''
Dear {options['first_name']},

We've created an account for you on the APSIS platform: https://apsis.mcc-berlin.net/scoping/.

To log in, use your email address (lower case) and the following password:

{pw}

The platform is documented here: https://github.com/mcallaghan/tmv/wiki/Scoping-Documentation, although the platform has since been updated, and the automatic retrieval of documents from Web of Science and Scopus is only available to internal MCC users.

This is an automated email, but please get in touch with any questions, comments or suggestions on the platform. These are gladly received, although prompt changes might not always be possible.

Best,

Max
        '''
        print(message)

        # if they have been created, set the password and stuff, and send them an email
        u.first_name = options["first_name"]
        u.last_name = options["last_name"]
        u.is_superuser = True
        u.set_password(pw)

        u.save()

        emessage = EmailMessage(
            subject = 'APSIS scoping platform',
            body = message,
            from_email = 'Max Callaghan <callaghan@mcc-berlin.net>',
            to = (options['email'],),
        )

        emessage.send()
