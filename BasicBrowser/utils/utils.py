import django, re, gc
from django.conf import settings

from RISparser import readris
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl
import sys
import uuid
import short_url
from django.db import IntegrityError
from django.core.exceptions import FieldDoesNotExist
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
    from scoping.models import Citation, CDO
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
            else:
                if cobject.ftext != c:
                    if cobject.alt_text is None:
                        cobject.alt_text = [c]
                    else:
                        cobject.alt_text = cobject.alt_text.append(c)
            #otherise append to alt text
        else:
            try:
                cobject = Citation.objects.get(
                    ftext = c
                )
            except:
                try:
                    cobject = Citation.objects.get(
                        alt_text = c
                    )
                except:
                    try:
                        cobject = Citation(ftext=c)
                        cobject.save()
                    except:
                        print("!!ERROR saving!!")
                        print(c)
                        continue

        cdo = CDO(doc=doc,citation=cobject)
        cdos.append(cdo)
    return(cdos)


def shingle(text):
    return set(s for s in ngrams(text.lower().replace("-"," ").split(),2))

def get(r, k):
    try:
        x = r[k]
    except:
        try:
            x = r[k.upper()]
        except:
            x = None
    if k.upper()=="PY" and x is not None:
        try:
            x = int(x)
        except:
            x = "".join(re.findall("[0-9]",x))
    return(x)

def jaccard(s1,s2):
    try:
        return len(s1.intersection(s2)) / len(s1.union(s2))
    except:
        return 0


