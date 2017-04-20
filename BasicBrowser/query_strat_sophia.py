import django, os, sys, time, resource, re, gc, shutil
from django.utils import timezone
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def do_query(q):
    fname = "/queries/"+str(q.id)+".txt"
    # write query text to file
    with open(fname,encoding='utf-8',mode="w") as qfile:
        qfile.write(q.text.encode("utf-8").decode("utf-8"))
    # set the scraper running on it
    subprocess.Popen(["python3",
        "/home/galm/software/scrapewos/bin/scrapeQuery.py",
        "-s", "WoS", fname
    ])


sophia = User.objects.get(username="rogers")

#Queries created by Sophia
squeries = Query.objects.filter(creator=sophia)

#Of which innovation / tech queries
iqs = squeries.filter(title__iregex=r'^[A-Z]+_+').order_by('title')
tqs = squeries.filter(title__iregex=r'^[0-9]+_+').order_by('title')

squeries.filter(title__iregex=r'^[A-Z]+[0-9]+').delete()
squeries.filter(title__iregex=r'^[0-9]+[A-Z]+').delete()

# Make an all NETS query by combining with ors
all_nets = " OR ".join(["("+x.text.strip()+")" for x in tqs])

if tqs.filter(title="0_NETSall").count() == 0:
    q = Query(
        title = "0_NETSall",
        text = all_nets,
        creator = sophia,
        database = "WoS"
    )
    # save and do the new query
    q.save()
    do_query(q)

    # Combine this with each of the innovation queries
    for iq in iqs:
        i_ind = iq.title.split('_')[0]
        i_name = iq.title.split('_')[1]
        # Save an innovation object if one does not exist
        if Innovation.objects.filter(name=i_name).count() == 0:
            inno = Innovation(name=i_name)
            inno.save()
        else:
            inno = Innovation.objects.filter(name=i_name).first()
        # Create a new query combining the innovation query with all_nets
        q = Query(
            title = i_ind+"_"+i_name+"NETS",
            text = "("+all_nets+") AND ("+iq.text+")",
            creator = sophia,
            database = "WoS",
            innovation = inno
        )
        print(q.title)
        # save and do the new query
        q.save()
        do_query(q)


iqs.exclude(title__icontains="NETS").delete()

#loop through the tech queries
for tq in tqs:
    print(tq.technology)
    # Split the index and the name
    t_ind = tq.title.split('_')[0]
    t_name = tq.title.split('_')[1]
    #loop through the innovation queries
    for iq in iqs:
        i_ind = iq.title.split('_')[0]
        i_name = iq.title.split('_')[1]
        # make a new query
        q = Query(
            title = t_ind+i_ind+"_"+t_name+i_name,
            type = 'default',
            text = str(tq.id) + " AND " + str(iq.id),
            creator = sophia,
            date = timezone.now(),
            database = "intern",
            innovation = iq.innovation,
            technology = tq.technology
        )
        q.save()
        # Find the appropriate docs, they match a filter for BOTH queries
        combine = Doc.objects.filter(query=tq).filter(query=iq)
        # Add each matching doc to the new query
        for d in combine:
            d.query.add(q)
        q.r_count = len(combine.distinct())
        q.save()
