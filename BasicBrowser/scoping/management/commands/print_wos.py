from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from utils.utils import *
import os

class Command(BaseCommand):
    help = 'print a WoS type file'

    def add_arguments(self, parser):
        parser.add_argument('qid',type=int)
        parser.add_argument('relevant',type=str, default="F")

    def handle(self, *args, **options):
        qid = options['qid']
        relevant = options['relevant']

        def ensure_dir(file_path):
            directory = os.path.dirname(file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)

        q = Query.objects.get(pk=qid)

        docs = Doc.objects.filter(query=q)

        print(relevant)

        if relevant=="T":
            docs = docs.filter(relevant=True)

        n = docs.count()
        #docs = docs[:11200]
        print(n)

        chunk_size = 10000

        alldocs = docs

        for chunk in range((n//chunk_size)+1):
            a = chunk*chunk_size
            z = (chunk+1)*chunk_size
            if z > n:
                z=n
            print(a)
            print(z)
            docs = alldocs[a:z]

            fname = "queries/{}/results_{}.txt".format(qid,chunk)

            ensure_dir(fname)

            with open(fname,"w") as f:
                f.write('FN Thomson Reuters Web of Science\nVR 1.0\n')
                for d in docs.iterator():
                    for field in WoSArticle._meta.get_fields():
                        #print(field)
                        #print(field.name)
                        #print(getattr(d.wosarticle, field.name, None))
                        if field.name=="doc":
                            continue

                        try:
                            wa = d.wosarticle
                        except:
                            print(d)
                            continue

                        r = getattr(d.wosarticle, field.name, None)

                        if r is None:
                            continue

                        if field.name=="c1":
                            r = eval(r)


                        fn = field.name.upper()
                        if fn=="KWP":
                            fn="ID"
                        if fn=="ISS":
                            fn="IS"
                        if fn=="EMS":
                            fn="EM"
                        f.write(fn)
                        f.write(' ')

                        if type(r) is list:
                            for i in range(len(r)):
                                if i>0:
                                    f.write('   ')
                                if fn=="CR" and "WOS:" not in d.UT.UT:
                                    r[i] = wosify_scopus_ref(r[i].strip())
                                f.write(r[i].strip())
                                f.write('\n')
                        else:
                            f.write(
                                str(r).strip().replace('\n','').replace('\r','')
                            )
                            f.write('\n')

                    if d.docauthinst_set.count() > 0:
                        dai = d.docauthinst_set.all()
                        aus = [x.AU.strip() for x in dai.distinct('AU')]

                        afs = [""]
                        for x in dai.distinct('AF'):
                            if x.AF is not None:
                                afs.append(x.AF.strip())
                        #afs = [x.AF.strip() for x in dai.distinct('AF')]

                        f.write('AU ')
                        for i in range(len(aus)):
                            if i>0:
                                f.write('   ')
                            f.write(aus[i])
                            f.write('\n')

                        if len(afs[0]) > 0:
                            f.write('AF ')
                            for i in range(len(afs)):
                                if i>0:
                                    f.write('   ')
                                f.write(afs[i])
                                f.write('\n')

                    f.write('UT ')
                    f.write(d.UT.UT)
                    f.write('\n')


                    f.write('ER\n\n')

                f.write('EF')
