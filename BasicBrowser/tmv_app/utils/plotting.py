import matplotlib.pyplot as plt
from time import time
import numpy as np
import random
import math
from scipy import interpolate
from matplotlib import cm, patches
from scoping.models import *
from scipy.spatial import ConvexHull
from sklearn.cluster import DBSCAN
from adjustText import adjust_text, get_renderer, get_bboxes



plt.rc('font',size=7)
plt.rc('axes',titlesize=7)
plt.rc('axes',labelsize=7)
plt.rc('xtick',labelsize=7)
plt.rc('ytick',labelsize=7)
plt.rc('legend',fontsize=7)
plt.rc('figure',titlesize=7)

class SquareCollection:
    def __init__(self):
        self.objects = []

    def add(self, o):
        self.objects.append(o)

    def get(self,**kwargs):
        matches = []
        for o in self.objects:
            match = True
            for k,v in kwargs.items():
                if getattr(o,k)!=v:
                    match=False
            if match:
                matches.append(o)
        if len(matches) > 0:
            return matches[0]
        else:
            return None

class CoordSquare:
    def __init__(self,x1,x2,y1,y2,r_ind,tsne_results,ar=None):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.r_ind = r_ind
        self.tsne_results = tsne_results
        self.ar = ar
        self.size = self.r_ind.shape[0]
        self.share = None
        self.av_y = None
        self.H = None

    def get_points(self):
        r = self.tsne_results#[self.r_ind[:,0],:]
        conditions = (r[:,0]>self.x1) & (r[:,0]<self.x2) & (r[:,1]>self.y1) & (r[:,1]<self.y2)
        self.r = r[conditions]
        self.r_ind = self.r_ind[conditions]

        self.share = self.r.shape[0] / self.size

        return self.r.shape[0] / self.size
    def summarise_topics(self,run_id):
        stat = RunStats.objects.get(pk=run_id)
        docs = Doc.objects.filter(id__in=self.r_ind)
        if stat.method=="DT":
            dt_string = 'docdynamictopic'
            DTO = DocDynamicTopic.objects
        else:
            dt_string = 'doctopic'
            DTO = DocTopic.objects

        if docs.count()<100:
            self.av_y = None
            self.H = None
        else:
            self.av_y = np.mean(list(docs.filter(PY__isnull=False).values_list('PY',flat=True)))
            H = 0
            ts = DTO.filter(
                run_id=run_id,
                score__gt=stat.dt_threshold,
                doc__id__in=self.r_ind
            ).values('topic').annotate(
                pzc = Sum('score')
            )
            for t in ts:
                H+=t['pzc']*np.log(t['pzc'])
            self.H = -1*H

        topics = docs.filter(
            **{f'{dt_string}__run_id': run_id}
        ).values(f'{dt_string}__topic__title').annotate(
            tscore=Sum(f'{dt_string}__score')
        ).order_by('-tscore')
        total = topics.aggregate(tsum = Sum('tscore'))
        df = pd.DataFrame.from_dict(list(topics))
        df['x1'] = self.x1
        df['x2'] = self.x2
        df['y1'] = self.y1
        df['y2'] = self.y2
        df['proportion'] = df['tscore'] / total['tsum']
        df = df[df['proportion']>0.001]
        return df

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

def extend_points(p1,p2,length=0.8):
    p3 = [None,None]
    lenAB = np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
    p3[0] = p2[0] + (p2[0] - p1[0]) / lenAB*length
    p3[1] = p2[1] + (p2[1] - p1[1]) / lenAB*length
    return p3

