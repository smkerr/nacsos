import django, re, gc

from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl
import sys



from scoping.models import *
from tmv_app.models import *

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
        x = ""
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
    else:
        doc, created = Doc.objects.get_or_create(UT=ut)
        doc.title=get(r,'TI')
        doc.content=get(r,'AB')
        doc.PY=get(r,'PY')
        doc.wos=True
        doc.save()
        doc.query.add(q)
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

        article.save()


        ## Add authors
        # try:
        if get(r,'AU') == "":
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

def add_doc_text(r,q):

    scopus2WoSFields = {
        'TY': 'dt',
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
        'References': 'CR',
        'UR': 'UT', # use url as ut, that's the only unique identifier...
        'PB': ''
        #'ER': , #End record

    }

    record = {}
    mfields = ['au','AF','CR','C1']
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
                record[key] = [value]
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
    add_scopus_doc(record,q)

def add_scopus_doc(r,q):
    django.db.connections.close_all()
    doc = None
    try:
        r['UT'] = dict(parse_qsl(urlparse(r['UT']).query))['eid']
    except:
        print(r)
        return

    docs = Doc.objects.filter(UT=r['UT'])
    if docs.count()==1: # If it's just there - great!
        doc = docs.first()
        article = WoSArticle(doc=doc)
        article.save()
        try:
            if doc.wosarticle.cr is None and get(r,'cr') is not None:
                doc.wosarticle.cr = r['CR']
                doc.wosarticle.save()
                doc.save()
        except:
            pass
        doc.query.add(q)
        #return

    else: # Otherwise try and match by doi
        try:
            did = r['di']
        except:
            did = 'NA'
            pass

        if did=='NA':
            docs = Doc.objects.filter(
                    wosarticle__ti=get(r,'ti')).filter(PY=get(r,'py')
            )
        else:
            docs = Doc.objects.filter(wosarticle__di=did)


        if len(docs)==1:
            docs.first().query.add(q)
            doc = docs.first()
        if len(docs)>1: # if there are two, that's bad!
            print("more than one doc matching!!!!!")
            for d in docs:
                print(d.title)
                print(d.UT)
        if len(docs)==0: # if there are none, try with the title and jaccard similarity
            #print("no matching docs")
            s1 = shingle(get(r,'ti'))
            py_docs = Doc.objects.filter(PY=get(r,'py'))
            docs = []
            for d in py_docs:
                j = jaccard(s1,d.shingle())
                if j > 0.51:
                    d.query.add(q)
                    doc = d
                    docs = Doc.objects.filter(UT=doc.UT)
                    break

        if len(docs)==0: # if there's still nothing, create one
            doc = Doc(UT=r['UT'])
            #print(doc)

    if doc is not None and "WOS:" not in doc.UT:

        print("UPDATING")
        doc.title=get(r,'ti')
        doc.content=get(r,'ab')
        doc.PY=get(r,'py')
        doc.save()
        doc.query.add(q)
        doc.save()
        article, created = WoSArticle.objects.get_or_create(doc=doc)


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
        try:
            dais = []
            for a in range(len(r['au'])):
                #af = r['AF'][a]
                au = r['au'][a]
                dai = DocAuthInst(doc=doc)
                dai.AU = au
                dai.position = a
                dais.append(dai)
                #dai.save()
            DocAuthInst.objects.bulk_create(dais)
        except:
            print("couldn't add authors")

def read_scopus(res, q, update):

    n_records = 0
    records= []
    record = []
    mfields = ['au','AF','CR','C1']

    max_chunk_size = 2000
    chunk_size = 0

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
                pool = Pool(processes=32)
                pool.map(add_doc_text, records)
                pool.terminate()
                records = []
                chunk_size = 0
            continue
        if re.match("^EF",line): #end of file
            #done!
            continue
        record.append(line)

    print(chunk_size)

    if chunk_size < max_chunk_size:
        # parallely add docs
        pool = Pool(processes=32)
        pool.map(partial(add_doc_text, q=q), records)
        pool.terminate()

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
