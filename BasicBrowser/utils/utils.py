import django, re, gc
from django.conf import settings

from RISparser import readris
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl
import sys
import uuid
import short_url


from scoping.models import *
from tmv_app.models import *

import scoping.models

##################################
## Flatten nested lists

def flatten(container):
    for i in container:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i



########################
## check status of run

def run_status(run_id):
    stat = RunStats.objects.get(pk=run_id)


###################################
# function, to be done in parallel,
# which pull citations from docs,
# adds them to db,
# and links citations and docs

def doc_cites(doc):
    django.db.connections.close_all()
    citations = doc.wosarticle.cr
    cdos = []
    for c in citations:

        doim = re.findall("DOI ([0-9]+.*)",c)
        if len(doim) > 0:
            doi = doim[0].replace(" ","")
            cobject, created = Citation.objects.get_or_create(
                doi = doi
            )
            if created:
                cobject.ftext = c
                cobject.save()
            #otherise append to alt text
        else:
            cobject, created = Citation.objects.get_or_create(
                ftext = c
            )

        cdo = CDO(doc=doc,citation=cobject)
        cdos.append(cdo)
    return(cdos)


def shingle(text):
    return set(s for s in ngrams(text.lower().split(),2))

def get(r, k):
    try:
        x = r[k]
    except:
        x = None
    return(x)

def jaccard(s1,s2):
    try:
        return len(s1.intersection(s2)) / len(s1.union(s2))
    except:
        return 0


def add_doc(r, q, update):

    django.db.connections.close_all()

    ut, created = UT.objects.get_or_create(UT=r['UT'])

    #doc, created = Doc.objects.get_or_create(UT=r['UT'])

    if created==False and update==False:
        doc = ut.doc
        doc.query.add(q)
        #doc.projects.add(q.project)
    else:
        doc, created = Doc.objects.get_or_create(UT=ut)
        doc.title=get(r,'TI')
        doc.content=get(r,'AB')
        doc.PY=get(r,'PY')
        doc.wos=True
        doc.save()
        doc.query.add(q)
        #doc.projects.add(q.project)
        article, created = WoSArticle.objects.get_or_create(doc=doc)
        try:
            r['wc'] = [x.strip() for x in get(r,'WC').split(";")]
        except:
            pass
        r['kwp'] = get(r,'ID')
        r['iss'] = get(r,'IS')
        for field in r:
            f = field.lower()
            try:
                article.f = r[field]
                setattr(article,f,r[field])
                #article.save()
                #print(r[field])
            except:
                print(field)
                print(r[field])

        try:
            article.save()
        except:
            print(r)
            sys.exit()


        ## Add authors
        # try:
        if get(r,'AU') is None:
            return

        for a in range(len(r['AU'])):
            try:
                af = r['AF'][a]
            except:
                af = None
            au = r['AU'][a]
            if 'C1' not in r:
                r['C1'] = [""]
            a_added = False
            for inst in r['C1']:
                inst = inst.split('] ',1)
                iauth = inst[0]
                # try:
                if len(inst) == 1:
                    if len(r['AU'])==1:
                        institute = inst
                        iauth = af
                else:
                    institute = inst[1]
                if af in iauth:
                    try:
                        dai,created = DocAuthInst.objects.get_or_create(
                            doc=doc,
                            AU = au,
                            AF = af,
                            institution = institute,
                            position = a+1
                        )
                        dai.save()
                        a_added=True
                    except:
                        doc.docauthinst_set.all().delete()
                        dai,created = DocAuthInst.objects.get_or_create(
                            doc=doc,
                            AU = au,
                            AF = af,
                            institution = institute,
                            position = a+1
                        )
                        dai.save()
                        a_added=True
                        print("{} {} {} {} {}".format(doc,au,af,institute,a+1))
            if a_added == False: # i.e. if there is nothing in institution...
                dai, created = DocAuthInst.objects.get_or_create(
                    doc=doc,
                    AU = au,
                    AF = af,
                    position = a+1
                )
                dai.save()

        doc.authors = ', '.join([x.AU for x in doc.docauthinst_set.all().order_by('position')])
        doc.first_author = doc.docauthinst_set.all().order_by('position').first().AU
        # except:
        #     pass


