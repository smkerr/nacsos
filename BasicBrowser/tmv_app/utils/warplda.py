from scipy.sparse import find
def export_warp_lda(doc_ids, tfidf, vocab, run_id):
    fname = f"/tmp/yahoo_{run_id}.txt"
    with open(fname, "w") as f:
        for i in range(tfidf.shape[0]):
            words = []
            did = doc_ids[i]
            for di, ti, n in zip(*find(tfidf[i])):
                word = vocab[ti]
                words += [word]*n
            wordlist = " ".join(words)
            if i > 0:
                f.write('\n')
            f.write(f"{did} {did} {wordlist}")

    return fname
