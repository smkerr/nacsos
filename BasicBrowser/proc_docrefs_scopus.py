import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl

from django.utils import timezone
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

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

def add_doc(r):

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
        'References': '',
        'UR': 'UT', # use url as ut, that's the only unique identifier...
        'PB': ''
        #'ER': , #End record

    }

#    if request.session.get('DEBUG', None) == None:
    DEBUG = False
#    else:
#        DEBUG = request.session['DEBUG'] 

    if DEBUG:
        print("  >> Entering add_doc() with document id: "+str(r['UT']))

    django.db.connections.close_all()
    if Doc.objects.filter(UT=r['UT']).count() == 1:
        doc = Doc.objects.get(UT=r['UT'])
        if DEBUG:
            print("     > Document is already in the DB. Add to query table only.")
        doc.query.add(q)
        doc.save()
    else:   #look for nonexact matches!
        if DEBUG:
            print("     > Looking for nonexact matches.")
        try:
            did = r['DO']    
            if DEBUG:
                print("     > Found a doi!: %s" % did) 
        except:
            did = 'NA'
            pass

        if did=='NA':
            docs = Doc.objects.filter(
                    wosarticle__ti=get(r,'ti')).filter(PY=get(r,'PY')
            )
        else: 
            docs = Doc.objects.filter(wosarticle__di=did)

        if len(docs)==1:
            doc = docs.first()
            doc.query.add(q)
            if DEBUG:
                print("     > Found an exact match!.") 
        if len(docs)>1:
            if DEBUG:
                print("     > Found more than one match (uhoh) Here they are!.") 
            for d in docs:
                print(d.title)
                print(d.UT)
        if len(docs)==0:
            #print("no matching docs")
            if DEBUG:
                print("     > Found no exact matches, computing jaccard similarity for wos docs from same year") 
            s1 = shingle(get(r,'ti'))
            py_docs = Doc.objects.filter(PY=get(r,'PY'))
            docs = []
            for d in py_docs:
                j = jaccard(s1,d.shingle())
                if j > 0.51:
                    d.query.add(q)
                    return
        if len(docs)==0:
            doc = Doc(UT=r['UT'])
            #print(doc)
            doc.title=get(r,'TI')
            doc.content=get(r,'AB')
            doc.PY=get(r,'PY')
            doc.save()
            doc.query.add(q)
            doc.save()
            article = WoSArticle(doc=doc)


            for field in r:
                try:
                    f = scopus2WoSFields[field]
                except:
                    f = field
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
                for a in range(len(r['AU'])):
                    #af = r['AF'][a]
                    au = r['AU'][a]  
                    dai = DocAuthInst(doc=doc)
                    dai.AU = au
                    dai.position = a
                    dais.append(dai)
                    #dai.save()
                DocAuthInst.objects.bulk_create(dais)
            except:
                print("couldn't add authors")


