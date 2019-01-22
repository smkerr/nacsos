import string
import nltk
import re
from nltk.stem import SnowballStemmer
import uuid
import os, shutil

def tokenize(text):
    transtable = {ord(c): None for c in string.punctuation + string.digits}
    tokens = nltk.word_tokenize(text.translate(transtable))
    tokens = [i for i in tokens if len(i) > 2 and len(i) < 100]
    return tokens

def get_sentence(abstract):
    return [snowball_stemmer().stemmer.stem(t) for t in tokenize(abstract)]

def get_sentence_g(texts):
    return [german_stemmer().stemmer.stem(t) for t in tokenize(texts)]

stoplist = set(nltk.corpus.stopwords.words("english"))

class snowball_stemmer(object):
    def __init__(self):
        self.stemmer = SnowballStemmer("english")
    def __call__(self, doc):
        return [self.stemmer.stem(t) for t in tokenize(doc)]

class german_stemmer(object):
    def __init__(self):
        self.stemmer = SnowballStemmer("german")
    def __call__(self, doc):
        return [self.stemmer.stem(t) for t in tokenize(doc)]

def proc_docs(docs, stoplist, fulltext=False, citations=False):

    docs = [x for x in docs.iterator() if x.word_count() > 10]
    if fulltext:
        abstracts = [x.fulltext.replace("Copyright (C)","") for x in docs]
    else:
        abstracts = [x.content.split("Copyright (C)")[0] for x in docs]
        abstracts = [re.split("\([C-c]\) [1-2][0-9]{3} Elsevier",x)[0] for x in abstracts]
        abstracts = [x.split("Published by Elsevier")[0] for x in abstracts]
        abstracts = [x.split("Copyright. (C)")[0] for x in abstracts]
        abstracts = [re.split("\. \(C\) [1-2][0-9]{3} ",x)[0] for x in abstracts]
        abstracts = [re.split("\. \(C\) Copyright",x)[0] for x in abstracts]
    docsizes = [len(x) for x in abstracts]
    ids = [x.pk for x in docs]

    if citations:
        citations = []
        for x in docs:
            try:
                if x.wosarticle.tc is not None:
                    citations.append(x.wosarticle.tc)
                else:
                    citations.append(0)
            except:
                citations.append(0)
    return [abstracts, docsizes, ids, citations]

def docset_to_corpus(docset):
    dirname = '/tmp/{}/'.format(uuid.uuid4())
    os.mkdir(dirname)
    for doc in docset.iterator():
        fname=str(doc.id)+'.txt'
        corpusfile=open(dirname+fname,'a')
        corpusfile.write(str(doc.content))
        corpusfile.close()

    my_corpus = nltk.corpus.reader.PlaintextCorpusReader(dirname,r'.*')

    shutil.rmtree()


def process_texts(docs):
    docs = [x for x in docs.iterator()]
    docsizes = [len(x.text) for x in docs]
    ids = [x.pk for x in docs]
    abstracts = [x.text for x in docs]

    return [abstracts, docsizes, ids]

class ModelSimilarity:
	'''
	Uses a model (e.g. Word2Vec model) to calculate the similarity between two terms.
	'''
	def __init__( self, model ):
		self.model = model

	def similarity( self, ranking_i, ranking_j ):
		sim = 0.0
		pairs = 0
		for term_i in ranking_i:
			for term_j in ranking_j:
				try:
					sim += self.model.similarity(term_i, term_j)
					pairs += 1
				except:
					#print "Failed pair (%s,%s)" % (term_i,term_j)
					pass
		if pairs == 0:
			return 0.0
		return sim/pairs


# --------------------------------------------------------------

class WithinTopicMeasure:
	'''
	Measures within-topic coherence for a topic model, based on a set of term rankings.
	'''
	def __init__( self, metric ):
		self.metric = metric

	def evaluate_ranking( self, term_ranking ):
		return self.metric.similarity( term_ranking, term_ranking )

	def evaluate_rankings( self, term_rankings ):
		scores = []
		overall = 0.0
		for topic_index in range(len(term_rankings)):
			score = self.evaluate_ranking( term_rankings[topic_index] )
			scores.append( score )
			overall += score
		overall /= len(term_rankings)
		return overall
