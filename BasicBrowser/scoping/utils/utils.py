from scoping.models import *
import re
from django.conf import settings
from utils.utils import *
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


def element_text_contents(element):
    s = element.text or ""
    for sub_element in element:
        s += sub_element.text
    return s.strip()

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

def ihighlight(word, text):
    idx = 0
    remaining_text = text
    parsed_text = ""
    word = word.replace("(","").replace(")","")
    try:
        for m in re.finditer(word.lower().replace("*","\w*"),text.lower()):
            parsed_text += f'{text[idx:m.span()[0]]}<span class="t1">{m.group()}</span>'
            idx = m.span()[1]
            remaining_text = text[idx:]
    except:
        print(word)
        pass

    return parsed_text + remaining_text


def clean_qword(s):
    # Remove WoS + Scopus Field Keys
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
