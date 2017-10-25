from django.core.management.base import BaseCommand, CommandError
from scoping.models import *
from tmv_app.models import *

from multiprocess import Pool
from functools import partial

import numpy as np
import re, nltk
from nltk.stem import SnowballStemmer
from time import time

from utils.utils import *# flatten

class Command(BaseCommand):
    help = 'do open heart surgery on database'

    def handle(self, *args, **options):

        def get_objs(objs, test):
            n = objs.count()
            if n > 100000:
                p = n*0.00001
            else:
                p = n*0.1

            #p = 100
            if test:
                try:
                    objs = objs[:p]
                except:
                    objs = objs
            return(objs)

        # (<ManyToOneRel: scoping.docproject>,
        #  <ManyToManyRel: scoping.doc>,
        #  <ManyToOneRel: scoping.docbigram>,
        test = False



        def copy_bigram(db):
            django.db.connections.close_all()
            dc = Doc_2.objects.get(
                UT__UT=db.doc.UT
            )
            dbc, created = DocBigram_copy.objects.get_or_create(
                doc = dc,
                bigram = db.bigram,
                n = db.n
            )

        if DocBigram_copy.objects.count() != DocBigram.objects.count():
            print("Processing docbigrams")
            objs = DocBigram.objects.all()
            if test:
                try:
                    objs = objs[:20]
                except:
                    objs = objs
            t0 = time()
            DocBigram_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_bigram,DocBigram.objects.all())
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))

        #  <ManyToOneRel: scoping.networkproperties>,
        # 88683

        def copy_np(mod):
            django.db.connections.close_all()
            dc = Doc_2.objects.get(
                UT__UT=mod.doc.UT
            )
            nobj, created = NetworkProperties_copy.objects.get_or_create(
                doc = dc,
                network = mod.network,
                value = mod.value,
                fvalue = mod.fvalue
            )

        if NetworkProperties_copy.objects.count() != NetworkProperties.objects.count():
            print("Processing NetworkProperties")
            objs = NetworkProperties.objects.all()
            if test:
                try:
                    objs = objs[:20]
                except:
                    objs = objs
            t0 = time()
            NetworkProperties_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_np, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))

        #  <ManyToOneRel: scoping.citation>,
        # 4370448

        def copy_citation(mod):
            django.db.connections.close_all()
            if mod.referent is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.referent.UT
                )
            else:
                dc = None
            nobj, created = Citation_copy.objects.get_or_create(
                referent = dc,
                au = mod.au,
                py = mod.py,
                so = mod.so,
                vl = mod.vl,
                bp = mod.bp,
                doi = mod.doi,
                ftext = mod.ftext,
                alt_text = mod.alt_text,
                docmatches = mod.docmatches
            )
            nobj.save()

        if abs(Citation_copy.objects.count() - Citation.objects.count()) > 10 :
            print("Processing Citations")
            t0 = time()
            Citation_copy.objects.all().delete()
            objs = Citation.objects.all()
            if test:
                try:
                    objs = objs[:20]
                except:
                    objs = objs
            pool = Pool(processes=6)
            pool.map(copy_citation, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))


        # <ManyToOneRel: scoping.cdo>
        # 7719245

        def copy_cdo(mod):
            django.db.connections.close_all()
            dc = Doc_2.objects.get(
                UT__UT=mod.doc.UT
            )
            if mod.citation.referent is not None:
                ref = Doc_2.objects.get(
                    UT__UT=mod.citation.referent.UT
                )
            else:
                ref = None

            cc, created = Citation_copy.objects.get_or_create(
                referent = ref,
                au = mod.citation.au,
                py = mod.citation.py,
                so = mod.citation.so,
                vl = mod.citation.vl,
                bp = mod.citation.bp,
                doi = mod.citation.doi,
                ftext = mod.citation.ftext,
                alt_text = mod.citation.alt_text,
                docmatches = mod.citation.docmatches
            )

            nobj, created = CDO_copy.objects.get_or_create(
                doc = dc,
                citation = cc
            )

            nobj.save()

        if abs(CDO_copy.objects.count() - CDO.objects.count()) > 100000:
            print("Processing CDOs")
            objs = get_objs(CDO.objects.all(),test)
            t0 = time()
            CDO_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_cdo, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))


        # <ManyToOneRel: scoping.bibcouple>
        # 2029594

        # <ManyToOneRel: scoping.bibcouple>
        # 2029594

        def copy_bc(mod):
            django.db.connections.close_all()
            dc = Doc_2.objects.get(
                UT__UT=mod.doc1.UT
            )
            dc2 = Doc_2.objects.get(
                UT__UT=mod.doc2.UT
            )

            nobj, created = BibCouple_copy.objects.get_or_create(
                doc1 = dc,
                doc2 = dc2,
                cocites = mod.cocites
            )

            nobj.save()

        if BibCouple_copy.objects.count() != BibCouple.objects.count():
            print("Processing BibCouples")
            objs = get_objs(BibCouple.objects.all(),test)
            t0 = time()
            BibCouple_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_bc, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))


        # <ManyToOneRel: scoping.ipccref>
        # 73522
        def copy_ip(mod):
            django.db.connections.close_all()
            if mod.doc is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.doc.UT
                )
            else:
                dc = None

            nobj, created = IPCCRef_copy.objects.get_or_create(
                authors = mod.authors,
                year = mod.year,
                text = mod.text,
                words = mod.words,
                doc = dc,
                chapter = mod.chapter
            )
            nobj.save()
            for ar in mod.ar.all():
                nobj.ar.add(ar)
            for wg in mod.wg.all():
                nobj.wg.add(wg)

            nobj.save()

        if IPCCRef_copy.objects.count() != IPCCRef.objects.count():
            print("Processing IPCCREFS")
            objs = get_objs(IPCCRef.objects.all(),test)
            t0 = time()
            IPCCRef_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_ip, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))

        # <ManyToManyRel: scoping.kw>
        # 309021

        def copy_kw(mod):
            django.db.connections.close_all()
            nobj, created = KW_copy.objects.get_or_create(
                text = mod.text,
                ndocs = mod.ndocs
            )
            for d in get_objs(mod.doc.all(),False):
                dc = Doc_2.objects.get(
                    UT__UT=d.UT
                )
                nobj.doc.add(dc)

            nobj.save()

        if KW_copy.objects.count() != KW.objects.count():
            print("Processing KWs")
            objs = get_objs(KW.objects.all(),test)
            t0 = time()
            KW_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_kw, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))


        # <ManyToManyRel: scoping.wc>
        # 232
        def copy_wc(mod):
            django.db.connections.close_all()
            nobj, created = WC_copy.objects.get_or_create(
                text = mod.text,
                oecd = mod.oecd,
                oecd_fos = mod.oecd_fos,
                oecd_fos_text = mod.oecd_fos_text
            )
            nobj.save()
            for d in get_objs(mod.doc.all(),False):
                dc = Doc_2.objects.get(
                    UT__UT=d.UT
                )
                nobj.doc.add(dc)


            nobj.save()

        if WC_copy.objects.count() != WC.objects.count():
            print("Processing WCs")
            objs = get_objs(WC.objects.all(),test)
            t0 = time()
            WC_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_wc, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))


        # <ManyToOneRel: scoping.docrel>
        # 73111
        # <ManyToOneRel: scoping.docrel>
        # 73111

        def copy_dr(mod):
            django.db.connections.close_all()
            dc = Doc_2.objects.get(
                UT__UT=mod.seed.UT
            )
            if mod.referent is not None:
                dc2 = Doc_2.objects.get(
                    UT__UT=mod.referent.UT
                )
            else:
                dc2 = None

            nobj, created = DocRel_copy.objects.get_or_create(
                seed = dc,
                referent = dc2,
                seedquery = mod.seedquery,
                relation = mod.relation,
                text = mod.text,
                title = mod.title,
                au = mod.au,
                PY = mod.PY,
                journal =  mod.journal,
                link = mod.link,
                url = mod.url,
                doi = mod.doi,
                hasdoi = mod.hasdoi,
                docmatch_q = mod.docmatch_q,
                timatch_q = mod.timatch_q,
                indb = mod.indb,
                sametech = mod.sametech
            )

            nobj.save()

        if DocRel_copy.objects.count() != DocRel.objects.count():
            print("Processing DocRels")
            objs = get_objs(DocRel.objects.all(),test)
            t0 = time()
            DocRel_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_dr, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))




        # <ManyToOneRel: scoping.note>
        # 1354

        def copy_note(mod):
            django.db.connections.close_all()
            if mod.doc is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.doc.UT
                )
            else:
                dc = None

            nobj, created = Note_copy.objects.get_or_create(
                doc=dc,
                user=mod.user,
                date=mod.date,
                text=mod.text
            )

            nobj.save()

        if Note_copy.objects.count() != Note.objects.count():
            print("Processing Notes")
            objs = get_objs(Note.objects.all(),test)
            t0 = time()
            Note_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_note, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))

        # <ManyToOneRel: scoping.docownership>
        # 27756

        def copy_do(mod):
            django.db.connections.close_all()
            if mod.doc is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.doc.UT
                )
            else:
                dc = None

            nobj, created = DocOwnership_copy.objects.get_or_create(
                doc=dc,
                user=mod.user,
                query=mod.query,
                tag=mod.tag,
                relevant=mod.relevant,
                date=mod.date
            )

            nobj.save()

        if DocOwnership_copy.objects.count() != DocOwnership.objects.count():
            print("Processing DocOwnerships")
            objs = get_objs(DocOwnership.objects.all(),test)
            t0 = time()
            DocOwnership_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_do, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))

        # <ManyToOneRel: scoping.docauthinst>
        # 2755184

        def copy_dai(mod):
            django.db.connections.close_all()
            if mod.doc is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.doc.UT
                )
            else:
                dc = None

            nobj, created = DocAuthInst_copy.objects.get_or_create(
                doc=dc,
                AU=mod.AU,
                AF=mod.AF,
                institution=mod.institution,
                position=mod.position
            )

            nobj.save()

        if DocAuthInst_copy.objects.count() != DocAuthInst.objects.count():
            print("Processing DAIS")
            objs = get_objs(DocAuthInst.objects.all(),test)
            t0 = time()
            DocAuthInst_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_dai, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))


        # <ManyToOneRel: scoping.docreferences>
        # 9638

        def copy_dr(mod):
            django.db.connections.close_all()
            if mod.doc is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.doc.UT
                )
            else:
                dc = None

            nobj, created = DocReferences_copy.objects.get_or_create(
                doc=dc,
                refdoi=mod.refdoi,
                refall=mod.refall
            )

            nobj.save()

        if DocReferences_copy.objects.count() != DocReferences.objects.count():
            print("Processing DocRefs")
            objs = get_objs(DocReferences.objects.all(),test)
            t0 = time()
            DocReferences_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_dr, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))

        # <OneToOneRel: scoping.wosarticle>
        # 745842

        def copy_wa(mod):
            django.db.connections.close_all()
            if mod.doc is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.doc.UT
                )
            else:
                dc = None

            nobj, created = WoSArticle_copy.objects.get_or_create(
                doc=dc,
                pt = mod.pt,
                ti = mod.ti,
                ab = mod.ab,
                py = mod.py,
                ar = mod.ar,
                bn = mod.bn,
                bp =  mod.bp,
                c1 = mod.c1,
                cl = mod.cl,
                cr = mod.cr,
                ct = mod.ct,
                de = mod.de,
                di = mod.di,
                dt = mod.dt,
                em = mod.em,
                ep = mod.ep,
                fn = mod.fn,
                fu = mod.fu,
                fx = mod.fx,
                ga = mod.ga,
                ho =  mod.ho,
                iss = mod.iss,
                ad = mod.ad,
                kwp = mod.kwp,
                j9 = mod.j9,
                ji = mod.ji,
                la = mod.la,
                nr = mod.nr,
                pa = mod.pa,
                pd = mod.pd,
                pg = mod.pg,
                pi = mod.pi,
                pu = mod.pu,
                rp = mod.rp,
                sc = mod.sc,
                se =  mod.se,
                si = mod.si,
                sn = mod.sn,
                so = mod.so,
                sp = mod.sp,
                su = mod.su,
                tc = mod.tc,
                vl = mod.vl,
                wc = mod.wc
            )

            nobj.save()

        if WoSArticle_copy.objects.count() != WoSArticle.objects.count():
            print("Processing WosArticles")
            WoSArticle_copy.objects.all().delete()
            objs = get_objs(WoSArticle.objects.all(),test)
            t0 = time()
            pool = Pool(processes=6)
            pool.map(copy_wa, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))

        # <ManyToOneRel: tmv_app.hdoctopic>
        # 0
        # <ManyToOneRel: tmv_app.doctopic>
        # 147221512
        def copy_dt(mod):
            django.db.connections.close_all()
            if mod.doc is not None:
                dc = Doc_2.objects.get(
                    UT__UT=mod.doc.UT
                )
            else:
                dc = None

            nobj, created = DocTopic_copy.objects.get_or_create(
                doc=dc,
                topic=mod.topic,
                score=mod.score,
                scaled_score=mod.scaled_score,
                run_id=mod.run_id
            )

            nobj.save()

        if DocTopic_copy.objects.count() != DocTopic.objects.count():
            print("Processing DocTopics")
            objs = get_objs(DocTopic.objects.all(),test)
            t0 = time()
            DocTopic_copy.objects.all().delete()
            pool = Pool(processes=6)
            pool.map(copy_dt, objs)
            pool.terminate()
            gc.collect()
            django.db.connections.close_all()
            print("done in %0.3fs." % (time() - t0))