def read_wos(res, q, update):
    i=0
    n_records = 0
    records=[]
    record = {}
    mfields = ['AU','AF','CR','C1','WC']

    max_chunk_size = 2000
    chunk_size = 0

    q.doc_set.clear()

    p=12

    for line in res:
        if '\ufeff' in line: # BOM on first line
            continue
        if line=='ER\n':
            # end of record - save it and start a new one
            n_records +=1
            records.append(record)
            record = {}
            chunk_size+=1
            if chunk_size==max_chunk_size:
                # parallely add docs
                pool = Pool(processes=p)
                pool.map(partial(add_doc, q=q, update=update),records)
                pool.terminate()
                records = []
                chunk_size = 0
            continue
        if re.match("^EF",line): #end of file
            if chunk_size < max_chunk_size:
                # parallely add docs
                pool = Pool(processes=p)
                #pool.map(update_doc, records)
                pool.map(partial(add_doc, q=q, update=update),records)
                pool.terminate()
            #done!
            break
        if re.match("(^[A-Z][A-Z1-9])",line):
            s = re.search("(^[A-Z][A-Z1-9]) (.*)",line)
            key = s.group(1).strip()
            value = s.group(2).strip()
            if key in mfields:
                record[key] = [value]
            else:
                record[key] = value
        elif len(line) > 1:
            if key in mfields:
                record[key].append(line.strip())
            else:
                try:
                    record[key] += " " + line.strip()
                except:
                    print(line)
                    print(record)

    return n_records

def add_doc_text(r,q,update):

    scopus2WoSFields = {
        'M3': 'dt',
        'TI': 'ti',
        'T2': '',
        'C3': '',
        'J2': 'so',
        'VL': 'vl',
        'IS': '',
        'SP': 'bp',
        'EP': 'ep',
        'PY': 'py',
        'DO': 'di',
        'SN': 'sn',
        'AU': 'au',
        'AD': 'ad',
        'AB': 'ab',
        'KW': 'kwp',
        'Y2': '',
        'CY': '',
        #N1 means we need to read the next bit as key

        'Correspondence Address': '',
        'Funding details': 'fu',
        'Funding text': 'fx',
        'Cited By': 'tc',
        'References': 'cr',
        'UR': 'UT', # use url as ut, that's the only unique identifier...
        'PB': ''
        #'ER': , #End record

    }

    record = {}
    mfields = ['au','AF','cr','C1']
    for line in r:
        if re.search("([A-Z][A-Z1-9])(\s{2}-\s*)",line):
            s = re.search("([A-Z][A-Z1-9])(\s{2}-\s*)(.*)",line)
            key = s.group(1).strip()
            value = s.group(3).strip()
            if re.search("(.*)([A-Z][A-Z1-9])(\ {2}-\s*)",value):
                s = re.search("(.*)([A-Z][A-Z1-9])(\s*-\s*)(.*)",value)
                value = s.group(1).strip()
                nextkey = s.group(2).strip()
                nextvalue = s.group(4).strip()

                try:
                    nextkey = scopus2WoSFields[nextkey]
                except:
                    pass

                if nextkey in mfields:
                    record[nextkey] = [nextvalue]
                else:
                    record[nextkey] = nextvalue


            if key=="N1":
                s = re.search("([a-zA-Z1-9 ]*): *(.*)",value)
                try:
                    key = s.group(1).strip()
                    value = s.group(2).strip()
                except:
                    print(key)
                    print(value)

            try:
                key = scopus2WoSFields[key]
            except:
                pass



            if key in mfields:
                if key in record:
                    record[key].append(value)
                else:
                    record[key] = [value]
            else:
                if key in record:
                    record[key] += "; " + value
                else:
                    record[key] = value

        elif len(line) > 1:
            if key in mfields:
                record[key].append(line.strip())
            else:
                record[key] += line.strip()

    try:
        record['scopus_id'] = dict(parse_qsl(urlparse(record['UT']).query))['eid']
    except:
        print("don't want to add this record, it has no id!")
        return
    add_scopus_doc(record,q,update)
    return

def find_with_id(r):
    import scoping.models
    print(scoping.models)
    doc = None
    try:
        doc = scoping.models.Doc.objects.get(UT__sid=r['UT'])
    except:
        docs = scoping.models.Doc.objects.filter(UT__sid=r['UT']) | scoping.models.Doc.objects.filter(UT__UT=r['UT'])
        if docs.count()==1: # If it's just there - great!
            doc = docs.first()
            print("found!")
        elif docs.count() > 1:
            print("OH no! multiple matches!")
    return doc

def find_with_url(r):
    url, created = scoping.models.URLs.objects.get_or_create(
        url=r['url']
    )
    surl = short_url.encode_url(url.id)
    try:
        ut = scoping.models.UT.objects.get(UT=surl)
        doc = ut.doc
    except:
        doc = None
    return doc

