# Allocate paragraphs to users

from scoping.models import *

tagid = 646
# Users
# galm:  1
# minj:  3
# hilj:  7
# nemet: 9
userids = [
    ('hilj', 0.75),    # hilj gets 800 paragraphs
    ('minj', 0.25)     # minj gets 400 paragraphs
]

# Get all unprocessed paragraphs
do_pars = DocOwnership.objects.filter(tag__id=tagid, relevant=0)

# Get all associated documents
doc_pars = DocPar.objects.filter(pk=dopars)

# Reallocate documents + paragraphs to users so that each user get roughly the same number of items
