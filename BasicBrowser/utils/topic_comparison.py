import django
from scipy.optimize import linear_sum_assignment
import networkx as nx
from networkx.algorithms import bipartite
from scipy import sparse
import pandas as pd
import numpy as np
import matplotlib.pylab as plt

from django.db.models import Q, Count, Func, F, Sum, Avg, Value as V
from tmv_app.models import *


def compare_topic_queryset(runs, method='top_word_overlap', verbosity=0, order_by_str='id'):
    """
    Compares two topic model runs

    :param runs:
    :param method:
    :param verbosity:
    :param order_by_str:
    :return:
    """

    col1s = []
    col2s = []
    ss = []
    scols = []

    stat = runs.first()

    if runs.count() == 1 and runs.first().method == "DT":
        windows = True
        runs = stat.periods.all().order_by('n')
    else:
        windows = False
        runs = runs.order_by('K').values_list('run_id', flat=True)

    for i in range(1, len(runs)):

        if windows:
            s1 = runs[i - 1]
            s2 = runs[i]
            topics1 = Topic.objects.filter(run_id=stat.parent_run_id, period=s1).order_by(order_by_str)
            topics2 = Topic.objects.filter(run_id=stat.parent_run_id, period=s2).order_by(order_by_str)

        else:
            s1 = RunStats.objects.get(pk=runs[i - 1])
            s2 = RunStats.objects.get(pk=runs[i])

            if s1.method == "DT":
                topics1 = DynamicTopic.objects.filter(run_id=runs[i - 1]).order_by(order_by_str)
            else:
                topics1 = Topic.objects.filter(run_id=runs[i - 1]).order_by(order_by_str)

            if s2.method == "DT":
                topics2 = DynamicTopic.objects.filter(run_id=runs[i]).order_by(order_by_str)
            else:
                topics2 = Topic.objects.filter(run_id=runs[i]).order_by(order_by_str)

        score_matrix = np.ndarray(shape=[len(topics1), len(topics2)])

        df = pd.DataFrame.from_dict(list(topics2.values('title', 'score')))
        # df2 = pd.DataFrame.from_dict([{'title': 'None','score': 0}])
        # df = df.append(df2)

        col1 = "run_{}_topics_{}".format(runs[i - 1], topics1.count())
        scol = "scores_{}".format(runs[i])
        bscol = "scores_{}".format(runs[i - 1])

        if i == 1:
            scols.append(bscol)

        col1s.append(col1)
        scols.append(scol)

        col2 = "run_{}_topics_{}".format(runs[i], topics2.count())

        col2s.append(col2)

        s = "similarity_{}-{}".format(runs[i - 1], runs[i])
        ss.append(s)

        df = df.rename(columns={'title': col2, 'score': scol})

        df[scol] = df[scol].astype(object)

        df[s] = 0
        df[col1] = "None"
        df[bscol] = 0
        df[bscol] = df[bscol].astype(object)

        for j, t in enumerate(topics2):
            scores = [0]
            titles = [""]
            tscores = [0]

            if method is "top_word_overlap":

                for k, ct in enumerate(topics1):
                    score = len(set(t.top_words).intersection(set(ct.top_words)))
                    if score > 0:
                        scores.append(score)
                        titles.append(ct.title)
                        tscores.append(ct.score)

                    score_matrix[k][j] = score

            elif method is "score_product":

                terms2_scores = {term2.term_title: term2.score
                                 for term2 in TopicTerm.objects.filter(topic=t).annotate(term_title=F('term__title'))}
                count = TopicTerm.objects.filter(topic=t).count()
                if verbosity > 0:
                    print("computing scores for topic #{} {} ({} terms)".format(j, t.title, count))

                for k, ct in enumerate(topics1):
                    score = 0
                    terms2 = Topic
                    for term in TopicTerm.objects.filter(topic=ct).annotate(term_title=F('term__title')):
                        try:
                            score += term.score * terms2_scores[term.term_title]
                        except KeyError:
                            # print("KeyError: {}".format(term.term.title))
                            pass

                    scores.append(score)
                    titles.append(ct.title)
                    tscores.append(ct.score)

                    score_matrix[k][j] = score

            m = max(scores)
            # df.loc[df[col2]==t.title, s] = m
            df.loc[df[col2] == t.title, s] = m
            if m == 0:
                # df.loc[df[col2]==t.title, col1] = 'None'
                df.loc[df[col2] == t.title, col1] = 'None'
            else:
                # df.loc[df[col2]==t.title, col1] = titles[scores.index(max(scores))]
                # df.loc[df[col2]==t.title, bscol] = tscores[scores.index(max(scores))]
                df.loc[df[col2] == t.title, col1] = titles[scores.index(max(scores))]
                df.loc[df[col2] == t.title, bscol] = tscores[scores.index(max(scores))]

        for c in df.columns:
            df[c] = df[c].astype(object)

        if i == 1:
            # df = pd.DataFrame.from_dict(list(topics2.values('title')))
            mdf = df
        else:
            for c in mdf.columns:
                mdf[c] = mdf[c].astype(object)
            mdf = mdf.merge(df, how="outer").fillna("")

        # print(df.head())

    columns = []
    for i in range(len(col1s)):
        columns.append(col1s[i])
        columns.append(scols[i])
        columns.append(ss[i])
        if i == len(col1s) - 1:
            columns.append(col2s[i])
            columns.append(scols[i + 1])

    print(columns)

    mdf = mdf[columns]

    res = mdf.groupby(columns)
    res = res.apply(lambda x: x.sort_values(s, ascending=False))

    res = res.drop(columns=columns)

    return [res, ss, score_matrix]


