import django
from tmv_app.models import *
from parliament.models import *


def merge_utterance_paragraphs(uts, include_interjections=False):

    """
    Merges all paragraphs of one utterance to one text

    :param uts:
    :param include_interjections:
    :return: [document texts, document sizes, utterance ids]
    """

    doc_texts = []
    for ut in uts.iterator():
        pars = Paragraph.objects.filter(utterance=ut)
        if include_interjections:
            interjections = Interjection.objects.filter(utterance=ut)
        doc_text = "\n".join([par.text for par in pars])

        doc_texts.append(doc_text)

    ids = [x.pk for x in uts.iterator()]
    docsizes = [len(x) for x in doc_texts]

    return [doc_texts, docsizes, ids]

