import matplotlib.pyplot as plt
from time import time
import numpy as np
import random
import math
from scipy import interpolate
from matplotlib import cm, patches
from scoping.models import *
from scipy.spatial import ConvexHull

plt.rc('font',size=7)
plt.rc('axes',titlesize=7)
plt.rc('axes',labelsize=7)
plt.rc('xtick',labelsize=7)
plt.rc('ytick',labelsize=7)
plt.rc('legend',fontsize=7)
plt.rc('figure',titlesize=7)

def plot_tsne_2(r_ind,tsne_results,cats,verbose=False):
    cs = []
    sizes = []
    xs = []
    ys = []
    fig = plt.figure(dpi=188)

    t0 = time()

    for i,did in enumerate(r_ind):
        x = tsne_results[i,0]
        y = tsne_results[i,1]
        col = "#F0F0F026"
        for c in cats:
            if did in c['docs']:
                col = c['color']
        cs.append(col)
        xs.append(x)
        ys.append(y)

    if verbose:
        print("calculating points took %0.3fs." % (time() - t0))

    t0 = time()

    plt.scatter(
        xs,
        ys,
        s=3,
        alpha=0.6,
        #s=sizes,
        linewidth=0.1,
        c=cs,
        edgecolor='#a39c9c66'
    )

    if verbose:
        print("plotting points took %0.3fs." % (time() - t0))

    l = plt.xlim()[0]
    t = plt.ylim()[1]

    yextent = plt.ylim()[1]- plt.ylim()[0]
    ysp = yextent*0.08



    for i,c in enumerate(cats):
        plt.text(
            l*0.95,
            t-ysp-i*ysp,
            "{} {:.1%}".format(c['name'],len(c['docs'])/len(r_ind)),
            fontsize=5,
            bbox={
                'facecolor': c['color'],
                'pad': 3
            }
        )
    plt.tick_params(
        axis='both',
        which='both',
        bottom=False,
        top=False,
        labelbottom=False,
        left=False,
        labelleft=False
    )


def plot_tsne(
    r_ind,tsne_results,cats,nocatids,
    ax=None,verbose=False,hdoc=False,
    legend=True, sc=None, heat_var=None, cmapname=None,
    topics=None
    ):
    cs = []
    sizes = []
    xs = []
    ys = []

    if ax == None:
        fig,ax = plt.subplots(dpi=188)
    t0 = time()

    nocatids = np.argwhere(np.isin(r_ind,nocatids))

    psize = 1

    if hdoc is not False:
        hdocs = nocatids[np.isin(nocatids,hdoc)]
        ids = nocatids[np.isin(nocatids,hdoc,invert=True)]
    ax.scatter(
        tsne_results[nocatids,0],
        tsne_results[nocatids,1],
        c='#F0F0F026',
        s=psize,
        alpha=0.4,
        linewidth=0.1,
        edgecolor='#a39c9c66'
    )

    # Draw docs to be highlighted separately
    if hdoc is not False:
        ax.scatter(
            tsne_results[hdocs,0],
            tsne_results[hdocs,1],
            c='#F0F0F026',
            s=psize,
            alpha=1,
            linewidth=0.2,
            edgecolor='black'
        )

    # split the data and add layer by layer to prevent top layer overwriting all
    splits = 10
    for i in range(splits):
        for c in cats:
            ids = np.array_split(c["dis"],splits)[i]
            if hdoc is not False:
                hdocs = ids[np.isin(ids,hdoc)]
                ids = ids[np.isin(ids,hdoc,invert=True)]
            ax.scatter(
                tsne_results[ids,0],
                tsne_results[ids,1],
                #zorder = [math.ceil(random.random()*1) for i in range(len(ids))],
                c=c['color'],
                s=psize,
                alpha=0.7,
                linewidth=0.1,
                edgecolor='#a39c9c66'
            )
            if hdoc is not False:
                ax.scatter(
                    tsne_results[hdocs,0],
                    tsne_results[hdocs,1],
                    c=c["color"],
                    s=psize,
                    alpha=1,
                    linewidth=0.2,
                    edgecolor='black'
                )



    ax.grid(linestyle='-')

    if verbose:
        print("calculating points took %0.3fs." % (time() - t0))

    l = ax.get_xlim()[0]
    t = ax.get_ylim()[1]

    yextent = ax.get_ylim()[1]- ax.get_ylim()[0]
    ysp = yextent*0.08


    if legend:
        for i,c in enumerate(cats):
            ax.text(
                l*0.95,
                t-ysp-i*ysp,
                "{} {:.1%}".format(c['name'],len(c['docs'])/len(r_ind)),
                fontsize=5,
                bbox={
                    'facecolor': c['color'],
                    'pad': 3
                }
            )

    if heat_var:
        cmap = cm.get_cmap(cmapname)
        ys = [getattr(cs,heat_var) for cs in sc.objects if getattr(cs,heat_var) is not None]
        X = np.interp(ys, (np.min(ys), np.max(ys)), (0, +1))
        f = interpolate.interp1d(ys, X)
        for cs in sc.objects:
            if getattr(cs, heat_var):
                col = cmap(f(getattr(cs, heat_var)).max())
                rect = patches.Rectangle(
                    (cs.x1,cs.y1),cs.x2-cs.x1,cs.y2-cs.y1,
                    linewidth=1,edgecolor='r',
                    facecolor=col,alpha=0.3
                )

                ax.add_patch(rect)

    if topics:
        for t in topics:

            atdocscores = Doc.objects.filter(
                docdynamictopic__topic=t,
            ).values_list('docdynamictopic__score',flat=True)

            thresh = np.quantile(atdocscores,0.99)

            tdocs = Doc.objects.filter(
                docdynamictopic__topic=t,
                docdynamictopic__score__gt=thresh
            ).order_by('-docdynamictopic__score').values_list('id',flat=True)

            highlight_docs = np.argwhere(np.isin(r_ind,tdocs))[:,0]

            if len(highlight_docs) == 0:
                continue

            print(len(highlight_docs))
            #points = np.array([tsne_results[v] for i,v in enumerate(highlight_docs)]
            points = tsne_results[highlight_docs]
            hull = ConvexHull(points)
            for i, simplex in enumerate(hull.simplices):
                plt.plot(
                    points[simplex, 0],
                    points[simplex, 1],
                    'k-',
                    linewidth=0.5
                )
                for j in range(len(points[simplex,0])):
                    if i==0 and j==0:
                        px = points[simplex,0][j]
                        py = points[simplex,1][j]
                    else:
                        if points[simplex,0][j] < px:
                            px = points[simplex,0][j]
                            py = points[simplex,1][j]
            plt.text(
                px-1,
                py,
                t.title,
                va="center",
                ha="right",
                fontsize=5
            )


    # plt.tick_params(
    #     axis='both',
    #     which='both',
    #     bottom=False,
    #     top=False,
    #     labelbottom=False,
    #     left=False,
    #     labelleft=False
    # )