def add_scopus_doc(r,q,update):
    doc = None
    try:
        r['UT'] = dict(parse_qsl(urlparse(r['UT']).query))['eid'].strip()
    except:
        if 'UT' not in r:
            r['UT'] = str(uuid.uuid1())
        r['url'] = r['UT']
        r['UT'] = None

    if r['UT'] is not None:
        doc = find_with_id(r)
    else:
        doc = find_with_url(r)
        for f in r:
            try:
                r[f] = r[f].replace('///','')
            except:
                pass

    if doc is None:
        # Try and find an exact match with doi and title
        try:
            did = r['di']
        except:
            did = 'NA'
            pass

        if did=='NA':
            docs = scoping.models.Doc.objects.filter(
                    wosarticle__ti__iexact=get(r,'ti'),
                    PY=get(r,'py')
            )
        else:
            docs = scoping.models.Doc.objects.filter(
                wosarticle__di=did
            )

        if len(docs)==1:
            print("found it through stage 2")
            docs.first().query.add(q)
            doc = docs.first()
        elif len(docs)>1: # if there are two, that's bad!
            print("more than one doc matching!!!!!")
            wdocs = docs.filter(UT__UT__contains='WOS:')
            if wdocs.count()==1:
                docs.exclude(UT__UT__contains='WOS:').delete()
                doc = wdocs.first()
            else:
                doc = docs.first()

        elif len(docs)==0: # if there are none, try with the title and jaccard similarity
            s1 = shingle(get(r,'ti'))

            twords = get(r,'ti').split()
            if len(twords) > 1:
                twords = ' '.join([x for x in twords[0:1]])
            else:
                twords = twords[0]

            py_docs = scoping.models.Doc.objects.filter(
                PY=get(r,'py'),
                title__iregex='\w',
                title__icontains=twords
            )
            doc = None
            for d in py_docs.iterator():
                j = jaccard(s1,d.shingle())
                if j > 0.51:
                    d.query.add(q)
                    doc = d
                    break

        if doc is None:
            if r['UT'] is not None:
                ut, created = scoping.models.UT.objects.get_or_create(
                    UT=r['UT'],
                    sid=r['UT']
                )
                doc = scoping.models.Doc(UT=ut)
                doc.save()
            else:
                url, created = scoping.models.URLs.objects.get_or_create(
                    url=r['url']
                )
                surl = short_url.encode_url(url.id)
                ut, created = scoping.models.UT.objects.get_or_create(
                    UT=surl
                )
                doc = scoping.models.Doc(UT=ut)
                doc.save()
                #print(doc)
    if doc is not None:
        if r['UT'] is not None:
            doc.UT.sid = r['UT']
            doc.UT.save()
        article, created = scoping.models.WoSArticle.objects.get_or_create(doc=doc)
        article.save()
        article.tc=get(r,'tc')
        if article.fu is None:
            article.fu = get(r,'fu')
        if article.fx is None:
            article.fx = get(r,'fx')
        try:
            article.dt = r['dt']
        except:
            pass

        try: # if it has no references, add them
            if article.cr is None and get(r,'cr') is not None:
                article.cr = r['cr']
        except:
            pass
        doc.save()
        article.save()
        doc.query.add(q)
        #doc.projects.add(q.project)
    if doc is not None and "WOS:" not in str(doc.UT.UT):
        if update:
            doc.title=get(r,'ti')
            doc.content=get(r,'ab')
            doc.PY=get(r,'py')
            doc.save()

            for field in r:
                f = field.lower()
                try:
                    article.f = r[field]
                    setattr(article,f,r[field])
                    #article.save()
                    #print(r[field])
                except:
                    print(field)
                    print(r[field])

            try:
                article.save()

            except:
                pass


            ## Add authors
            #try:
            dais = []
            if get(r,'au') is not None:
                doc.docauthinst_set.clear()
                for a in range(len(get(r,'au'))):
                    #af = r['AF'][a]
                    au = r['au'][a]
                    dai = scoping.models.DocAuthInst(doc=doc)
                    dai.AU = au
                    dai.position = a+1
                    dais.append(dai)
                    #dai.save()
                try:
                    DocAuthInst.objects.bulk_create(dais)
                except:
                    for dai in dais:
                        try:
                            dai.save()
                        except:
                            print("could not save dai {}".format(dai.AU))
        # except:
        #     print("couldn't add authors")

    return

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def proc_scopus_chunk(docs,q,update):
    django.db.connections.close_all()
    for d in docs:
        add_doc_text(d,q=q,update=update)
    django.db.connections.close_all()
    return

