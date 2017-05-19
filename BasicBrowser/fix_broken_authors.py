import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import csv
from urllib.parse import urlparse, parse_qsl

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def add_doc_text(r):

    record = {}
    mfields = ['AU']
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
                    nextkey = nextkey
                except:
                    pass

                if nextkey in mfields:
                    record[nextkey] = [nextvalue]
                else:
                    record[nextkey] = nextvalue

            try:
                key = key
            except:
                pass

            if key in record:
                if key in mfields:
                    record[key].append(value)
                else:
                    record[key] += value
            else:
                if key in mfields:
                    record[key] = [value]
                else:
                    record[key] = value




    try:
        record['scopus_id'] = dict(parse_qsl(urlparse(record['UR']).query))['eid']
        add_doc(record)
    except:
        print("don't want to add this record, it has no id!")
        #print(record)

def add_doc(r):
    django.db.connections.close_all()
    try:
        doc = Doc.objects.get(UT=r['scopus_id'])
        doc.docauthinst_set.all().delete()
        #print("deleted")
        ## Add authors
        try:
            if len(r['AU']) > 0:
                dais = []
                for a in range(len(r['AU'])):
                    #af = r['AF'][a]
                    au = r['AU'][a]
                    dai = DocAuthInst(doc=doc)
                    dai.AU = au
                    dai.position = a
                    dais.append(dai)

                    #dai.save()
                #print(dais)
                DocAuthInst.objects.bulk_create(dais)
        except:
            print("couldn't add authors")
    except:
        pass
    django.db.connections.close_all()






def main():
    qid = sys.argv[1]

    very_par = True
    ## Get query
    global q
    q = Query.objects.get(pk=qid)


    i=0
    n_records = 0
    records=[]
    if very_par == True:
        record = []
    else:
        record = {}

    max_chunk_size = 2000
    chunk_size = 0

    print(q.title)

    title = str(q.id)

    with open("/queries/"+title+"/s_results.txt", encoding="utf-8") as res:
        for line in res:
            if '\ufeff' in line: # BOM on first line
                continue
            if 'ER  -' in line:

                # end of record - save it and start a new one
                n_records +=1
                records.append(record)
                if very_par:
                    record = []
                else:
                    record = {}
                chunk_size+=1
                if chunk_size==max_chunk_size:
                    #print("doing chunk starting from record:")
                    #print(records[0])
                    # parallely add docs
                    pool = Pool(processes=32)
                    if very_par:
                        pool.map(add_doc_text, records)
                    else:
                        pool.map(add_doc, records)
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
        if very_par:
            pool.map(add_doc_text, records)
        else:
            pool.map(add_doc, records)
        pool.terminate()

    django.db.connections.close_all()
    q.r_count = len(Doc.objects.filter(query=q))
    q.save()


if __name__ == '__main__':
    t0 = time.time()
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
