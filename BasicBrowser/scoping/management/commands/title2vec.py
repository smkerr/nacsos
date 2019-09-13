from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
import gensim
import time
from django.utils import timezone

class Command(BaseCommand):
    help = 'recalculates a doc2vec model with the titles currently in db'

    def handle(self, *args, **options):


        vector_size = 300
        epochs = 10

        # Update any documents which don't have a tslug saved
        updating_slugs = True
        while updating_slugs == True:

            batch_docs = Doc.objects.filter(title__iregex='\w',tslug__isnull=True).order_by('id')[:10000]
            if batch_docs:
                b_titles = list(batch_docs.values_list('title',flat=True))
                for i in range(len(batch_docs)):
                    batch_docs[i].tslug = Doc.make_tslug(b_titles[i])
                Doc.objects.bulk_update(batch_docs, ['tslug'])
            else:
                updating_slugs=False


        print("FINISHED!")
        docs = Doc.objects.filter(title__iregex='\w').order_by('id')
        n_docs = docs.count()

        tvm = TitleVecModel.objects.filter(whole_corpus=True).last()
        if tvm:
            if tvm.n_docs==n_docs:
                print("Exiting, as there are no new documents")
                return


        def simple_tokenize(s):
            from nltk.tokenize import RegexpTokenizer
            tokenizer = RegexpTokenizer('\W+', gaps=True)
            return tokenizer.tokenize(s.lower())

        def read_docs(fname, tokens_only=False):
            for i, doc in enumerate(docs.iterator()):
                yield gensim.models.doc2vec.TaggedDocument(simple_tokenize(doc.title), [doc.pk])

        t1 = time.time()

        print(f"Running a doc2vec model on {n_docs} documents with {vector_size} dimensions")

        titles = list(read_docs(docs))
        model = Doc2Vec(vector_size=vector_size, min_count=100, epochs=10)
        model.build_vocab(titles)
        model.train(titles, total_examples=model.corpus_count, epochs=model.epochs)

        t0 = time.time()
        fname = f"/usr/local/apsis/queries/title_model_{vector_size}"
        model.save(fname)

        tvmodel = TitleVecModel(
            date_completed = timezone.now(),
            n_docs = n_docs,
            n_vec = vector_size,
            file_path = fname,
            epochs = epochs,
            time_taken = t0-t1,
            whole_corpus = True
        )
        tvmodel.save()