RIS_KEY_MAPPING = {
    'A1': 'au',
    'AB': 'ab',
    'AD': 'c1',
    'AN': 'accession_number',
    'AU': 'au',
    'C1': 'custom1',
    'C2': 'custom2',
    'C3': 'custom3',
    'C4': 'custom4',
    'C5': 'custom5',
    'C6': 'custom6',
    'C7': 'custom7',
    'C8': 'custom8',
    'CA': 'caption',
    'CN': 'call_number',
    'CY': 'pi',
    'DA': 'pd',
    'DB': 'datanase',
    'DO': 'di',
    'DP': 'database_provider',
    'EP': 'ep',
    'ER': 'er',
    'ET': 'edition',
    'ID': 'ut',
    'IS': 'ar',
    'J2': 'so',
    'JA': 'alternate_title2',
    'JF': 'alternate_title3',
    'JO': 'so',
    'KW': 'kwp',
    'L1': 'file_attachments1',
    'L2': 'file_attachments2',
    'L4': 'figure',
    'LA': 'la',
    'LB': 'label',
    'M1': 'note',
    'M3': 'type_of_work',
    'N1': 'notes',
    'N2': 'ab',
    'NV': 'number_of_Volumes',
    'OP': 'original_publication',
    'PB': 'pu',
    'PY': 'py',
    'RI': 'reviewed_item',
    'RN': 'research_notes',
    'RP': 'reprint_edition',
    'SE': 'version',
    'SN': 'sn',
    'SP': 'bp',
    'ST': 'short_title',
    'T1': 'ti',
    'T2': 'secondary_title',
    'T3': 'tertiary_title',
    'TA': 'translated_author',
    'TI': 'ti',
    'TT': 'translated_title',
    'TY': 'pt',
    'UK': 'unknown_tag',
    'UR': 'UT',
    'VL': 'vl',
    'Y1': 'py',
    'Y2': 'access_date'
 }

RIS_TY_MAPPING = {
    'B': 'BOOK',
    'Book Chapter': 'CHAP',
    'Book Section': 'CHAP',
    'Book section': 'CHAP',
    'J': 'JOUR',
    'Journal Article': 'JOUR',
    'Report': 'REPORT',
    'S': 'SER',
    'SER': 'SER',
    None: 'GEN'
}

def read_ris(q, update):
    with open(
        "{}/{}".format(settings.MEDIA_ROOT,q.query_file.name
    ),'r') as f:
        entries = readris(f,mapping=RIS_KEY_MAPPING)
        try:
            for e in entries:
                add_scopus_doc(e,q,update)
        except:
            with open(
                "{}/{}".format(settings.MEDIA_ROOT,q.query_file.name
            ),'r',encoding='utf-8-sig') as f:
                entries = readris(f,mapping=RIS_KEY_MAPPING)
                for e in entries:
                    add_scopus_doc(e,q,update)

def read_scopus(res, q, update):

    n_records = 0
    records= []
    record = []
    mfields = ['au','AF','CR','C1']

    max_chunk_size = 2000
    chunk_size = 0

    q.doc_set.clear()

    print(update)

    for line in res:
        if '\ufeff' in line: # BOM on first line
            continue
        if 'ER  -' in line:
            # end of record - save it and start a new one
            n_records +=1
            records.append(record)
            record = []

            chunk_size+=1
            if chunk_size==max_chunk_size:
                # parallely add docs
                #pool = Pool(processes=8)
                r_chunks = chunks(records, 8)
                #pool.map(partial(proc_scopus_chunk,q=q,update=update), r_chunks)
                for r in r_chunks:
                    proc_scopus_chunk(r,q=q,update=update)
                #pool.terminate()
                records = []
                chunk_size = 0
            continue
        if re.match("^EF",line): #end of file
            #done!
            continue
        record.append(line)

    print(chunk_size)

    if chunk_size < max_chunk_size and chunk_size > 0:
        # parallely add docs
        #pool = Pool(processes=1)
        r_chunks = chunks(records, 1)
        for r in r_chunks:
            proc_scopus_chunk(r,q=q,update=update)
        #pool.map(partial(proc_scopus_chunk,q=q, update=update), r_chunks)
        #pool.terminate()

    django.db.connections.close_all()

    return n_records

def wosify_scopus_ref(r):
    r = r.strip()
    if re.match('(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)',str(r)):
        s = re.search('(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)',str(r))
        tiau = re.split('([A-Z]\.), ',s.group(1))
        ti = tiau[-1].strip()
        a1 = s.group(1).split('.')[0].replace(',','')
        py = s.group(2)
        extra = s.group(3)
        so = extra.split(',')[0]

        wosref = "{}, {}, {}".format(a1, py, so)
    else:
        wosref = r

    return wosref

ars = [
    {"name":"AR0","years":range(0,1985),"n":0},
    {"name":"AR1","years":range(1985,1991),"n":1},
    {"name":"AR2","years":range(1991,1995),"n":2},
    {"name":"AR3","years":range(1995,2001),"n":3},
    {"name":"AR4","years":range(2001,2008),"n":4},
    {"name":"AR5","years":range(2008,2014),"n":5},
    {"name":"AR6","years":range(2014,9999),"n":6}
]