############################################################################
############################################################################
## NEW PART TO DEAL WITH REFERENCES

    # Now that the article's saved, we can look at the references....
    # these are in a list accessible by get(r,'CR') 
    if q == q3: # When we are dealing with citations, we want to check each one's refs for the seed docs.....
        refs = get(r,'References')
        print(len(refs))
        seedtitles = [x.title for x in q1.doc_set.all()]
        print(seedtitles)
        for ref in refs:
            for st in seedtitles:
                if st.lower() in ref.lower(): # if any of the seedtitles are references, create a docrel object
                    print("found seed")
                    sdoc = Doc.objects.get(query=q1,title=st)
                    try:
                        dr = DocRel.objects.get(seed=sdoc,text=doc.title,seedquery=q1)
                    except:
                        dr = DocRel(seed=sdoc,text=doc.title,seedquery=q1)
                    dr.relation = 1
                    dr.title=doc.title
                    dr.referent=doc
                    # Is it already in the db? What technologies is it associated with?
                    if doc.query.exclude(id=q3.id).count() > 0:
                        dr.indb = 1
                        dtechs = [x.technology for x in doc.query.filter(type='default')]
                        if q1.technology in dtechs:
                            dr.sametech = 1
                        else:
                            dr.sametech = 0
                    else:
                        dr.indb = 2

                    dr.save()
    elif q == q2:
        r = DocRel.objects.filter(seedquery=q1,text__icontains=doc.title)
        if r.count() == 1:
            dr = r.first()
            dr.referent=doc
            dr.indb = 2
            dr.save
        if r.count() > 1:
            print(r.values())
    elif q == q1:
        refs = get(r,'References')
        if len(refs) > 0:
            if DEBUG:
                print("     > The document has the following references:")
            skip = 0
            doi_lookups_loc = []
            au_lookups_loc  = []
            py_lookups_loc  = []
            so_lookups_loc  = []
            for r in refs:
                if DEBUG:
                    print("       - "+str(r))
                #print(r)
                # Add them to a table of docs to references (a simple table of just the dois)
                try:
                    dr = DocRel.objects.get(seed=doc,text=r,seedquery=q)
                except:
                    dr = DocRel(seed=doc,text=r,seedquery=q)
                    dr.relation = -1
                    dr.save()

            
                if r[0] == "*":
                    if DEBUG:
                        print("         > Skipping (special document)")
                    skip+=1
                    continue

                doi = False
                # Try to get DOI
                if re.match('(.*)DOI:? (.*)',r):
                    DOI = re.search('DOI:? (.*)',r)
                    doi = DOI.group(1)
                elif re.match('.*, doi:([^ ]*)',r):
                    DOI = re.search(", doi:([^ ]*)",r)
                    doi = DOI.group(1)

                    if "a"=="B":
                        doidoc = Doc.objects.filter(wosarticle__di=doi)
                        if len(doidoc) > 0:
                            if DEBUG:
                                print("         . DOI exists in DB! Add reference to doc and query2.")
                            doidoc = doidoc.first()
                            doc.references.add(doidoc)
                            doc.save() # If so, create the link already!

                            # Add to query
                            doidoc.query.add(q2)
                            doidoc.save()
        
                        else: # otherwise, add it to a list of docs to lookup
                            if DEBUG:
                                print("         . DOI not in DB! Add to lookup list.")
                            doi_lookups.append(doi)
                            doi_lookups_loc.append(doi)                 
                else: 
                    if DEBUG:
                        print("         . No DOI found for this record. Skipping...")
                    skip+=1
                    pass 

                if doi:
                    dr.doi=doi
                    dr.hasdoi=True

                # Try to get AU, PY & TI
                try: # try and get the fields
                    ypat = '(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)'

                    au = ""
                    so = ""
                    py = ""
                    ti = ""
                    if re.match(ypat,r):
                        s = re.search('(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)',str(r))
                        tiau = re.split('([A-Z]\.), ',s.group(1))
                        ti = tiau[-1].strip()
                        dr.title=ti
                        aul = tiau[0:-1]
                        au = '; '.join([ ''.join(x) for x in zip(aul[0::2], aul[1::2]) ])
                        py = s.group(2)
                        extra = s.group(3)
                        so = extra.split(',')[0]

                    regurl = '(?:.*)(https?://[^\s,]+)'
                    if re.match(regurl,r):
                        dr.url = re.search(regurl,r).group(1)

                    #print(au)
                    #print(ti)    
                    print(extra)
                    flag_problem = False

                    

                    # Check validity of fields
                    test_au = re.match("([a-zA-Z\.\,; ]*$)", au) is not None
                    if not test_au:
                        flag_problem = True
                        if DEBUG:
                            print("         . AU doesn't look correct "+" (AU: "+str(au)+")")
                    else:
                        dr.au = au
                    if not py.isdigit():
                        flag_problem = True
                        if DEBUG:
                            print("         . PY field is not a numeric "+" (PY: "+str(py)+")")
                    else:
                        dr.PY=py
                    test_so = re.match("^([a-zA-Z0-9&.: ]*)$", so) is not None
                    if not test_so:
                        flag_problem = True
                        if DEBUG:
                            print("         . SO field doesn't look correct "+" (SO: "+str(so)+")")
                    if DEBUG:
                        print("         . AU: "+str(au)+"("+str(test_au)+"), PY: "+str(py)+" ("+str(py.isdigit())+") and SO:"+str(so)+" ("+str(test_so)+")")
                    if flag_problem:
                        if DEBUG:
                            print("         . Problem with one of the fields. Skipping...")  

                except:
                    if DEBUG:
                        print("         . Current reference has less than 3 fields. Skipping...")
                    skip+=1
                pass
                dr.save() #uncomment this when we want to actually save these
           
            refindb = len(refs) - skip - len(doi_lookups_loc) 
     
            global totnbrefs
            global totnbrefsindb
            global totnbskips

            totnbrefs     += len(refs)
            totnbrefsindb += refindb
            totnbskips    += skip

            if DEBUG:
                print("      > Number of references              : "+str(len(refs)))
                print("      > Number of discarded references (%): "+str(skip)+" ("+str(skip/len(refs)*100)+"%)")
                print("      > Number of references in DB (%)    : "+str(refindb)+" ("+str(skip/len(refs)*100)+"%)")
                print("      > Number of references to scrape (%): "+str(len(doi_lookups_loc))+" ("+str(len(doi_lookups_loc)/len(refs)*100)+"%)")

                # We can access a documents references by doc.references.all()
                # And get its citations by doc.doc_set.all()

        else :
            print("     > The document has no references!")

    if DEBUG:
        print("  << Exiting add_doc()")