def save_res(runs, res, options):
    ss = res[1]
    res = res[0]

    max_value_colorscale = len(Topic.objects.filter(run_id=runs.first()).first().top_words)

    run_ids_str = [str(run.run_id) for run in runs]

    if runs.count() == 1 and runs.first().method == "DT":
        fname = "/tmp/run_compare_{}_windows.xlsx".format(stat.run_id)
    else:
        fname = "/tmp/run_compare_{}.xlsx".format("_".join(run_ids_str))
        if options["fname"] is not None:
            fname = "{}/run_compare_{}.xlsx".format(options["fname"], "_".join(run_ids_str))

    writer = pd.ExcelWriter(fname, engine='xlsxwriter')

    res.to_excel(writer)

    worksheet = writer.sheets['Sheet1']

    cbase = ord('A') - 1

    for i in range(len(ss)):
        n = (i + 1) * 3 - 1
        l1 = ''
        if n > 26:
            l1 = chr(cbase + n // 26)
        c = l1 + chr(cbase + n % 26 + 1)
        r = "{}2:{}{}".format(c, c, len(res))
        print(r)

        worksheet.conditional_format(r, {
            'type': '3_color_scale',
            'min_value': 0,
            'mid_value': max_value_colorscale/2,
            'max_value': max_value_colorscale,
            'min_type': 'num',
            'mid_type': 'num',
            'max_type': 'num',
        })

    writer.save()
    return 0


# match topics to each other using the Hungarian algorithm
def sort_matrix(matrix):
    cost = np.ones(shape=matrix.shape) * matrix.max() - matrix

    row_ind, col_ind = linear_sum_assignment(cost)

    sorted_matrix = matrix.copy()
    perm = np.argsort(col_ind)
    sorted_matrix = np.array(matrix[perm])

    print("matching sum:\t{}".format(matrix[row_ind, col_ind].sum()))
    print("max rows:\t{}".format(sum([row.max() for row in matrix])))
    print("max cols:\t{}".format(sum([col.max() for col in matrix.T])))

    return [sorted_matrix, perm]


def draw_score_matrix(matrix, topic_list1, topic_list2, match=False, filename=None):
    if match:
        matrix, permutation = sort_matrix(matrix)
        topic_list1 = [topic_list1[int(permutation[i])] for i in range(len(topic_list1))]
    fig, ax = plt.subplots(figsize=(10, 10))
    cax = ax.imshow(matrix)
    plt.xticks(np.arange(len(topic_list2)), [t.title for t in topic_list2], rotation='vertical', fontsize=8)
    plt.yticks(np.arange(len(topic_list1)), [t.title for t in topic_list1], fontsize=8)
    cbar = fig.colorbar(cax)

    if filename:
        plt.tight_layout()
        plt.savefig(filename, bbox_inches='tight')
    return 0


def save_topic_list_as_table(topic_list, filename):
    # test which instance topic list is!
    topic_list = [topic.top_words for topic in topic_list]
    df = pd.DataFrame.from_records(topic_list)
    # print(df)
    df.to_csv(filename)
    return 0


def bipartite_graph_from_matrix(matrix, labels1, labels2, threshold=0, match=False):
    if match:
        matrix, permutation = sort_matrix(matrix)
        labels1 = [labels1[int(permutation[i])] for i in range(len(labels1))]

    label_dict = {i: l for i, l in enumerate(labels1 + labels2)}
    print("Topic labels:", label_dict)

    if not isinstance(matrix, np.ndarray):
        matrix = np.array(matrix)
    matrix[matrix < threshold] = 0
    sp_matrix = sparse.coo_matrix(matrix)
    g = bipartite.from_biadjacency_matrix(sp_matrix)
    nx.set_node_attributes(g, label_dict, name='label')
    return g


def draw_bipartite_topic_graph(graph, filename='bipartite_topic_graph', figsize=(12, 12)):
    top_nodes = set(n for n, d in graph.nodes(data=True) if d['bipartite'] == 0)
    bottom_nodes = set(graph) - top_nodes
    top_nodes = sorted(list(top_nodes))
    bottom_nodes = sorted(list(bottom_nodes))
    pos = dict()
    pos.update((n, (0, -i)) for i, n in enumerate(top_nodes))  # put top nodes at x=0
    pos.update((n, (1, -i)) for i, n in enumerate(bottom_nodes))  # put bottom nodes at x=1
    labels = nx.get_node_attributes(graph, 'label')
    labels1 = [labels[node] for node in top_nodes]
    labels2 = [labels[node] for node in bottom_nodes]

    fig = plt.figure(figsize=figsize)

    # edges
    weights = nx.get_edge_attributes(graph, 'weight')
    if weights:
        weight_array = np.array(list(weights.values()))
        weight_array = 5. * weight_array / weight_array.max()
        # nx.draw_networkx_edges(graph,pos,width=weight_array,alpha=0.5)
        weight_array = np.sort(weight_array)
        sorted_edgelist = [i[0] for i in sorted(weights.items(), key=lambda x: x[1])]
        nx.draw_networkx_edges(graph, pos, width=3, edgelist=sorted_edgelist, edge_color=weight_array,
                               edge_cmap=plt.cm.Blues, alpha=0.5)

    else:
        nx.draw_networkx_edges(graph, pos, width=2., alpha=0.5)

    nx.draw_networkx_nodes(graph, pos,
                           node_color='r',
                           node_size=30,
                           alpha=0.8)

    ax = plt.gca()
    for i, t in enumerate(labels1):
        ax.text(-0.1, -i, t,
                horizontalalignment='right',
                verticalalignment='center',
                fontsize=12)

    for i, t in enumerate(labels2):
        ax.text(1.1, -i, t,
                horizontalalignment='left',
                verticalalignment='center',
                fontsize=12)

    # nx.draw_networkx_labels(g,pos, labels1,font_size=6)
    # nx.draw_networkx_labels(g,pos, labels2,font_size=6)
    plt.xlim([-2, 3])
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(filename + ".png", dpi=150, bbox_inches='tight')  # save as png
    plt.savefig(filename + ".pdf", bbox_inches='tight')  # save as pd

    return fig