def cluster_label_points(
    title, points, ax, eps,
    min_cluster, n_clusters, clabel_size,
    words_only
    ):
    db = DBSCAN(eps=eps,min_samples=min_cluster).fit(points)
    labels = db.labels_
    texts = []
    bboxes = []
    r = get_renderer(ax.get_figure())
    for l in set(labels):
        text_set = False
        if l==-1:
            continue
        ind = np.argwhere(labels==l)[:,0]
        #print("\n##\nlabel: {}, {} documents".format(l,len(ind)))
        lpoints = points[ind]
        if len(ind) > min_cluster:
            try:
                hull = ConvexHull(lpoints)
            except:
                continue
            cx = np.mean(hull.points[hull.vertices,0])
            cy = np.mean(hull.points[hull.vertices,1])
            c = [cx,cy]


            if words_only:
                title = title.split(",")[0].replace("{","")
                text = ax.annotate(
                    title, c, fontsize=clabel_size,
                    ha="center",va="center",
                    bbox={'facecolor':"white", 'alpha':0.4, 'pad':0.4, 'boxstyle': 'round'}

                )
                return text
                break

            else:
                for i, simplex in enumerate(hull.simplices):
                    p1 = extend_points(c,lpoints[simplex,:][0])
                    p2 = extend_points(c,lpoints[simplex,:][1])
                    plt.plot(
                        [p1[0],p2[0]],
                        [p1[1],p2[1]],
                        'k-',
                        linewidth=0.5
                    )
                    if not text_set:
                        if p1[0] > cx:
                            ha = "left"
                        else:
                            ha = "right"
                        pl = extend_points(c,p1)
                        texts.append(ax.annotate(
                            title,
                            p1,
                            xytext=pl,
                            va="center",
                            ha=ha,
                            fontsize=clabel_size,
                            arrowprops=dict(width=0.2,headwidth=0.1),
                            bbox={'facecolor':"white", 'alpha':0.4, 'pad':0.4, 'boxstyle': 'round'}
                        ))
                        text_set = True
                # break here, just do the biggest cluster
                #break

def plot_tsne(
    r_ind,tsne_results,cats,nocatids,
    ax=None,verbose=False,hdoc=False,
    legend=True, sc=None, heat_var=None, cmapname=None,
    topics=None, min_cluster = 100, psize=1,
    t_thresh=0.8, eps=1, n_clusters=1,
    doc_sets=None, clabel_size=8,
    words_only=False, fsize=5
    ):
    cs = []
    sizes = []
    xs = []
    ys = []

    if ax == None:
        fig,ax = plt.subplots(dpi=188)
    t0 = time()

    nocatids = np.argwhere(np.isin(r_ind,nocatids))


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
            linewidth=0.5,
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
                    linewidth=0.5,
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
                fontsize=fsize,
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
        texts = []
        for t in topics:
            if t.run_id.method=="DT":
                atdocscores = Doc.objects.filter(
                    docdynamictopic__topic=t,
                ).values_list('docdynamictopic__score',flat=True)

                thresh = np.quantile(atdocscores,t_thresh)

                tdocs = Doc.objects.filter(
                    docdynamictopic__topic=t,
                    docdynamictopic__score__gt=thresh
                ).order_by('-docdynamictopic__score').values_list('id',flat=True)
            else:
                atdocscores = Doc.objects.filter(
                    doctopic__topic=t,
                ).values_list('doctopic__score',flat=True)

                thresh = np.quantile(atdocscores,t_thresh)

                tdocs = Doc.objects.filter(
                    doctopic__topic=t,
                    doctopic__score__gt=thresh
                ).order_by('-doctopic__score').values_list('id',flat=True)
            highlight_docs = np.argwhere(np.isin(r_ind,tdocs))[:,0]

            if len(highlight_docs) == 0:
                continue

            points = tsne_results[highlight_docs]

            texts.append(cluster_label_points(
                t.title,
                points,
                ax,
                eps,
                min_cluster,
                n_clusters,
                clabel_size,
                words_only
            ))
    # try:
    #     adjust_text(texts, arrowprops=dict(arrowstyle="->", color='None', lw=0.5))
    # except:
    #     pass
    if doc_sets:
        for d in doc_sets:
            highlight_docs = np.argwhere(np.isin(r_ind,d['docs']))[:,0]
            points = tsne_results[highlight_docs]

            cluster_label_points(
                d['title'],
                points,
                ax,
                eps,
                min_cluster,
                n_clusters,
                clabel_size
            )


                    #adjust_text(texts,arrowprops=dict(arrowstyle='->', color='red'))
