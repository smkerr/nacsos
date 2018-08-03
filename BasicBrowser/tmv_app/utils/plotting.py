import matplotlib.pyplot as plt
from time import time
import numpy as np


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


def plot_tsne(r_ind,tsne_results,cats,nocatids,verbose=False):
    cs = []
    sizes = []
    xs = []
    ys = []
    fig = plt.figure(dpi=188)

    t0 = time()

    nocatids = np.argwhere(np.isin(r_ind,nocatids))

    plt.scatter(
        tsne_results[nocatids,0],
        tsne_results[nocatids,1],
        c='#F0F0F026',
        s=3,
        alpha=0.6,
        linewidth=0.1,
        edgecolor='#a39c9c66'
    )

    for c in cats:
        plt.scatter(
            tsne_results[c["dis"],0],
            tsne_results[c["dis"],1],
            c=c['color'],
            s=3,
            alpha=0.6,
            linewidth=0.1,
            edgecolor='#a39c9c66'
        )

    if verbose:
        print("calculating points took %0.3fs." % (time() - t0))

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
