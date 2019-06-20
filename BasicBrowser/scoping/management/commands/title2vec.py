from django.core.management.base import BaseCommand, CommandError
from scoping.models import *

class Command(BaseCommand):
    help = 'recalculates a doc2vec model with the titles currently in db'

    def handle(self, *args, **options):

        def read_docs(fname, tokens_only=False):
            for i, doc in enumerate(docs.iterator()):
                yield gensim.models.doc2vec.TaggedDocument(gensim.utils.simple_preprocess(doc.title), [doc.pk])

        docs = Doc.objects.filter(title__iregex='\w').order_by('id')