def add_doc(r, q, update):

    django.db.connections.close_all()

    ut, created = scoping.models.UT.objects.get_or_create(UT=r['UT'])

    #doc, created = Doc.objects.get_or_create(UT=r['UT'])

    if created==False and update==False:
        doc = ut.doc
        doc.query.add(q)
        #doc.projects.add(q.project)
    else:
        doc, created = scoping.models.Doc.objects.get_or_create(UT=ut)
        doc.title=get(r,'TI')
        if created:
            doc.tslug = scoping.models.Doc.make_tslug(doc.title)
        doc.content=get(r,'AB')
        doc.PY=get(r,'PY')
        doc.wos=True
        doc.save()
        doc.query.add(q)
        #doc.projects.add(q.project)
        article, created = scoping.models.WoSArticle.objects.get_or_create(doc=doc)
        try:
            r['wc'] = [x.strip() for x in get(r,'WC').split(";")]
        except:
            pass
        r['kwp'] = get(r,'ID')
        r['iss'] = get(r,'IS')
        # handle lists of emails
        if get(r, "EM") is not None:
            if "; " in get(r,'EM'):
                r["EMS"] = get(r, "EM").split("; ")
                r["EM"] = r["EMS"][0]
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
            print("Failed to save article for record", r)
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
            if af is None:
                continue
            for inst in r['C1']:
                inst = inst.split('] ',1)
                iauth = inst[0]
                # try:
                if len(inst) == 1:
                    if len(r['AU'])==1:
                        institute = inst
                        iauth = af
                    else:
                        institute = inst
                else:
                    institute = inst[1]
                if af in iauth:
                    try:
                        dai,created = scoping.models.DocAuthInst.objects.get_or_create(
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
                        print("{} {} {} {} {}".format(doc,au,af,institute,a+1))
                        dai,created = scoping.models.DocAuthInst.objects.get_or_create(
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
                try:
                    dai, created = scoping.models.DocAuthInst.objects.get_or_create(
                        doc=doc,
                        AU = au,
                        AF = af,
                        position = a+1
                    )
                    dai.save()
                except:
                    dais = scoping.models.DocAuthInst.objects.filter(
                        doc=doc,
                        AU = au,
                        AF = af,
                        position = a+1
                    )
                    if dais[0] != dais[1]:
                        pass
                    else:
                        print(dais.values_list('institution',flat=True))



        doc.authors = ', '.join([x.AU for x in doc.docauthinst_set.all().order_by('position')])
        try:
            doc.first_author = doc.docauthinst_set.all().order_by('position').first().AU
        except:
            print("failed to extract first author.")


def read_wos(res, q, update, deduplicate=False):
    from django.db import connection
    connection.close()
    if deduplicate:
        print("nonstandard WoS, searching for duplicates")
    i=0
    n_records = 0
    records=[]
    record = {}
    mfields = ['AU','AF','CR','C1','WC']

    max_chunk_size = 2000
    chunk_size = 0

    q.doc_set.clear()

    p=4

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
                if deduplicate:
                    print("adding as if scopus")#
                    pool = Pool(processes=1)
                    pool.map(partial(add_scopus_doc, q=q, update=update),records)
                else:
                    pool = Pool(processes=p)
                    pool.map(partial(add_doc, q=q, update=update),records)
                pool.terminate()
                records = []
                chunk_size = 0
            continue
        if re.match("^EF",line): #end of file
            if chunk_size < max_chunk_size:
                # parallely add doc
                #pool.map(update_doc, records)
                if deduplicate:
                    print("adding as if scopus")
                    from django.db import connection
                    connection.close()
                    pool = Pool(processes=1)
                    pool.map(partial(add_scopus_doc, q=q, update=update),records)
                else:
                    pool = Pool(processes=p)
                    pool.map(partial(add_doc, q=q, update=update),records)
                pool.terminate()
            #done!
            break
        if re.match("(^[A-Z][A-Z1-9]) (.*)",line):
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

    DEBUG=False

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
            if DEBUG: print("= IF / Key found! ============================================================")
            if DEBUG: print(line)
            s = re.search("([A-Z][A-Z1-9])(\s{2}-\s*)(.*)",line)
            if DEBUG: print(s)
            key = s.group(1).strip()
            if DEBUG: print(key)
            value = s.group(3).strip()
            if DEBUG: print(value)
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

            if DEBUG: print("= N1 ============================================================")
            if key=="N1":
                if DEBUG: print("= N1 ============================================================")
                s = re.search("([a-zA-Z1-9 ]*): *(.*)",value)
                if DEBUG: print(s)
                try:
                    key = s.group(1).strip()
                    value = s.group(2).strip()
                    if DEBUG: print(key)
                    if DEBUG: print(value)
                except:
                    print(key)
                    print(value)

            if DEBUG: print("= scopus2WoSFields ============================================================")
            try:
                key = scopus2WoSFields[key]
                if DEBUG: print("try...")
                if DEBUG: print(key)
            except:
                if DEBUG: print("except...")
                if DEBUG: print(key)
                pass


            if DEBUG: print("= key in mfields ============================================================")
            if key in mfields:
                if DEBUG: print("  > True")
                if key in record:
                    if DEBUG: print("    > Key already in record. Appending...")
                    record[key].append(value)
                else:
                    if DEBUG: print("    > Key not in record. Adding...")
                    record[key] = [value]
            else:
                if DEBUG: print("  > False")
                if key in record:
                    if DEBUG: print("    > Key already in record. Appending...")
                    record[key] += "; " + value
                else:
                    if DEBUG: print("    > Key not in record. Adding...")
                    record[key] = value

        elif len(line) > 1:
            if DEBUG: print("= ELIF / Key not found! ============================================================")
            if DEBUG: print(line)
            if key in mfields:
                if DEBUG: print("  > Key in mfields. Appending...")
                record[key].append(line.strip())
            else:
                if DEBUG: print("  > Key not in mfields. Adding...")
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
    doc = None
    try:
        doc = scoping.models.Doc.objects.get(UT__sid=r['UT'])
    except:
        docs = scoping.models.Doc.objects.filter(UT__sid=r['UT']) | scoping.models.Doc.objects.filter(UT__UT=r['UT'])
        if docs.count()==1: # If it's just there - great!
            doc = docs.first()
        elif docs.count() > 1:
            print("OH no! multiple matches!")
        elif scoping.models.UT.objects.filter(UT=r['UT'],doc__isnull=True).exists():
            scoping.models.UT.objects.filter(UT=r['UT'],doc__isnull=True).delete()
    return doc

def find_with_url(r):
    url, created = scoping.models.URLs.objects.get_or_create(
        url=r['url']
    )
    surl = short_url.encode_url(url.id)
    try:
        ut = scoping.models.UT.objects.get(UT=surl)
        doc = ut.doc
        #print("found with ID")
    except:
        doc = None
    return doc

def add_scopus_doc(r,q,update):
    from django.db import connection
    connection.close()
    doc = None
    try:
        r['UT'] = dict(parse_qsl(urlparse(r['UT']).query))['eid'].strip()
    except:
        if 'UT' not in r or r['UT'] is None:
            if get(r, 'url') is not None:
                r['UT'] = r['url']
            else:
                r['UT'] = str(uuid.uuid1())
        else:
            print(r['UT'])
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

        if get(r,'ti') is None or len(get(r,'ti')) < 2:
            print(f"<p>This document ({r}) has no title!! ")
            q.upload_log+=f"<p>This document ({r}) has no title!! "
            q.save()
            return

        tslug=scoping.models.Doc.make_tslug(get(r,'ti'))
        
        if did=='NA':
            docs = scoping.models.Doc.objects.filter(
                    tslug=tslug,
                    PY=get(r,'py')
            )
            if not docs.exists() and get(r,'au') is not None:
                if len(get(r,'au')) > 0:
                    docs = scoping.models.Doc.objects.filter(
                        tslug=tslug,
                        docauthinst__AU__icontains=get(r,'au')[0].split(',')[0]
                    ).distinct('pk')

        else:
            docs = scoping.models.Doc.objects.filter(
                wosarticle__di=did
            )

            if not docs.exists():

                docs = scoping.models.Doc.objects.filter(
                        tslug=tslug,
                        PY=get(r,'py')
                )
                if not docs.exists() and get(r,'au') is not None:
                    if len(get(r,'au')) > 0:
                        docs = scoping.models.Doc.objects.filter(
                            tslug=tslug,
                            docauthinst__AU__icontains=get(r,'au')[0].split(',')[0]
                        ).distinct('pk')


        if len(docs)==1:
            #print("found! with doi or ti and authors")
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
            #print("looking with jaccard similarity and so on")
            s1 = shingle(get(r,'ti'))

            twords = get(r,'ti').split()
            if len(twords) > 1:
                twords = ' '.join([x for x in twords[0:1]])
            else:
                twords = twords[0]

            py_docs = scoping.models.Doc.objects.filter(
                PY=get(r,'py'),
                title__iregex='\w',
                title__icontains=twords,
                docproject__project=q.project
            )
            print(py_docs.count())
            doc = None
            for d in py_docs.iterator():
                j = jaccard(s1,d.shingle())
                if j > 0.51:
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
            if created:
                doc.tslug = tslug
                doc.save()
            
    if doc is not None:
        if doc.query.filter(pk=q.id).exists():
            q.upload_log+=f"<p>This document ({doc.title}) is considered an internal duplicate of ({get(r,'ti')}) "
            q.save()
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

        try:
            doc.query.add(q)
        except IntegrityError as e:
            print("already in there")

        #doc.projects.add(q.project)
    if doc is not None and "WOS:" not in str(doc.UT.UT):
        if update:
            doc.title=get(r,'ti')
            doc.content=get(r,'ab')
            doc.PY=get(r,'py')
            doc.save()

            for field in r:
                try:
                    f = article._meta.get_field(field.lower())
                    if f.max_length is None or f.max_length > len(r[field]):
                        if f.get_internal_type() != 'ArrayField' and type(r[field]) == list:
                            setattr(article,f.name,'; '.join(r[field]))
                        else:
                            setattr(article,f.name,get(r,f.name))
                except FieldDoesNotExist:
                    # Field in data but not in model
                    pass
                    #print(field)
                    #print(r[field])


            try:
                article.save()

            except:
                article.save()
                pass


            ## Add authors
            #try:
            dais = []
            if get(r,'au') is not None:
                doc.docauthinst_set.clear()
                for a in range(len(get(r,'au'))):
                    #af = r['AF'][a]
                    au = get(r,'au')[a]
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
    'DB': 'database',
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
    'KW': 'de',
    'L1': 'file_attachments1',
    'L2': 'file_attachments2',
    'L4': 'figure',
    'LA': 'la',
    'LB': 'label',
    'M1': 'note',
    'M3': 'pt',
    'M4': 'source',
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
    'Y2': 'access_date',
    'References': 'cr',
    'Funding details': 'fu',
    'Funding text': 'fx',
    'Correspondence Address': 'em',
    'Cited By ': 'tc',
    'Cited By': 'tc',
    'Link to the Ovid Full Text or citation': 'ol'
 }

RIS_TY_MAPPING = {
    'B': 'BOOK',
    'BOOK': 'BOOK',
    'Book Chapter': 'CHAP',
    'Book Section': 'CHAP',
    'Book section': 'CHAP',
    'J': 'JOUR',
    'JOUR': 'JOUR',
    'CONF': 'CONF',
    'INPR': 'INPR',
    'Journal Article': 'JOUR',
    'Report': 'REPORT',
    'S': 'SER',
    'SER': 'SER',
    'CASE': 'CASE',
    'ABST': 'ABST',
    'THES': 'THES',
    'RPRT': 'RPRT',
    'UNPB': 'UNPB',
    None: 'GEN',
}

def read_ris(q, update):
    r_count = 0
    changed = False
    encoding = None
    with open(
        "{}/{}".format(settings.MEDIA_ROOT,q.query_file.name
    ),'r') as f:
        with open(
            "{}/{}_tmp".format(settings.MEDIA_ROOT,q.query_file.name), "w"
        ) as ftmp:
            for l in f:
                if "\\ufeff" in repr(l) or "\ufeff" in repr(l):
                    #encoding = 'utf-8-sig'
                    changed = True
                    ftmp.write(l.replace('\\ufeff','').replace('\ufeff',''))
                elif l == "EF":
                    changed=True
                elif "Link to the Ovid Full Text or citation:" in l:
                    changed=True
                elif re.compile('^[A-Z][A-Z0-9]  -\n').match(l):
                    changed = True
                    ftmp.write(l.replace('-\n','- \n'))
                else:
                    ftmp.write(l)
    if changed:
        print("opening edited file")
        fpath = "{}/{}_tmp".format(settings.MEDIA_ROOT,q.query_file.name)
    else:
        fpath = "{}/{}".format(settings.MEDIA_ROOT,q.query_file.name)

    with open(fpath, "r", encoding = encoding) as f:
        entries = readris(f,mapping=RIS_KEY_MAPPING)
        try:
            for e in entries:
                if "py" in e:
                    if type(e["py"] is str):
                        try:
                            e["py"] = int(e["py"][:4])
                        except:
                            print(f"cannot convert {e['py']} into string")
                            e["py"] = None
                if "unknown_tag" in e:
                    del e["unknown_tag"]
                try:
                    add_scopus_doc(e,q,update)
                    r_count+=1
                except:
                    print(f"couldn't add {e}")
                    return e

        except:
            r_count = 0
            with open(fpath,'r',encoding='utf-8-sig') as f:
                entries = readris(f,mapping=RIS_KEY_MAPPING)
                for e in entries:
                    if "py" in e:
                        if type(e["py"] is str):
                            try:
                                e["py"] = int(e["py"][:4])
                            except:
                                print(f"cannot convert {e['py']} into string")
                                e["py"] = None
                    if "tc" in e:
                        if type(e["tc"] is str):
                            digits = re.findall(r"\d+",e["tc"])
                            if len(digits) > 0:
                                e["tc"] = int(digits[0])
                            else:
                                e["tc"] = None
                    if "unknown_tag" in e:
                        del e["unknown_tag"]

                    try:
                        add_scopus_doc(e,q,update)
                        r_count+=1
                    except:
                        print(f"couldn't add {e}")
                        break
    return r_count

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
