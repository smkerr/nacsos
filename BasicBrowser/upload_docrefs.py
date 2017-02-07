import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def get(r, k):
    try:
        x = r[k]
    except:
        x = ""
    return(x)

def add_doc(r):

    django.db.connections.close_all()
    try: # if this doc is in the database, do nothing
        doc = Doc.objects.get(UT=r['UT'])
        doc.query.add(q)
    except: # otherwise, add it!
        doc = Doc(UT=r['UT'])
        doc.title=get(r,'TI')
        doc.content=get(r,'AB')
        doc.PY=get(r,'PY')
        doc.save()
        doc.query.add(q)
        article = WoSArticle(doc=doc)
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
        for a in range(len(r['AF'])):
            af = r['AF'][a]
            au = r['AU'][a]
            if 'C1' not in r:               
                r['C1'] = [""]
            a_added = False
            for inst in r['C1']:
                inst = inst.split('] ',1)
                iauth = inst[0]
                try:
                    institute = inst[1]
                    if af in iauth:
                        dai = DocAuthInst(doc=doc)
                        dai.AU = au
                        dai.AF = af
                        dai.institution = institute
                        dai.position = a+1
                        dai.save()
                        a_added = True
                except:
                    pass # Fix this later, these errors are caused by multiline institutions
            if a_added == False:
                dai = DocAuthInst(doc=doc)
                dai.AU = au
                dai.AF = af
                dai.position = a
                dai.save()

############################################################################
############################################################################
## NEW PART TO DEAL WITH REFERENCES

    # Now that the article's saved, we can look at the references....
    # these are in a list accessible by get(r,'CR')
    refs = get(r,'CR')
    for r in refs:
        #print(r)
        # Add them to a table of docs to references (a simple table of just the dois)
        dr = DocReferences(doc=doc)
        dr.refall = r
        try: # try and get the doi if it's there
            doi = re.search(", DOI ([^ ]*)",r).group(1)
            doi = re.sub('^\[','',doi) ## This is to deal with lists !! of dois
            dr.refdoi=doi
            #print(doi)
            # Is this document already in our database?????
            doidoc = Doc.objects.filter(wosarticle__di=doi)
            if len(doidoc) > 0:
                print(doidoc)
                doidoc = doidoc.first()
                doc.references.add(doidoc)
                doc.save() # If so, create the link already!
            else: # otherwise, add it to a list of docs to lookup
                doi_lookups.append(doi)
        except: 
            pass 
        dr.save() #uncomment this when we want to actually save these


        # We can access a documents references by doc.references.all()
        # And get its citations by doc.doc_set.all()
        
#############################################################################
#############################################################################
#############################################################################           
        

def main():
    qid = sys.argv[1]

    ## Get query
    global q
    q = Query.objects.get(pk=qid)

    #Doc.objects.filter(query=qid).delete() # doesn't seem like a good idea

    i=0
    n_records = 0
    records=[]
    record = {}
    mfields = ['AU','AF','CR','C1']

    global doi_lookups # make a list of dois to lookup (global so accessible inside the parallel function)
    doi_lookups = []

    max_chunk_size = 2000
    chunk_size = 0

    print(q.title)

    title = str(q.id)

    with open("/queries/"+title+"/results.txt", encoding="utf-8") as res:
        for line in res:
            if '\ufeff' in line: # BOM on first line
                continue
###############################
#### Don't do this parellely anymore, just one at a time is easier here.
            if line=='ER\n':   
                # end of record - add whatever is currently in record
                add_doc(record)
                n_records +=1
                record = {} 
               
           
                records.append(record)
                continue
            if re.match("^EF",line): #end of file, stop now
                break
            # if the beginning of the line starts with a field key, start a new field
            # otherwise, add whatever is in the line to the current field
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
                    record[key] += line.strip()
    
    django.db.connections.close_all()
    q.r_count = n_records
    q.save()

    ############ When happy with the script we can uncomment and delete the files again

    #shutil.rmtree("/queries/"+title)
    #os.remove("/queries/"+title+".txt")
    #os.remove("/queries/"+title+".log")

    doiset = set(doi_lookups) # unique values
    print(len(doiset))
    query = 'DO = ("' + '" OR "'.join(doiset) + '")'
    print(query)

    ## Now we can write this to a text file and continue......

    


if __name__ == '__main__':
    t0 = time.time()	
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