#############################################################################
##



def add_doc_text(r):
    record = {}
    mfields = ['au','AF','CR','C1','References']
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
            
            if key in mfields:
                record[key] = [value]
            else:
                record[key] = value

        elif len(line) > 1:
            if key in mfields:
                record[key].append(line.strip())
            else:
                record[key] += line.strip()

    record['UT'] = dict(parse_qsl(urlparse(record['UR']).query))['eid'] 
    add_doc(record)
    try:
        record['UT'] = dict(parse_qsl(urlparse(record['UR']).query))['eid'] 
        #add_doc(record)
    except:
        print("don't want to add this record, it has no id!")
        print(record)
        return


#############################################################################
##
def matchref(dr):
    django.db.connections.close_all()
    if dr.hasdoi:
        r = Doc.objects.filter(wosarticle__di=dr.doi)
    elif len(dr.title)>10:
        r = Doc.objects.filter(title__icontains=dr.title)
    else:
        return
    if r.count() > 1:
        print(r.values('title','UT'))
        print(r.count())
        print(dr.title)
        print(dr.au)
    if r.count()==1:
        d = r.first()
        dr.referent = d
        dr.indb = 1
        print("indb")
        dtechs = [x.technology for x in d.query.all()] + list(d.technology.all())
        if q.technology in dtechs:
            dr.sametech = 1
        else:
            dr.sametech = 0
        dr.save()

        
#############################################################################
#############################################################################
#############################################################################           
        

