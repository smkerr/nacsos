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


def proc_docs(docs, stoplist):
    abstracts = [re.split("\([C-c]\) [1-2][0-9]{3} Elsevier",x.content)[0] for x in docs.iterator()]
    abstracts = [x.split("Published by Elsevier")[0] for x in abstracts]
    abstracts = [x.split("Copyright (C)")[0] for x in abstracts]
    abstracts = [re.split("\. \(C\) [1-2][0-9]{3} ",x)[0] for x in abstracts]
    docsizes = [len(x) for x in abstracts]
    ids = [x.UT for x in docs.iterator()]

    return [abstracts, docsizes, ids]
