import sys, csv, django, os, codecs, re, fnmatch

sys.path.append('/home/galm/software/django/tmv/BasicBrowser')

# sys.path.append('/home/max/Desktop/django/BasicBrowser/')
import db as db
from tmv_app.models import *
from scoping.models import *
from scoping.views import *

from utils.utils import *
from utils.text import *
import xml.etree.ElementTree as ET
import pandas as pd
import short_url


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

def parse_par(el):
    dict = el.attrib
    for key in dict:
        try:
            dict[key] = float(dict[key])
        except:
            dict[key] = dict[key]
    dict['text'] = el.text
    return dict

def parse_document(f, doc):
    tree = ET.parse(f)
    root = tree.getroot()

    # Get paragraphs into a dataframe (using parse_par function)
    pages = root.findall('pages/page')
    pars = list(flatten([p.findall('paragraph') for p in pages]))
    par_df = pd.DataFrame.from_dict([parse_par(el) for el in pars])

    # Calculate some things
    par_df['height'] = par_df['maxY'] - par_df['minY']
    par_df['width'] = par_df['maxX'] - par_df['minX']
    par_df['text_length'] = par_df['text'].str.len()

    # Here are some attributes
    attribs = ['mostCommonFont', 'mostCommonFontsize','mostCommonColor']

    # Find out the two most common values of these attributes for section headers and all pars
    ## TODO: improve section header identification
    sh_pat = "^[1-9]{1}(\\.{1}[1-9]{1}){,2}\\s{1}(\\w){1,}"
    section_headers = par_df[(par_df['text'].str.contains(sh_pat)) & (par_df['height']<=20)]
    sh_attribs = {}
    bt_attribs = {}
    for a in attribs:
        sh_attribs[a] = list(section_headers.groupby([a]).sum()['text_length'].sort_values(ascending=False).index[:2])
        bt_attribs[a] = list(par_df.groupby([a]).sum()['text_length'].sort_values(ascending=False).index[:1])

    # filter body and section headers by the information above
    filtered_bt = par_df[(~par_df['text'].str.contains(sh_pat)) & (par_df['height']>20)]
    for key,value in bt_attribs.items():
        filtered_bt = filtered_bt[filtered_bt[key].isin(value)]
    filtered_bt['imputed_role'] = 'body-text'

    for key,value in sh_attribs.items():
        section_headers = section_headers[section_headers[key].isin(value)]


    # Join incomplete paragraphs to the previous paragraph
    filtered_bt = filtered_bt.reset_index()
    filtered_bt['whole_par'] = True
    last = None
    for index, row in filtered_bt.iterrows():
        if not re.match('^[A-Z]',row['text']):
            if last is not None:
                filtered_bt['text'].iloc[last] += " " + row['text']
            filtered_bt['whole_par'].iloc[index] = False
        else:
            last = index

    whole_pars = filtered_bt[filtered_bt['whole_par']==True].reset_index().drop(['whole_par','level_0'],axis=1)

    whole_pars = whole_pars.rename(index=str, columns={"index": "n"})

    doc.docpar_set.all().delete()

    for index, row in whole_pars.iterrows():
        dp = DocPar(**dict(row))
        dp.doc=doc
        dp.n = index
        dp.save()

    return

def make_doc(f,d):
    url, created = URLs.objects.get_or_create(
        url=str(uuid.uuid1())
    )
    surl = short_url.encode_url(url.id)
    ut, created = UT.objects.get_or_create(UT=surl)
    doc = Doc(title=f,UT=ut)
    doc.title = f
    doc.PY = d['PY'][d.index[0]]
    doc.save()
    authors = d['AU'][d.index[0]].split(' et al')[0]
    authors = authors.split(" and ")
    for a in authors:
        dai = DocAuthInst(
            doc=doc,
            AU=a.strip()
        )
        dai.save()

    return doc

def find_doc_title(f,d):
    docs = Doc.objects.filter(title__iexact=d['TI'][d.index[0]])

    if docs.count() == 1:
        doc = docs.first()
    else:
        print('\n#####\nNot found by title')
        print(docs)
        print(d['TI'][d.index[0]])
        print(d['PY'][d.index[0]])
        doc = make_doc(f,d)

    return doc


xml_dir = '/home/hilj/NETs in IAM literature/xml_input2webplatform/'

# Get relevant query
#q = Query.objects.get(pk=2777)
q = Query.objects.get(pk=2823)
q.doc_set.filter(wosarticle__isnull=True).delete()

# Get document meta information
docs = pd.read_csv('/home/galm/projects/NETs-IAMs/netsiams/all_docs_20180529_edited.csv',sep=";", encoding = "latin-1")

unfound = 0

# Loop over xml files
for f in os.listdir(xml_dir):
    if fnmatch.fnmatch(f,'*.xml'):
        bare_file = f
        f         = xml_dir+f                   # get full name
        bare_file = bare_file.replace('  ',' ') # replace double spaces by single spaces
        # Try to find matching document in document meta information
        try:
            d = docs[docs['xml']==bare_file]

            # Look if current document already exists in the DB
            if not d['DOI'].isna().bool():
                doi = d['DOI'][d.index[0]]
                try:
                    doc = Doc.objects.get(wosarticle__di=doi)
                except:
                    if Doc.objects.filter(wosarticle__di=doi).count() > 1:
                        doc = Doc.objects.get(wosarticle__di=doi, UT__UT__contains="WOS:")
                    else:
                        doc = find_doc_title(f,d)
            else:
                doc = find_doc_title(f,d)

            if doc is None:
                unfound+=1
            #doc = Doc.objects.get()

        except:
            print("No match for: "+f)
            continue

        # Add document to query
        doc.query.add(q)

        # Parse document and extract paragraphs
        parse_document(f, doc)

print(str(unfound)+" document could not be found.")
q.r_count = q.doc_set.count()
q.save()

fields = ['doc__title','doc__wosarticle__di'] + [f.name for f in DocPar._meta.get_fields()]
dps = DocPar.obj