def main():

    index_kws = False

    if index_kws:
        KW.objects.all().delete()
        i = 0
        for d in Doc.objects.filter(wosarticle__de__isnull=False):
            i+=1
            if i > 100000000000000:
                break
            if len(d.wosarticle.de.split('; ')) > 0:
                for k in d.wosarticle.de.split('; '):
                    k = k.lower()
                    try:
                        kw = KW.objects.get(text=k)
                    except:
                        kw = KW(text=k)
                        kw.save()
                    kw.doc.add(d)
                    kw.ndocs+=1
                    kw.save() 
    
    DEBUG = True
    DOI_ONLY = True

    if DEBUG:
        print(">> Entering main() function in upload_docrefs.py")

    # Get query ID from kwargs
    qid  = sys.argv[1] # Query containing list of documents
    q2id = sys.argv[2] # Query containing list of references
    q3id = sys.argv[3] # Query containing list of citations

    if DEBUG:
        print("  - The document query has the following ID: "+str(qid))
        print("  - The reference query has the following ID: "+str(q2id))

    ## Get queries
    global q1
    if qid != '0':
        q1 = Query.objects.get(pk=qid)
    global q2
    q2 = Query.objects.get(pk=q2id)
    global q3 
    if q3id != '0':
        q3 = Query.objects.get(pk=q3id)
    else:
        q3 = 0
    global dorefs


    i         = 0
    n_records = 0
    records   = []
    record    = {}
    mfields   = ['AU','AF','CR','C1']

    global doi_lookups # make a list of dois to lookup (global so accessible inside the parallel function)
    global au_lookups
    global py_lookups
    global so_lookups
    global totnbrefs
    global totnbrefsindb
    global totnbskips

    totnbrefs     = 0
    totnbrefsindb = 0
    totnbskips    = 0
 
    doi_lookups   = []
    au_lookups    = []
    py_lookups    = []
    so_lookups    = []


    max_chunk_size = 2000
    chunk_size = 0

    global q
    q = q1
    if q3id == '0':
        q = q2
    title = str(q.id)
    dorefs = True
    record = []
    # Open results file and loop over lines
    with open("/queries/"+title+"/s_results.txt", encoding="utf-8") as res:
        for line in res:
            if '\ufeff' in line: # BOM on first line
                continue
            ###############################
            #### Don't do this parellely anymore, just one at a time is easier here.
            if 'ER  -' in line:   # end of record - save it and start a new one                               
                n_records +=1            
                add_doc_text(record)
                record = []
                continue
            if re.match("^EF",line): #end of file
                #done!
                #break # We added files together, so there will be multiple EFs
                continue 
            record.append(line)
    
    django.db.connections.close_all()
    q.r_count = n_records
    q.save()

    ############ When happy with the script we can uncomment and delete the files again

    #shutil.rmtree("/queries/"+title)
    #os.remove("/queries/"+title+".txt")
    #os.remove("/queries/"+title+".log")

    print("  > Total Number of references processed    : "+str(totnbrefs))
    print("  > Total Number of references in DB (%)    : "+str(totnbrefsindb)+" ("+str(totnbrefsindb/totnbrefs*100)+"%)")
    print("  > Total Number of references to scrape (%): "+str(len(doi_lookups))+" ("+str(len(doi_lookups)/totnbrefs*100)+"%)")
    print("  > Total Number of discarded references (%): "+str(totnbskips)+" ("+str(totnbskips/totnbrefs*100)+"%)")


    ####################
    ## These are the backwards docref objects
    drs = DocRel.objects.filter(seed__query=q,relation=-1)  

    if q3 == 0:
        drs = drs.filter(indb=2)  

    # Process docs with dois
    refdois = drs.filter(seedquery=q,hasdoi=True)
    
    # Look for the no dois in the database
    # Match them with a referent and see if they match the tech
    nodois = drs.filter(seedquery=q,hasdoi=False,title__isnull=False,relation=-1)
    pool = Pool(processes=4)
    #pool.map(partial(matchref,),drs)
    pool.terminate()
    django.db.connections.close_all()

    if q3id != '0':

        ##############################################################
        ## Write Q2 query
        ldocs = DocRel.objects.filter(seedquery=q,referent__isnull=True) # no referent!
        indocs = DocRel.objects.filter(seedquery=q,referent__isnull=False)
        print(ldocs.count())
        print(indocs.count())

        qtext = ""
        i = 0
        for l in ldocs:
            if l.hasdoi:
                if i > 0:
                    qtext+=" OR "
                i+=1
                qtext += '(DOI("{}")'.format(l.doi)            
            elif len(l.title) > 10 and len(str(l.PY)) > 0:
                if i > 0:
                    qtext+=" OR "
                i+=1
                qtext += '(TITLE("{}") AND PUBYEAR IS {})'.format(l.title, l.PY)

        q2.text=qtext
        q2.save()

        print(qtext)

        ###############################################################
        ## Parse the Citations now!
        global q
        q = q3
        title = str(q.id)
        print(title)
        dorefs = False
        record = []
        # Open results file and loop over lines
        with open("/queries/"+title+"/s_results.txt", encoding="utf-8") as res:
            for line in res:
                if '\ufeff' in line: # BOM on first line
                    continue
                ###############################
                #### Don't do this parellely anymore, just one at a time is easier here.
                if 'ER  -' in line:   # end of record - save it and start a new one                               
                    n_records +=1            
                    add_doc_text(record)
                    record = []
                    continue
                if re.match("^EF",line): #end of file
                    #done!
                    #break # We added files together, so there will be multiple EFs
                    continue 
                record.append(line)
        
        django.db.connections.close_all()
        q.r_count = n_records
        q.save()
        ##
        ###############################################################

    ## Look for the title in notechmatches
    ## 
    # kws is a list of keywords that are the keywords of the seed documents
    kws = [x.text for x in [item for sublist in [x.kw_set.all() for x in q1.doc_set.all()] for item in sublist]]
    for dr in DocRel.objects.filter(seedquery=q1,referent__isnull=False).exclude(sametech=1):
        kmatch = False
        # Get a list of keywords for the doc
        dkws = [x.text for x in dr.referent.kw_set.all()]
        for kw in kws:
            if kw in dr.referent.title or kw in dr.referent.content or kw in dkws:
                kmatch = True
                dr.docmatch_q=True
                dr.sametech=2
        dr.save()


    if DEBUG:
        print("<< Exiting main() function in upload_docrefs.py")


if __name__ == '__main__':
    t0 = time.time()	
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
