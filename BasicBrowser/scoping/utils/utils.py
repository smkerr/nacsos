from scoping.models import *
import re
from django.conf import settings
from utils.utils import *
from itertools import product
import scoping.models
import json
#from utils.utils import *

XML_TRANS_TABLE = {
    'journal-title': 'so',
    'book-title': 'ti',
    'publisher': 'pu',
    'article-id': 'UT',
    'article-title': 'ti',
    'year': 'py',
    'volume': 'vl',
    'issue': 'iss',
    'fpage': 'bp',
    'lpage': 'ep',
    'abstract': 'AB'
}

JSTOR_TRANS_TABLE = {
    'id': 'UT',
    'doi': 'di',
    'docType': 'dt',
    'tdmCategory': 'sc',
    'sourceCategory': 'sc',
    'language': 'la',
    'datePublished': 'pd',
    'pageCount': 'pg',
    'url': 'url',
    'isPartOf': 'so',
    'collection': 'so',
    'publisher': 'pu',
    'title': 'ti',
    'creator': 'au',
    'pageStart': 'bp',
    'pageEnd': 'ep',
    'publisher': 'pu',
    'publicationYear': 'py',
    'volumeNumber': 'vl',
    'issueNumber': 'iss',
    'abstract': 'AB',
    'fullText': 'ft'
}

def make_nears(q, nearness):
    qs = []
    ls = [ l.lower().split(' or ') for l in q.split(' AND ')]
    combinations = [f" NEAR{nearness} ".join([x.strip('()') for x in p]) for p in product(*ls)]
    qtext = ""
    for c in combinations:
        c = f'({c})'
        if len(qtext) == 0:
            qtext = c
        elif len(qtext) + len(c) < 250:
            qtext += " OR " + c
        else:
            qs.append(qtext)
            qtext = c
    if len(qs)==1:
        qs = qs[0]
    return qs

def make_jstor_nears(q, nearness):
    qs = []
    ls = [ l.lower().split(' or ') for l in q.split(' AND ')]
    combinations = [" ".join([x.strip('() "') for x in p]) for p in product(*ls)]
    qtext = ""
    for c in combinations:
        c = f'("{c}"~{nearness})'
        if len(qtext) == 0:
            qtext = c
        elif len(qtext) + len(c) < 250:
            qtext += " OR " + c
        else:
            qs.append(qtext)
            qtext = c
    if len(qtext) > 0:
        qs.append(qtext)
    if len(qs)==1:
        qs = qs[0]
    return qs

def element_text_contents(element):
    s = element.text or ""
    for sub_element in element:
        if hasattr(sub_element,'text'):
            if sub_element.text is not None:
                s += sub_element.text
    return s.strip()

ABSTRACKR_CSV_TABLE = {
    "keywords": "wosarticle__de",
    "abstract": "AB"
}

def parse_jstor_content(obj_parsed_from_json, file_db_mapping=JSTOR_TRANS_TABLE):
    '''parse the content of a JSTOR document'''
    doc_dict = {}
    for key_in_file, key_in_db in file_db_mapping.items():
        value_from_file = obj_parsed_from_json.get(key_in_file)
        doc_dict[key_in_db] = value_from_file
        if key_in_db == 'UT':
            doc_dict[key_in_db] = f"JSTOR_ID:{value_from_file}"
        if key_in_db == 'af':
            doc_dict[key_in_db] = value_from_file[0]
    return doc_dict

def get_jstor_json_content(jsonl_file):
    for line in jsonl_file:
        yield json.loads(line)

def read_jsonl(q, update):
    '''parse a JSTOR json file'''
    with open(f'{settings.MEDIA_ROOT}/{q.query_file.name}') as f:
        if '.jsonl' in q.query_file.name:
            json_objects = get_jstor_json_content(f)

        r_count = 0
        for doc_from_file in json_objects:
            doc_for_db = (parse_jstor_content(obj_parsed_from_json=doc_from_file))

            try:
                add_scopus_doc(doc_for_db,q,update)
                r_count+=1
            except:
                print(f"couldn't add {doc_for_db}")

        return r_count

csv_field_dict = {

}

def read_csv(q):
    df = pd.read_csv(f'{settings.MEDIA_ROOT}/{q.query_file.name}')
    for i, row in df.iterrows():
        row = {k: row[k] for k in df.columns if not pd.isna(row[k])}
        add_scopus_doc(row, q, False, find_ids=False)
    return q.doc_set.count()

