import string
import nltk
import re
from nltk.stem import SnowballStemmer

def tokenize(text):
    transtable = {ord(c): None for c in string.punctuation + string.digits}
    tokens = nltk.word_tokenize(text.translate(transtable))
    tokens = [i for i in tokens if len(i) > 2]
    return tokens

stoplist = set(nltk.corpus.stopwords.words("english"))

class snowball_stemmer(object):
    def __init__(self):
        self.stemmer = SnowballStemmer("english")
    def __call__(self, doc):
        return [self.stemmer.stem(t) for t in tokenize(doc)]


def proc_docs(docs, stoplist, fulltext=False):
    docs = [x for x in docs.iterator() if x.word_count() > 10]
    if fulltext:
        abstracts = [x.fulltext.split("Copyright (C)")[0] for x in docs]
    else:
        abstracts = [x.content.split("Copyright (C)")[0] for x in docs]
    abstracts = [re.split("\([C-c]\) [1-2][0-9]{3} Elsevier",x)[0] for x in abstracts]
    abstracts = [x.split("Published by Elsevier")[0] for x in abstracts]
    abstracts = [x.split("Copyright. (C)")[0] for x in abstracts]
    abstracts = [re.split("\. \(C\) [1-2][0-9]{3} ",x)[0] for x in abstracts]
    abstracts = [re.split("\. \(C\) Copyright",x)[0] for x in abstracts]
    docsizes = [len(x) for x in abstracts]
    ids = [x.pk for x in docs]

    return [abstracts, docsizes, ids]
