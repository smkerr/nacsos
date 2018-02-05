import string
import nltk
import re
from nltk.stem import SnowballStemmer

def tokenize(text):
    transtable = {ord(c): None for c in string.punctuation + string.digits}
    tokens = nltk.word_tokenize(text.translate(transtable))
    tokens = [i for i in tokens if len(i) > 2]
    return tokens

def get_sentence(abstract):
    return [snowball_stemmer().stemmer.stem(t) for t in tokenize(abstract)]


stoplist = set(nltk.corpus.stopwords.words("english"))

class snowball_stemmer(object):
    def __init__(self):
        self.stemmer = SnowballStemmer("english")
    def __call__(self, doc):
        return [self.stemmer.stem(t) for t in tokenize(doc)]


def proc_docs(docs, stoplist, fulltext=False):
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