def read_abstrackr_csv(q):
    '''parse an abstrackr generated csv'''
    import csv
    i = 0
    with open(f'{settings.MEDIA_ROOT}/{q.query_file.name}') as f:
        d = csv.DictReader(f)
        for row in d:
            i+=1
            t = row['title']
            try:
                d = scoping.models.Doc.objects.get(
                    docproject__project=q.project,
                    title=t
                )
            except:
                print(t)
                continue
            d.query.add(q)
    return i



def read_xml(q, update):
    '''parse a jstor like xml'''
    r_count = 0
    import xml.etree.ElementTree as ET
    tree = ET.parse("{}/{}".format(settings.MEDIA_ROOT,q.query_file.name))
    root = tree.getroot()
    types = ["article","book"]
    if root.tag in types:
        articles = [root]
    else:
        articles = [x for x in root]
    for article in articles:
        rtype = article.tag
        if rtype=="article":
            matter = "front"
        elif rtype=="book":
            matter = "book-meta"
        else:
            print(f"!!!!\n I don't know the record type: {rtype}")
        if article.find(matter):
            article = article.find(matter)
        article_dict = {}
        for field in article.iter():
            if field.tag in XML_TRANS_TABLE:
                f = XML_TRANS_TABLE[field.tag]
                article_dict[f] = element_text_contents(field)
                if f == "UT":
                    article_dict[f] = "JSTOR_ID:"+article_dict[f]
        authors = list(article.iter('contrib'))
        if len(authors) > 0:
            article_dict['au'] = []
            article_dict['af'] = []
            for author in authors:
                nameid = 'string-name'
                name = author.find(nameid)
                if name is None:
                    nameid = 'name'
                    name = author.find(nameid)
                if name is None:
                    if author.find('collab'):
                        article_dict['au'].append(author.find('collab').text)
                    continue
                surname = name.find('surname')
                if surname is not None:
                    first_names = name.find('given-names')
                    if first_names is not None:
                        AU = f"{surname.text}, {first_names.text[0]}."
                        article_dict['af'].append(f"{surname.text}, {first_names.text}")
                    else:
                        print(surname.text)
                        AU = surname.text
                    article_dict['au'].append(AU)
        try:
            add_scopus_doc(article_dict,q,update)
            r_count+=1
        except:
            add_scopus_doc(article_dict,q,update)
            print(f"couldn't add {article_dict}")

    return r_count

##################################
## Flatten nested lists

def flatten(container):
    for i in container:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i

def jaccard(s1,s2):
    try:
        return len(s1.intersection(s2)) / len(s1.union(s2))
    except:
        return 0

SCOPUS_QUERY_FIELDS = [
    "TITLE-ABS-KEY","TITLE",
    "PUBYEAR","DOI","AUTH",
]
OPERATORS = [
    "OR","AND","NOT","AND NOT","NEAR","W/","PRE/"
]

def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def ihighlight(word, text, tclass="t1"):
    idx = 0
    remaining_text = text
    parsed_text = ""
    word = word.replace("(","").replace(")","")
    try:
        for m in re.finditer(word.lower().replace("*","\w*")+"(\W|$)",text.lower()):
            parsed_text += f'{text[idx:m.span()[0]]}<span class="{tclass}">{m.group()}</span>'
            idx = m.span()[1]
            remaining_text = text[idx:]
    except:
        print(word)
        pass

    return parsed_text + remaining_text


def clean_qword(s):
    # Remove WoS + Scopus Field Keys
    try:
        s = s.split('(')[1]
    except:
        pass
    if "=" in s:
        return False
    s = re.sub('[\(\)]','',s)
    if is_number(s):
        return False
    if len(s) < 3:
        return False
    if s in SCOPUS_QUERY_FIELDS:
        return False
    if s in OPERATORS:
        return False
    return s


def extract_words_phrases(s):
    s = s.replace('“','"').replace('”','"')
    s = s.replace("All of the words:","")
    phrase = re.compile('"([^"]*)"')

    phrases = re.findall('"([^"]*)"',s)
    s = re.sub('"([^"]*)"','',s)
    notpat = "(NOT \w* ?= ?\(.*\))"
    s = re.sub(notpat,"",s)
    words = [clean_qword(x) for x in s.split() if clean_qword(x)]

    return phrases + words


def get_query_words(qs):
    try:
        qtexts = qs.values_list('text',flat=True)
    except:
        qtexts = [q.text for q in qs]
    qwords = flatten([extract_words_phrases(s) for s in qtexts])
    qwords = set(qwords)
    return qwords
