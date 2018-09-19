from scoping.models import *
import re
from utils.utils import *

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

def ihighlight(old, text):
    idx = 0
    while idx < len(text):
        index_l = text.lower().find(old.lower(), idx)
        if index_l == -1:
            return text
        text = text[:index_l] + '<span class="t1">' + text[index_l:index_l+len(old)] + '</span>' + text[index_l + len(old):]
        idx = index_l + len('<span class="t1">'+'</span>')
    return text

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
    phrase = re.compile('"([^"]*)"')

    phrases = re.findall('"([^"]*)"',s)
    s = re.sub('"([^"]*)"','',s)
    words = [clean_qword(x) for x in s.split() if clean_qword(x)]

    return phrases + words


def get_query_words(qs):
    qtexts = qs.values_list('text',flat=True)
    qwords = flatten([extract_words_phrases(s) for s in qtexts])
    qwords = set(qwords)
    return qwords
