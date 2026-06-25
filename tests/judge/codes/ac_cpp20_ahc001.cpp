#include <bits/stdc++.h>
using namespace std;

struct FastRNG {
    uint64_t x;
    FastRNG(uint64_t seed = 88172645463325252ULL) {
        x = seed ? seed : 88172645463325252ULL;
    }
    uint64_t nextU64() {
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        return x * 2685821657736338717ULL;
    }
    int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
    double nextDouble() { return (nextU64() >> 11) * (1.0 / 9007199254740992.0); }
};

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() { reset(); }
    void reset() { st = chrono::steady_clock::now(); }
    double elapsed() const {
        return chrono::duration<double>(chrono::steady_clock::now() - st).count();
    }
};

struct Rect {
    int a, b, c, d;
};

static uint64_t splitmix64_hash(uint64_t z) {
    z += 0x9e3779b97f4a7c15ULL;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

class Solver {
    static constexpr int SZ = 10000;
    static constexpr double TIME_LIMIT = 4.86;
    static constexpr double FINAL_RESERVE = 0.045;

    int n;
    vector<int> x, y;
    vector<long long> r;
    vector<double> rd, invR;
    FastRNG rng;
    Timer timer;

    struct State {
        vector<Rect> rect;
        vector<double> val;
        double total = 0.0;
    };

    struct Move {
        bool ok = false;
        int dir = 0;
        int coord = 0;
        double newScore = 0.0;
        double delta = 0.0;
    };

    struct PairMove {
        bool ok = false;
        int orient = 0;
        int i = -1, j = -1;
        int coord = 0;
        double newScoreI = 0.0;
        double newScoreJ = 0.0;
        double delta = 0.0;
    };

    struct LineComp {
        int orient = 0;
        int coord = -1;
        vector<int> A;
        vector<int> B;
    };

    struct LineMove {
        bool ok = false;
        int orient = 0;
        int coord = -1;
        int newCoord = 0;
        vector<int> A, B;
        double delta = 0.0;
    };

    struct SplitCand {
        int orient;
        int k;
        int t;
        double cost;
    };

    long long rectArea(const Rect& rc) const {
        return 1LL * (rc.c - rc.a) * (rc.d - rc.b);
    }

    double scoreOne(int i, long long s) const {
        double ratio;
        if (s <= r[i]) ratio = (double)s * invR[i];
        else ratio = rd[i] / (double)s;
        return 2.0 * ratio - ratio * ratio;
    }

    static double scoreRatio(long long s, long long target) {
        double ratio;
        if (s <= target) ratio = (double)s / (double)target;
        else ratio = (double)target / (double)s;
        return 2.0 * ratio - ratio * ratio;
    }

    State makeState(const vector<Rect>& rects) const {
        State st;
        st.rect = rects;
        st.val.assign(n, 0.0);
        for (int i = 0; i < n; i++) {
            st.val[i] = scoreOne(i, rectArea(st.rect[i]));
            st.total += st.val[i];
        }
        return st;
    }

    int clampLL(long long v, int lo, int hi) const {
        if (v < lo) return lo;
        if (v > hi) return hi;
        return (int)v;
    }

    bool yOverlap(const Rect& p, const Rect& q) const {
        return max(p.b, q.b) < min(p.d, q.d);
    }

    bool xOverlap(const Rect& p, const Rect& q) const {
        return max(p.a, q.a) < min(p.c, q.c);
    }

    bool overlapRect(const Rect& p, const Rect& q) const {
        return xOverlap(p, q) && yOverlap(p, q);
    }

    void sortIds(vector<int>& ord, int orient) const {
        if (orient == 0) {
            sort(ord.begin(), ord.end(), [&](int u, int v) {
                if (x[u] != x[v]) return x[u] < x[v];
                return y[u] < y[v];
            });
        } else {
            sort(ord.begin(), ord.end(), [&](int u, int v) {
                if (y[u] != y[v]) return y[u] < y[v];
                return x[u] < x[v];
            });
        }
    }

    vector<SplitCand> generateSplitCands(const vector<int>& ids, const Rect& box) const {
        int m = (int)ids.size();
        vector<SplitCand> cands;
        if (m <= 1) return cands;

        long long totalR = 0;
        for (int id : ids) totalR += r[id];

        long long A = rectArea(box);
        int W = box.c - box.a;
        int H = box.d - box.b;

        cands.reserve(m * 40);

        for (int orient = 0; orient < 2; orient++) {
            vector<int> ord = ids;
            sortIds(ord, orient);

            long long pref = 0;
            for (int k = 1; k < m; k++) {
                pref += r[ord[k - 1]];

                int lo, hi;
                if (orient == 0) {
                    int xl = x[ord[k - 1]];
                    int xr = x[ord[k]];
                    lo = max(box.a + 1, xl + 1);
                    hi = min(box.c - 1, xr);
                } else {
                    int yl = y[ord[k - 1]];
                    int yr = y[ord[k]];
                    lo = max(box.b + 1, yl + 1);
                    hi = min(box.d - 1, yr);
                }

                if (lo > hi) continue;

                vector<int> ts;
                ts.reserve(32);

                auto addT = [&](int t) {
                    if (t < lo || t > hi) return;
                    for (int u : ts) if (u == t) return;
                    ts.push_back(t);
                };

                auto addReal = [&](long double real) {
                    long long f = (long long)floorl(real);
                    for (long long v = f - 2; v <= f + 2; v++) {
                        addT(clampLL(v, lo, hi));
                    }
                    long long rr = (long long)llroundl(real);
                    for (long long v = rr - 1; v <= rr + 1; v++) {
                        addT(clampLL(v, lo, hi));
                    }
                };

                if (orient == 0) {
                    long double prop = box.a + ((long double)A * pref / totalR) / H;
                    long double exactL = box.a + (long double)pref / H;
                    long double exactR = box.a + ((long double)A - (long double)(totalR - pref)) / H;
                    addReal(prop);
                    addReal(exactL);
                    addReal(exactR);
                } else {
                    long double prop = box.b + ((long double)A * pref / totalR) / W;
                    long double exactL = box.b + (long double)pref / W;
                    long double exactR = box.b + ((long double)A - (long double)(totalR - pref)) / W;
                    addReal(prop);
                    addReal(exactL);
                    addReal(exactR);
                }

                addT(lo);
                addT(hi);

                for (int t : ts) {
                    long long leftA;
                    if (orient == 0) leftA = 1LL * (t - box.a) * H;
                    else leftA = 1LL * W * (t - box.b);

                    long long rightA = A - leftA;
                    if (leftA <= 0 || rightA <= 0) continue;

                    double sc =
                        k * scoreRatio(leftA, pref) +
                        (m - k) * scoreRatio(rightA, totalR - pref);

                    double loss = 1.0 - sc / m;

                    auto aspectPenalty = [&](int ww, int hh, int cnt) -> double {
                        if (cnt <= 1) return 0.0;
                        double ar = max((double)ww / hh, (double)hh / ww);
                        return 0.00025 * (cnt / (double)m) * max(0.0, log(ar) - 2.0);
                    };

                    double cost = loss;
                    cost += 0.00020 * abs(m - 2 * k) / (double)m;

                    if (orient == 0) {
                        cost += aspectPenalty(t - box.a, H, k);
                        cost += aspectPenalty(box.c - t, H, m - k);
                    } else {
                        cost += aspectPenalty(W, t - box.b, k);
                        cost += aspectPenalty(W, box.d - t, m - k);
                    }

                    cands.push_back({orient, k, t, cost});
                }
            }
        }

        return cands;
    }

    void buildRec(const vector<int>& ids, const Rect& box, vector<Rect>& out, double temp) {
        int m = (int)ids.size();
        if (m == 1) {
            out[ids[0]] = box;
            return;
        }

        vector<SplitCand> cands = generateSplitCands(ids, box);

        if (cands.empty()) {
            for (int id : ids) {
                out[id] = {x[id], y[id], x[id] + 1, y[id] + 1};
            }
            return;
        }

        sort(cands.begin(), cands.end(), [](const SplitCand& p, const SplitCand& q) {
            return p.cost < q.cost;
        });

        int chosen = 0;
        if (temp > 1e-12) {
            double bestCost = cands[0].cost;
            double maxDiff = max(0.03, temp * 12.0);

            vector<pair<int, double>> cumulative;
            double sum = 0.0;
            for (int i = 0; i < (int)cands.size(); i++) {
                double diff = cands[i].cost - bestCost;
                if (diff > maxDiff) continue;
                double w = exp(-diff / temp);
                if (w < 1e-12) continue;
                sum += w;
                cumulative.push_back({i, sum});
            }

            if (sum > 0.0) {
                double z = rng.nextDouble() * sum;
                for (auto [idx, cum] : cumulative) {
                    if (z <= cum) {
                        chosen = idx;
                        break;
                    }
                }
            }
        }

        SplitCand sp = cands[chosen];

        vector<int> ord = ids;
        sortIds(ord, sp.orient);

        vector<int> leftIds(ord.begin(), ord.begin() + sp.k);
        vector<int> rightIds(ord.begin() + sp.k, ord.end());

        if (sp.orient == 0) {
            Rect L{box.a, box.b, sp.t, box.d};
            Rect R{sp.t, box.b, box.c, box.d};
            buildRec(leftIds, L, out, temp);
            buildRec(rightIds, R, out, temp);
        } else {
            Rect B{box.a, box.b, box.c, sp.t};
            Rect T{box.a, sp.t, box.c, box.d};
            buildRec(leftIds, B, out, temp);
            buildRec(rightIds, T, out, temp);
        }
    }

    double scoreIds(const vector<Rect>& rects, const vector<int>& ids) const {
        double s = 0.0;
        for (int id : ids) s += scoreOne(id, rectArea(rects[id]));
        return s;
    }

    double buildRecBeam(const vector<int>& ids, const Rect& box, vector<Rect>& out, double stopTime) {
        int m = (int)ids.size();
        if (m == 1) {
            out[ids[0]] = box;
            return scoreOne(ids[0], rectArea(box));
        }

        if (timer.elapsed() > stopTime) {
            buildRec(ids, box, out, 0.0);
            return scoreIds(out, ids);
        }

        vector<SplitCand> cands = generateSplitCands(ids, box);
        if (cands.empty()) {
            for (int id : ids) out[id] = {x[id], y[id], x[id] + 1, y[id] + 1};
            return scoreIds(out, ids);
        }

        sort(cands.begin(), cands.end(), [](const SplitCand& p, const SplitCand& q) {
            return p.cost < q.cost;
        });

        int width;
        if (m <= 3) width = 10;
        else if (m <= 5) width = 5;
        else width = 3;

        width = min(width, (int)cands.size());

        double best = -1e100;
        vector<Rect> bestOut = out;

        for (int ci = 0; ci < width; ci++) {
            if (timer.elapsed() > stopTime) break;

            SplitCand sp = cands[ci];
            vector<int> ord = ids;
            sortIds(ord, sp.orient);

            vector<int> leftIds(ord.begin(), ord.begin() + sp.k);
            vector<int> rightIds(ord.begin() + sp.k, ord.end());

            vector<Rect> tmp = out;
            double sc = 0.0;

            if (sp.orient == 0) {
                Rect L{box.a, box.b, sp.t, box.d};
                Rect R{sp.t, box.b, box.c, box.d};
                sc += buildRecBeam(leftIds, L, tmp, stopTime);
                sc += buildRecBeam(rightIds, R, tmp, stopTime);
            } else {
                Rect B{box.a, box.b, box.c, sp.t};
                Rect T{box.a, sp.t, box.c, box.d};
                sc += buildRecBeam(leftIds, B, tmp, stopTime);
                sc += buildRecBeam(rightIds, T, tmp, stopTime);
            }

            if (sc > best) {
                best = sc;
                bestOut = std::move(tmp);
            }
        }

        if (best < -1e90) {
            buildRec(ids, box, out, 0.0);
            return scoreIds(out, ids);
        }

        out = std::move(bestOut);
        return best;
    }

    vector<Rect> buildRecursive(double temp) {
        vector<Rect> out(n);
        vector<int> ids(n);
        iota(ids.begin(), ids.end(), 0);
        buildRec(ids, Rect{0, 0, SZ, SZ}, out, temp);
        return out;
    }

    vector<Rect> buildUnit() const {
        vector<Rect> rects(n);
        for (int i = 0; i < n; i++) {
            rects[i] = {x[i], y[i], x[i] + 1, y[i] + 1};
        }
        return rects;
    }

    pair<int, int> legalInterval(const State& st, int i, int dir) const {
        const Rect& ri = st.rect[i];

        if (dir == 0) {
            int lo = 0;
            int hi = min(x[i], ri.c - 1);
            for (int j = 0; j < n; j++) if (j != i) {
                const Rect& rj = st.rect[j];
                if (yOverlap(ri, rj) && rj.a < ri.c) {
                    lo = max(lo, rj.c);
                }
            }
            return {lo, hi};
        }

        if (dir == 1) {
            int lo = max(x[i] + 1, ri.a + 1);
            int hi = SZ;
            for (int j = 0; j < n; j++) if (j != i) {
                const Rect& rj = st.rect[j];
                if (yOverlap(ri, rj) && rj.c > ri.a) {
                    hi = min(hi, rj.a);
                }
            }
            return {lo, hi};
        }

        if (dir == 2) {
            int lo = 0;
            int hi = min(y[i], ri.d - 1);
            for (int j = 0; j < n; j++) if (j != i) {
                const Rect& rj = st.rect[j];
                if (xOverlap(ri, rj) && rj.b < ri.d) {
                    lo = max(lo, rj.d);
                }
            }
            return {lo, hi};
        }

        int lo = max(y[i] + 1, ri.b + 1);
        int hi = SZ;
        for (int j = 0; j < n; j++) if (j != i) {
            const Rect& rj = st.rect[j];
            if (xOverlap(ri, rj) && rj.d > ri.b) {
                hi = min(hi, rj.b);
            }
        }
        return {lo, hi};
    }

    int getCoord(const Rect& rc, int dir) const {
        if (dir == 0) return rc.a;
        if (dir == 1) return rc.c;
        if (dir == 2) return rc.b;
        return rc.d;
    }

    void setCoord(Rect& rc, int dir, int v) {
        if (dir == 0) rc.a = v;
        else if (dir == 1) rc.c = v;
        else if (dir == 2) rc.b = v;
        else rc.d = v;
    }

    long long areaAfterCoord(const Rect& rc, int dir, int coord) const {
        if (dir == 0) return 1LL * (rc.c - coord) * (rc.d - rc.b);
        if (dir == 1) return 1LL * (coord - rc.a) * (rc.d - rc.b);
        if (dir == 2) return 1LL * (rc.c - rc.a) * (rc.d - coord);
        return 1LL * (rc.c - rc.a) * (coord - rc.b);
    }

    Move bestEdgeDir(const State& st, int i, int dir) const {
        Move mv;
        auto [lo, hi] = legalInterval(st, i, dir);
        if (lo > hi) return mv;

        const Rect& rc = st.rect[i];
        int cur = getCoord(rc, dir);

        mv.ok = true;
        mv.dir = dir;
        mv.coord = cur;
        mv.newScore = st.val[i];
        mv.delta = 0.0;

        int cand[48];
        int cnt = 0;

        auto addCand = [&](int v) {
            if (v < lo) v = lo;
            if (v > hi) v = hi;
            for (int k = 0; k < cnt; k++) if (cand[k] == v) return;
            cand[cnt++] = v;
        };

        addCand(cur);
        addCand(lo);
        addCand(hi);

        long double real;
        if (dir == 0 || dir == 1) {
            int h = rc.d - rc.b;
            long double wantW = (long double)r[i] / h;
            if (dir == 0) real = rc.c - wantW;
            else real = rc.a + wantW;
        } else {
            int w = rc.c - rc.a;
            long double wantH = (long double)r[i] / w;
            if (dir == 2) real = rc.d - wantH;
            else real = rc.b + wantH;
        }

        long long f = (long long)floorl(real);
        for (long long v = f - 5; v <= f + 5; v++) {
            addCand(clampLL(v, lo, hi));
        }

        double bestScore = st.val[i];
        int bestCoord = cur;

        for (int k = 0; k < cnt; k++) {
            int v = cand[k];
            long long ar = areaAfterCoord(rc, dir, v);
            double ns = scoreOne(i, ar);
            if (ns > bestScore + 1e-15) {
                bestScore = ns;
                bestCoord = v;
            }
        }

        mv.coord = bestCoord;
        mv.newScore = bestScore;
        mv.delta = bestScore - st.val[i];
        return mv;
    }

    Move bestMove(const State& st, int i) const {
        Move best;
        best.newScore = st.val[i];
        for (int dir = 0; dir < 4; dir++) {
            Move mv = bestEdgeDir(st, i, dir);
            if (!mv.ok) continue;
            if (!best.ok || mv.delta > best.delta) best = mv;
        }
        return best;
    }

    void applyCoord(State& st, int i, int dir, int coord, double newScore) {
        setCoord(st.rect[i], dir, coord);
        st.total += newScore - st.val[i];
        st.val[i] = newScore;
    }

    void applyMove(State& st, int i, const Move& mv) {
        applyCoord(st, i, mv.dir, mv.coord, mv.newScore);
    }

    PairMove bestPairVertical(const State& st, int li, int ri) const {
        PairMove pm;
        pm.orient = 0;
        pm.i = li;
        pm.j = ri;

        if (li == ri) return pm;
        const Rect& L = st.rect[li];
        const Rect& R = st.rect[ri];

        if (L.c > R.a) return pm;
        if (!yOverlap(L, R)) return pm;

        int lo1 = max(x[li] + 1, L.a + 1);
        int hi1 = SZ;
        for (int k = 0; k < n; k++) if (k != li && k != ri) {
            const Rect& K = st.rect[k];
            if (yOverlap(L, K) && K.c > L.a) hi1 = min(hi1, K.a);
        }

        int lo2 = 0;
        int hi2 = min(x[ri], R.c - 1);
        for (int k = 0; k < n; k++) if (k != li && k != ri) {
            const Rect& K = st.rect[k];
            if (yOverlap(R, K) && K.a < R.c) lo2 = max(lo2, K.c);
        }

        int lo = max(lo1, lo2);
        int hi = min(hi1, hi2);
        if (lo > hi) return pm;

        int hL = L.d - L.b;
        int hR = R.d - R.b;

        auto eval = [&](int t) -> double {
            long long a1 = 1LL * (t - L.a) * hL;
            long long a2 = 1LL * (R.c - t) * hR;
            return scoreOne(li, a1) + scoreOne(ri, a2);
        };

        double bestScore = -1e100;
        int bestT = lo;

        auto test = [&](int t) {
            if (t < lo || t > hi) return;
            double sc = eval(t);
            if (sc > bestScore + 1e-15) {
                bestScore = sc;
                bestT = t;
            }
        };

        test(lo);
        test(hi);
        test(clampLL(L.c, lo, hi));
        test(clampLL(R.a, lo, hi));
        test(lo + (hi - lo) / 2);
        test(lo + (hi - lo) / 4);
        test(lo + 3 * (hi - lo) / 4);

        auto addReal = [&](long double z) {
            long long f = (long long)floorl(z);
            for (long long v = f - 6; v <= f + 6; v++) test(clampLL(v, lo, hi));
        };

        addReal((long double)L.a + (long double)r[li] / hL);
        addReal((long double)R.c - (long double)r[ri] / hR);

        int TL = lo, TR = hi;
        while (TR - TL > 40) {
            int m1 = TL + (TR - TL) / 3;
            int m2 = TR - (TR - TL) / 3;
            if (eval(m1) < eval(m2)) TL = m1;
            else TR = m2;
        }
        for (int t = TL; t <= TR; t++) test(t);

        long long a1 = 1LL * (bestT - L.a) * hL;
        long long a2 = 1LL * (R.c - bestT) * hR;

        pm.ok = true;
        pm.coord = bestT;
        pm.newScoreI = scoreOne(li, a1);
        pm.newScoreJ = scoreOne(ri, a2);
        pm.delta = pm.newScoreI + pm.newScoreJ - st.val[li] - st.val[ri];
        return pm;
    }

    PairMove bestPairHorizontal(const State& st, int bi, int ti) const {
        PairMove pm;
        pm.orient = 1;
        pm.i = bi;
        pm.j = ti;

        if (bi == ti) return pm;
        const Rect& B = st.rect[bi];
        const Rect& T = st.rect[ti];

        if (B.d > T.b) return pm;
        if (!xOverlap(B, T)) return pm;

        int lo1 = max(y[bi] + 1, B.b + 1);
        int hi1 = SZ;
        for (int k = 0; k < n; k++) if (k != bi && k != ti) {
            const Rect& K = st.rect[k];
            if (xOverlap(B, K) && K.d > B.b) hi1 = min(hi1, K.b);
        }

        int lo2 = 0;
        int hi2 = min(y[ti], T.d - 1);
        for (int k = 0; k < n; k++) if (k != bi && k != ti) {
            const Rect& K = st.rect[k];
            if (xOverlap(T, K) && K.b < T.d) lo2 = max(lo2, K.d);
        }

        int lo = max(lo1, lo2);
        int hi = min(hi1, hi2);
        if (lo > hi) return pm;

        int wB = B.c - B.a;
        int wT = T.c - T.a;

        auto eval = [&](int t) -> double {
            long long a1 = 1LL * wB * (t - B.b);
            long long a2 = 1LL * wT * (T.d - t);
            return scoreOne(bi, a1) + scoreOne(ti, a2);
        };

        double bestScore = -1e100;
        int bestT = lo;

        auto test = [&](int t) {
            if (t < lo || t > hi) return;
            double sc = eval(t);
            if (sc > bestScore + 1e-15) {
                bestScore = sc;
                bestT = t;
            }
        };

        test(lo);
        test(hi);
        test(clampLL(B.d, lo, hi));
        test(clampLL(T.b, lo, hi));
        test(lo + (hi - lo) / 2);
        test(lo + (hi - lo) / 4);
        test(lo + 3 * (hi - lo) / 4);

        auto addReal = [&](long double z) {
            long long f = (long long)floorl(z);
            for (long long v = f - 6; v <= f + 6; v++) test(clampLL(v, lo, hi));
        };

        addReal((long double)B.b + (long double)r[bi] / wB);
        addReal((long double)T.d - (long double)r[ti] / wT);

        int TL = lo, TR = hi;
        while (TR - TL > 40) {
            int m1 = TL + (TR - TL) / 3;
            int m2 = TR - (TR - TL) / 3;
            if (eval(m1) < eval(m2)) TL = m1;
            else TR = m2;
        }
        for (int t = TL; t <= TR; t++) test(t);

        long long a1 = 1LL * wB * (bestT - B.b);
        long long a2 = 1LL * wT * (T.d - bestT);

        pm.ok = true;
        pm.coord = bestT;
        pm.newScoreI = scoreOne(bi, a1);
        pm.newScoreJ = scoreOne(ti, a2);
        pm.delta = pm.newScoreI + pm.newScoreJ - st.val[bi] - st.val[ti];
        return pm;
    }

    void applyPair(State& st, const PairMove& pm) {
        int i = pm.i;
        int j = pm.j;

        if (pm.orient == 0) {
            st.rect[i].c = pm.coord;
            st.rect[j].a = pm.coord;
        } else {
            st.rect[i].d = pm.coord;
            st.rect[j].b = pm.coord;
        }

        st.total += pm.newScoreI - st.val[i];
        st.total += pm.newScoreJ - st.val[j];

        st.val[i] = pm.newScoreI;
        st.val[j] = pm.newScoreJ;
    }

    void shuffleVector(vector<int>& v) {
        for (int i = (int)v.size() - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            swap(v[i], v[j]);
        }
    }

    int selectBad(const State& st) {
        int best = rng.nextInt(n);
        double bv = st.val[best];

        int K = min(n, 6);
        for (int k = 1; k < K; k++) {
            int j = rng.nextInt(n);
            if (st.val[j] < bv) {
                bv = st.val[j];
                best = j;
            }
        }
        return best;
    }

    bool greedyPasses(State& st, int passes, double stopTime) {
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);

        bool globalAny = false;

        for (int pass = 0; pass < passes; pass++) {
            if (timer.elapsed() > stopTime) return globalAny;
            shuffleVector(ord);

            bool any = false;
            for (int id : ord) {
                for (int rep = 0; rep < 4; rep++) {
                    Move mv = bestMove(st, id);
                    if (mv.ok && mv.delta > 1e-12) {
                        applyMove(st, id, mv);
                        any = true;
                        globalAny = true;
                    } else {
                        break;
                    }
                }
            }
            if (!any) break;
        }

        return globalAny;
    }

    bool pairGreedyPasses(State& st, int passes, double stopTime) {
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);

        bool globalAny = false;

        for (int pass = 0; pass < passes; pass++) {
            shuffleVector(ord);
            bool any = false;
            int checks = 0;

            for (int ai = 0; ai < n; ai++) {
                int i = ord[ai];
                for (int bj = ai + 1; bj < n; bj++) {
                    if ((checks++ & 255) == 0 && timer.elapsed() > stopTime) return globalAny;

                    int j = ord[bj];
                    const Rect& A = st.rect[i];
                    const Rect& B = st.rect[j];

                    PairMove best;
                    best.delta = 0.0;

                    if (yOverlap(A, B)) {
                        PairMove mv;
                        if (A.c <= B.a) mv = bestPairVertical(st, i, j);
                        else if (B.c <= A.a) mv = bestPairVertical(st, j, i);
                        if (mv.ok && (!best.ok || mv.delta > best.delta)) best = mv;
                    }

                    if (xOverlap(A, B)) {
                        PairMove mv;
                        if (A.d <= B.b) mv = bestPairHorizontal(st, i, j);
                        else if (B.d <= A.b) mv = bestPairHorizontal(st, j, i);
                        if (mv.ok && (!best.ok || mv.delta > best.delta)) best = mv;
                    }

                    if (best.ok && best.delta > 1e-12) {
                        applyPair(st, best);
                        any = true;
                        globalAny = true;
                    }
                }
            }

            if (!any) break;
        }

        return globalAny;
    }

    vector<LineComp> buildLineComponents(const State& st, int orient) const {
        vector<int> coords;
        coords.reserve(2 * n);

        for (int i = 0; i < n; i++) {
            const Rect& rc = st.rect[i];
            if (orient == 0) {
                if (0 < rc.c && rc.c < SZ) coords.push_back(rc.c);
                if (0 < rc.a && rc.a < SZ) coords.push_back(rc.a);
            } else {
                if (0 < rc.d && rc.d < SZ) coords.push_back(rc.d);
                if (0 < rc.b && rc.b < SZ) coords.push_back(rc.b);
            }
        }

        sort(coords.begin(), coords.end());
        coords.erase(unique(coords.begin(), coords.end()), coords.end());

        vector<LineComp> comps;

        for (int coord : coords) {
            vector<int> A, B;
            for (int i = 0; i < n; i++) {
                const Rect& rc = st.rect[i];
                if (orient == 0) {
                    if (rc.c == coord) A.push_back(i);
                    if (rc.a == coord) B.push_back(i);
                } else {
                    if (rc.d == coord) A.push_back(i);
                    if (rc.b == coord) B.push_back(i);
                }
            }

            if (A.empty() || B.empty()) continue;

            int na = (int)A.size();
            int nb = (int)B.size();
            vector<vector<int>> adj(na + nb);

            for (int i = 0; i < na; i++) {
                for (int j = 0; j < nb; j++) {
                    bool ov = (orient == 0)
                        ? yOverlap(st.rect[A[i]], st.rect[B[j]])
                        : xOverlap(st.rect[A[i]], st.rect[B[j]]);
                    if (ov) {
                        adj[i].push_back(na + j);
                        adj[na + j].push_back(i);
                    }
                }
            }

            vector<char> vis(na + nb, 0);
            for (int s = 0; s < na + nb; s++) {
                if (vis[s]) continue;

                vector<int> q = {s};
                vis[s] = 1;
                for (int qi = 0; qi < (int)q.size(); qi++) {
                    int v = q[qi];
                    for (int to : adj[v]) {
                        if (!vis[to]) {
                            vis[to] = 1;
                            q.push_back(to);
                        }
                    }
                }

                LineComp cp;
                cp.orient = orient;
                cp.coord = coord;

                for (int v : q) {
                    if (v < na) cp.A.push_back(A[v]);
                    else cp.B.push_back(B[v - na]);
                }

                if (!cp.A.empty() && !cp.B.empty()) comps.push_back(std::move(cp));
            }
        }

        return comps;
    }

    bool componentInternalOK(const State& st, const LineComp& cp) const {
        vector<unsigned char> side(n, 0);

        for (int id : cp.A) {
            if (side[id] & 1) return false;
            side[id] |= 1;
        }
        for (int id : cp.B) {
            if (side[id] & 2) return false;
            if (side[id] & 1) return false;
            side[id] |= 2;
        }

        auto perpOverlap = [&](int u, int v) -> bool {
            if (cp.orient == 0) return yOverlap(st.rect[u], st.rect[v]);
            else return xOverlap(st.rect[u], st.rect[v]);
        };

        for (int i = 0; i < (int)cp.A.size(); i++) {
            for (int j = i + 1; j < (int)cp.A.size(); j++) {
                if (perpOverlap(cp.A[i], cp.A[j])) return false;
            }
        }
        for (int i = 0; i < (int)cp.B.size(); i++) {
            for (int j = i + 1; j < (int)cp.B.size(); j++) {
                if (perpOverlap(cp.B[i], cp.B[j])) return false;
            }
        }

        return true;
    }

    vector<LineComp> buildFrontierComponents(const State& st, int orient) const {
        const int INF = 1e9;
        vector<int> bestA(n, INF), bestB(n, INF);

        auto canFace = [&](int i, int j, int& gap) -> bool {
            if (i == j) return false;
            const Rect& P = st.rect[i];
            const Rect& Q = st.rect[j];

            if (orient == 0) {
                if (!yOverlap(P, Q)) return false;
                if (P.c <= Q.a) {
                    gap = Q.a - P.c;
                    return true;
                }
            } else {
                if (!xOverlap(P, Q)) return false;
                if (P.d <= Q.b) {
                    gap = Q.b - P.d;
                    return true;
                }
            }
            return false;
        };

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                int gap;
                if (canFace(i, j, gap)) {
                    bestA[i] = min(bestA[i], gap);
                    bestB[j] = min(bestB[j], gap);
                }
            }
        }

        vector<vector<int>> adj(2 * n);

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                int gap;
                if (canFace(i, j, gap)) {
                    if (gap == bestA[i] && gap == bestB[j]) {
                        adj[i].push_back(n + j);
                        adj[n + j].push_back(i);
                    }
                }
            }
        }

        vector<LineComp> comps;
        vector<char> vis(2 * n, 0);

        for (int s = 0; s < 2 * n; s++) {
            if (vis[s] || adj[s].empty()) continue;

            vector<int> q = {s};
            vis[s] = 1;

            for (int qi = 0; qi < (int)q.size(); qi++) {
                int v = q[qi];
                for (int to : adj[v]) {
                    if (!vis[to]) {
                        vis[to] = 1;
                        q.push_back(to);
                    }
                }
            }

            LineComp cp;
            cp.orient = orient;
            cp.coord = -1;

            for (int v : q) {
                if (v < n) cp.A.push_back(v);
                else cp.B.push_back(v - n);
            }

            if (cp.A.empty() || cp.B.empty()) continue;
            if (!componentInternalOK(st, cp)) continue;

            bool sameCoord = true;
            int common = -1;

            auto feedCoord = [&](int z) {
                if (common < 0) common = z;
                else if (common != z) sameCoord = false;
            };

            if (orient == 0) {
                for (int id : cp.A) feedCoord(st.rect[id].c);
                for (int id : cp.B) feedCoord(st.rect[id].a);
            } else {
                for (int id : cp.A) feedCoord(st.rect[id].d);
                for (int id : cp.B) feedCoord(st.rect[id].b);
            }

            if (sameCoord) continue;
            comps.push_back(std::move(cp));
        }

        return comps;
    }

    LineMove bestBoundaryComponent(const State& st, const LineComp& cp, double stopTime) {
        LineMove lm;
        lm.orient = cp.orient;
        lm.coord = cp.coord;
        lm.A = cp.A;
        lm.B = cp.B;

        if (cp.A.empty() || cp.B.empty()) return lm;
        if (!componentInternalOK(st, cp)) return lm;

        if (cp.coord >= 0) {
            if (cp.orient == 0) {
                for (int id : cp.A) if (st.rect[id].c != cp.coord) return lm;
                for (int id : cp.B) if (st.rect[id].a != cp.coord) return lm;
            } else {
                for (int id : cp.A) if (st.rect[id].d != cp.coord) return lm;
                for (int id : cp.B) if (st.rect[id].b != cp.coord) return lm;
            }
        }

        vector<char> moved(n, 0);
        double curScore = 0.0;

        for (int id : cp.A) {
            if (!moved[id]) {
                moved[id] = 1;
                curScore += st.val[id];
            }
        }
        for (int id : cp.B) {
            if (!moved[id]) {
                moved[id] = 1;
                curScore += st.val[id];
            }
        }

        int lo = 0;
        int hi = SZ;

        if (cp.orient == 0) {
            for (int id : cp.A) {
                const Rect& ri = st.rect[id];
                lo = max(lo, max(x[id] + 1, ri.a + 1));

                for (int k = 0; k < n; k++) if (!moved[k]) {
                    const Rect& rk = st.rect[k];
                    if (yOverlap(ri, rk) && rk.c > ri.a) hi = min(hi, rk.a);
                }
            }

            for (int id : cp.B) {
                const Rect& ri = st.rect[id];
                hi = min(hi, min(x[id], ri.c - 1));

                for (int k = 0; k < n; k++) if (!moved[k]) {
                    const Rect& rk = st.rect[k];
                    if (yOverlap(ri, rk) && rk.a < ri.c) lo = max(lo, rk.c);
                }
            }
        } else {
            for (int id : cp.A) {
                const Rect& ri = st.rect[id];
                lo = max(lo, max(y[id] + 1, ri.b + 1));

                for (int k = 0; k < n; k++) if (!moved[k]) {
                    const Rect& rk = st.rect[k];
                    if (xOverlap(ri, rk) && rk.d > ri.b) hi = min(hi, rk.b);
                }
            }

            for (int id : cp.B) {
                const Rect& ri = st.rect[id];
                hi = min(hi, min(y[id], ri.d - 1));

                for (int k = 0; k < n; k++) if (!moved[k]) {
                    const Rect& rk = st.rect[k];
                    if (xOverlap(ri, rk) && rk.b < ri.d) lo = max(lo, rk.d);
                }
            }
        }

        if (lo > hi) return lm;

        auto eval = [&](int t) -> double {
            double sc = 0.0;

            if (cp.orient == 0) {
                for (int id : cp.A) {
                    const Rect& rc = st.rect[id];
                    long long ar = 1LL * (t - rc.a) * (rc.d - rc.b);
                    sc += scoreOne(id, ar);
                }
                for (int id : cp.B) {
                    const Rect& rc = st.rect[id];
                    long long ar = 1LL * (rc.c - t) * (rc.d - rc.b);
                    sc += scoreOne(id, ar);
                }
            } else {
                for (int id : cp.A) {
                    const Rect& rc = st.rect[id];
                    long long ar = 1LL * (rc.c - rc.a) * (t - rc.b);
                    sc += scoreOne(id, ar);
                }
                for (int id : cp.B) {
                    const Rect& rc = st.rect[id];
                    long long ar = 1LL * (rc.c - rc.a) * (rc.d - t);
                    sc += scoreOne(id, ar);
                }
            }

            return sc;
        };

        double bestScore = curScore;
        int bestT = (cp.coord >= 0 ? clampLL(cp.coord, lo, hi) : lo);

        for (int t = lo; t <= hi; t++) {
            if (((t - lo) & 1023) == 0 && timer.elapsed() > stopTime) break;
            double sc = eval(t);
            if (sc > bestScore + 1e-15) {
                bestScore = sc;
                bestT = t;
            }
        }

        lm.ok = true;
        lm.newCoord = bestT;
        lm.delta = bestScore - curScore;
        return lm;
    }

    void applyLineMove(State& st, const LineMove& lm) {
        int t = lm.newCoord;

        if (lm.orient == 0) {
            for (int id : lm.A) st.rect[id].c = t;
            for (int id : lm.B) st.rect[id].a = t;
        } else {
            for (int id : lm.A) st.rect[id].d = t;
            for (int id : lm.B) st.rect[id].b = t;
        }

        vector<char> upd(n, 0);
        for (int id : lm.A) {
            if (!upd[id]) {
                upd[id] = 1;
                double ns = scoreOne(id, rectArea(st.rect[id]));
                st.total += ns - st.val[id];
                st.val[id] = ns;
            }
        }
        for (int id : lm.B) {
            if (!upd[id]) {
                upd[id] = 1;
                double ns = scoreOne(id, rectArea(st.rect[id]));
                st.total += ns - st.val[id];
                st.val[id] = ns;
            }
        }
    }

    bool boundarySequentialPass(State& st, int orient, bool includeFrontier, double stopTime) {
        vector<LineComp> comps = buildLineComponents(st, orient);

        if (includeFrontier) {
            vector<LineComp> extra = buildFrontierComponents(st, orient);
            for (auto& cp : extra) comps.push_back(std::move(cp));
        }

        sort(comps.begin(), comps.end(), [](const LineComp& p, const LineComp& q) {
            int sp = (int)p.A.size() + (int)p.B.size();
            int sq = (int)q.A.size() + (int)q.B.size();
            if (sp != sq) return sp > sq;
            bool lp = p.coord >= 0;
            bool lq = q.coord >= 0;
            if (lp != lq) return lp > lq;
            return p.coord < q.coord;
        });

        bool any = false;

        for (const LineComp& cp : comps) {
            if (timer.elapsed() > stopTime) break;

            LineMove mv = bestBoundaryComponent(st, cp, stopTime);
            if (mv.ok && mv.delta > 1e-12) {
                applyLineMove(st, mv);
                any = true;
            }
        }

        return any;
    }

    bool boundaryGreedyPasses(State& st, int passes, double stopTime, bool includeFrontier) {
        bool globalAny = false;

        for (int pass = 0; pass < passes; pass++) {
            if (timer.elapsed() > stopTime) return globalAny;

            bool any = false;
            if (rng.nextInt(2) == 0) {
                any |= boundarySequentialPass(st, 0, includeFrontier, stopTime);
                any |= boundarySequentialPass(st, 1, includeFrontier, stopTime);
            } else {
                any |= boundarySequentialPass(st, 1, includeFrontier, stopTime);
                any |= boundarySequentialPass(st, 0, includeFrontier, stopTime);
            }

            if (!any) break;
            globalAny = true;
        }

        return globalAny;
    }

    Rect groupBoundingBox(const State& st, const vector<int>& ids) const {
        Rect box{SZ, SZ, 0, 0};
        for (int id : ids) {
            const Rect& rc = st.rect[id];
            box.a = min(box.a, rc.a);
            box.b = min(box.b, rc.b);
            box.c = max(box.c, rc.c);
            box.d = max(box.d, rc.d);
        }
        return box;
    }

    bool bboxClearForGroup(const State& st, const vector<int>& ids, const Rect& box) const {
        vector<char> in(n, 0);
        for (int id : ids) in[id] = 1;
        for (int i = 0; i < n; i++) {
            if (in[i]) continue;
            if (overlapRect(st.rect[i], box)) return false;
        }
        return true;
    }

    long long desiredSum(const vector<int>& ids) const {
        long long s = 0;
        for (int id : ids) s += r[id];
        return s;
    }

    bool boxUsableForGroup(const State& st, const vector<int>& ids, const Rect& box) const {
        if (!(0 <= box.a && box.a < box.c && box.c <= SZ)) return false;
        if (!(0 <= box.b && box.b < box.d && box.d <= SZ)) return false;

        for (int id : ids) {
            if (!(box.a <= x[id] && x[id] + 1 <= box.c)) return false;
            if (!(box.b <= y[id] && y[id] + 1 <= box.d)) return false;
        }

        return bboxClearForGroup(st, ids, box);
    }

    vector<Rect> alternativeRepackBoxes(const State& st, const vector<int>& ids, const Rect& orig) const {
        vector<Rect> res;

        long long S = 0;
        int minX = SZ, minY = SZ, maxX1 = 0, maxY1 = 0;

        for (int id : ids) {
            S += r[id];
            minX = min(minX, x[id]);
            minY = min(minY, y[id]);
            maxX1 = max(maxX1, x[id] + 1);
            maxY1 = max(maxY1, y[id] + 1);
        }

        int pW = max(1, maxX1 - minX);
        int pH = max(1, maxY1 - minY);
        int oW = orig.c - orig.a;
        int oH = orig.d - orig.b;

        auto sameBox = [](const Rect& u, const Rect& v) {
            return u.a == v.a && u.b == v.b && u.c == v.c && u.d == v.d;
        };

        auto addRect = [&](const Rect& bx) {
            if ((int)res.size() >= 4) return;
            if (sameBox(bx, orig)) return;
            if (!boxUsableForGroup(st, ids, bx)) return;
            for (const Rect& e : res) if (sameBox(e, bx)) return;
            res.push_back(bx);
        };

        auto ceilDiv = [](long long a, long long b) -> long long {
            return (a + b - 1) / b;
        };

        auto trySize = [&](long long W0, long long H0) {
            if ((int)res.size() >= 4) return;
            if (W0 <= 0 || H0 <= 0) return;

            long long W = max<long long>(W0, pW);
            long long H = max<long long>(H0, pH);

            if (W > SZ) return;

            long long needH = ceilDiv(S, W);
            if (H < needH) H = needH;

            if (H > SZ) {
                H = SZ;
                long long needW = ceilDiv(S, H);
                if (W < needW) W = needW;
            }

            if (W > SZ || H > SZ) return;

            int w = (int)W;
            int h = (int)H;

            auto placements = [&](bool inside) {
                int alo = max(0, maxX1 - w);
                int ahi = min(minX, SZ - w);
                int blo = max(0, maxY1 - h);
                int bhi = min(minY, SZ - h);

                if (inside) {
                    alo = max(alo, orig.a);
                    ahi = min(ahi, orig.c - w);
                    blo = max(blo, orig.b);
                    bhi = min(bhi, orig.d - h);
                }

                if (alo > ahi || blo > bhi) return;

                vector<int> As, Bs;
                auto addA = [&](long long v) {
                    int z = clampLL(v, alo, ahi);
                    for (int q : As) if (q == z) return;
                    As.push_back(z);
                };
                auto addB = [&](long long v) {
                    int z = clampLL(v, blo, bhi);
                    for (int q : Bs) if (q == z) return;
                    Bs.push_back(z);
                };

                addA(((long long)orig.a + orig.c - w) / 2);
                addA(orig.a);
                addA((long long)orig.c - w);
                addA((long long)minX - w / 2);

                addB(((long long)orig.b + orig.d - h) / 2);
                addB(orig.b);
                addB((long long)orig.d - h);
                addB((long long)minY - h / 2);

                for (int a : As) {
                    for (int b : Bs) {
                        addRect(Rect{a, b, a + w, b + h});
                        if ((int)res.size() >= 4) return;
                    }
                }
            };

            bool inside = (w <= oW && h <= oH);
            placements(inside);
            if (!inside) placements(false);
        };

        auto ceilDiv2 = ceilDiv;

        trySize(oW, ceilDiv2(S, max(1, oW)));
        trySize(ceilDiv2(S, max(1, oH)), oH);

        {
            long double asp = max(0.05L, min(20.0L, (long double)oW / max(1, oH)));
            long long w = max(1LL, (long long)llroundl(sqrtl((long double)S * asp)));
            trySize(w, ceilDiv2(S, w));
        }

        {
            long long w = max(1LL, (long long)llroundl(sqrtl((long double)S)));
            trySize(w, ceilDiv2(S, w));
        }

        {
            long double asp = max(0.05L, min(20.0L, (long double)pW / max(1, pH)));
            long long w = max(1LL, (long long)llroundl(sqrtl((long double)S * asp)));
            trySize(w, ceilDiv2(S, w));
        }

        trySize(pW, ceilDiv2(S, max(1, pW)));
        trySize(ceilDiv2(S, max(1, pH)), pH);

        return res;
    }

    bool closureGroup(const State& st, vector<int> ids, int maxK, vector<int>& out) const {
        if (ids.empty()) return false;

        sort(ids.begin(), ids.end());
        ids.erase(unique(ids.begin(), ids.end()), ids.end());

        if ((int)ids.size() > maxK) return false;

        vector<char> in(n, 0);
        for (int id : ids) in[id] = 1;

        Rect box = groupBoundingBox(st, ids);

        bool changed = true;
        while (changed) {
            changed = false;

            for (int i = 0; i < n; i++) {
                if (in[i]) continue;

                if (overlapRect(st.rect[i], box)) {
                    in[i] = 1;
                    ids.push_back(i);

                    if ((int)ids.size() > maxK) return false;

                    const Rect& rc = st.rect[i];
                    box.a = min(box.a, rc.a);
                    box.b = min(box.b, rc.b);
                    box.c = max(box.c, rc.c);
                    box.d = max(box.d, rc.d);

                    changed = true;
                }
            }
        }

        sort(ids.begin(), ids.end());
        out = ids;
        return true;
    }

    bool validSubsetRects(const vector<Rect>& v, const vector<int>& ids) const {
        vector<char> in(n, 0);
        for (int id : ids) in[id] = 1;

        for (int id : ids) {
            const Rect& rc = v[id];
            if (!(0 <= rc.a && rc.a < rc.c && rc.c <= SZ)) return false;
            if (!(0 <= rc.b && rc.b < rc.d && rc.d <= SZ)) return false;
            if (!(rc.a <= x[id] && x[id] + 1 <= rc.c)) return false;
            if (!(rc.b <= y[id] && y[id] + 1 <= rc.d)) return false;
        }

        for (int i = 0; i < (int)ids.size(); i++) {
            for (int j = i + 1; j < (int)ids.size(); j++) {
                if (overlapRect(v[ids[i]], v[ids[j]])) return false;
            }
        }

        for (int id : ids) {
            for (int j = 0; j < n; j++) {
                if (in[j]) continue;
                if (overlapRect(v[id], v[j])) return false;
            }
        }

        return true;
    }

    void recomputeSubset(State& st, const vector<int>& ids) {
        for (int id : ids) {
            double ns = scoreOne(id, rectArea(st.rect[id]));
            st.total += ns - st.val[id];
            st.val[id] = ns;
        }
    }

    bool greedySubset(State& st, vector<int> ids, int passes, double stopTime) {
        bool globalAny = false;

        for (int pass = 0; pass < passes; pass++) {
            if (timer.elapsed() > stopTime) return globalAny;
            shuffleVector(ids);

            bool any = false;
            for (int id : ids) {
                for (int rep = 0; rep < 4; rep++) {
                    Move mv = bestMove(st, id);
                    if (mv.ok && mv.delta > 1e-12) {
                        applyMove(st, id, mv);
                        any = true;
                        globalAny = true;
                    } else {
                        break;
                    }
                }
            }

            if (!any) break;
        }

        return globalAny;
    }

    bool pairSubsetPass(State& st, vector<int> ids, int passes, double stopTime) {
        bool globalAny = false;

        for (int pass = 0; pass < passes; pass++) {
            if (timer.elapsed() > stopTime) return globalAny;
            shuffleVector(ids);

            bool any = false;
            int checks = 0;

            for (int ai = 0; ai < (int)ids.size(); ai++) {
                int i = ids[ai];
                for (int bj = ai + 1; bj < (int)ids.size(); bj++) {
                    if ((checks++ & 63) == 0 && timer.elapsed() > stopTime) return globalAny;

                    int j = ids[bj];
                    const Rect& A = st.rect[i];
                    const Rect& B = st.rect[j];

                    PairMove best;
                    best.delta = 0.0;

                    if (yOverlap(A, B)) {
                        PairMove mv;
                        if (A.c <= B.a) mv = bestPairVertical(st, i, j);
                        else if (B.c <= A.a) mv = bestPairVertical(st, j, i);
                        if (mv.ok && (!best.ok || mv.delta > best.delta)) best = mv;
                    }

                    if (xOverlap(A, B)) {
                        PairMove mv;
                        if (A.d <= B.b) mv = bestPairHorizontal(st, i, j);
                        else if (B.d <= A.b) mv = bestPairHorizontal(st, j, i);
                        if (mv.ok && (!best.ok || mv.delta > best.delta)) best = mv;
                    }

                    if (best.ok && best.delta > 1e-12) {
                        applyPair(st, best);
                        any = true;
                        globalAny = true;
                    }
                }
            }

            if (!any) break;
        }

        return globalAny;
    }

    bool tryRepackGroup(State& st, vector<int> ids, double stopTime, int trials) {
        if (timer.elapsed() > stopTime) return false;

        sort(ids.begin(), ids.end());
        ids.erase(unique(ids.begin(), ids.end()), ids.end());

        if ((int)ids.size() < 2 || (int)ids.size() > 8) return false;

        Rect box = groupBoundingBox(st, ids);
        if (!(box.a < box.c && box.b < box.d)) return false;
        if (!bboxClearForGroup(st, ids, box)) return false;

        State bestLocal = st;

        double beforeScore = 0.0;
        for (int id : ids) beforeScore += st.val[id];

        long long desire = desiredSum(ids);
        double mismatch = fabs((double)rectArea(box) - (double)desire) / max(1.0, (double)desire);
        double loss = (double)ids.size() - beforeScore;

        auto consider = [&](const vector<Rect>& fullRects) {
            if (timer.elapsed() > stopTime) return;
            if (!validSubsetRects(fullRects, ids)) return;

            State tr = st;
            for (int id : ids) tr.rect[id] = fullRects[id];
            recomputeSubset(tr, ids);

            greedySubset(tr, ids, 2, stopTime);
            pairSubsetPass(tr, ids, 1, stopTime);
            greedySubset(tr, ids, 1, stopTime);

            if (tr.total > bestLocal.total + 1e-12) bestLocal = std::move(tr);
        };

        if ((int)ids.size() <= 6 && timer.elapsed() + 0.004 < stopTime) {
            vector<Rect> rects = st.rect;
            buildRecBeam(ids, box, rects, stopTime);
            consider(rects);
        }

        {
            vector<Rect> rects = st.rect;
            buildRec(ids, box, rects, 0.0);
            consider(rects);
        }

        if ((loss > 0.015 || mismatch > 0.08) && timer.elapsed() + 0.005 < stopTime) {
            vector<Rect> altBoxes = alternativeRepackBoxes(st, ids, box);

            int used = 0;
            for (const Rect& bx : altBoxes) {
                if (used >= 3) break;
                if (timer.elapsed() + 0.003 > stopTime) break;

                {
                    vector<Rect> rects = st.rect;
                    if ((int)ids.size() <= 5 && timer.elapsed() + 0.004 < stopTime) {
                        buildRecBeam(ids, bx, rects, stopTime);
                    } else {
                        buildRec(ids, bx, rects, 0.0);
                    }
                    consider(rects);
                }

                if (trials >= 4 && (int)ids.size() <= 4 && timer.elapsed() + 0.004 < stopTime) {
                    vector<Rect> rects = st.rect;
                    double temp = 0.0005 * pow(500.0, rng.nextDouble());
                    buildRec(ids, bx, rects, temp);
                    consider(rects);
                }

                used++;
            }
        }

        if (trials >= 3 && timer.elapsed() < stopTime) {
            vector<Rect> rects = st.rect;
            for (int id : ids) rects[id] = {x[id], y[id], x[id] + 1, y[id] + 1};
            consider(rects);
        }

        for (int t = 0; t < trials && timer.elapsed() < stopTime; t++) {
            vector<Rect> rects = st.rect;
            double temp = 0.0005 * pow(500.0, rng.nextDouble());
            buildRec(ids, box, rects, temp);
            consider(rects);
        }

        if (bestLocal.total > st.total + 1e-12) {
            st = std::move(bestLocal);
            return true;
        }

        return false;
    }

    bool tryRepackGroupClosure(State& st, vector<int> ids, double stopTime, int trials, int maxK = 8) {
        vector<int> cl;
        if (!closureGroup(st, std::move(ids), maxK, cl)) return false;
        return tryRepackGroup(st, cl, stopTime, trials);
    }

    bool componentRepackPass(State& st, double stopTime, int maxGroups) {
        struct GC {
            double key;
            vector<int> ids;
        };

        vector<GC> groups;

        for (int orient = 0; orient < 2; orient++) {
            vector<LineComp> comps = buildLineComponents(st, orient);
            for (const LineComp& cp : comps) {
                vector<int> ids = cp.A;
                for (int id : cp.B) ids.push_back(id);

                vector<int> cl;
                if (!closureGroup(st, ids, 8, cl)) continue;

                int k = (int)cl.size();
                if (k < 2 || k > 8) continue;

                double loss = 0.0;
                for (int id : cl) loss += 1.0 - st.val[id];

                double key = loss + 0.0015 * k + 1e-5 * rng.nextDouble();
                groups.push_back({key, cl});
            }
        }

        sort(groups.begin(), groups.end(), [](const GC& p, const GC& q) {
            return p.key > q.key;
        });

        bool any = false;
        int tried = 0;

        for (auto& g : groups) {
            if (timer.elapsed() > stopTime) break;
            if (tried++ >= maxGroups) break;

            int k = (int)g.ids.size();
            int trials = (k <= 3 ? 5 : 3);

            if (tryRepackGroup(st, g.ids, stopTime, trials)) any = true;
        }

        return any;
    }

    int rectGap(const Rect& A, const Rect& B) const {
        int dx = 0;
        if (A.c < B.a) dx = B.a - A.c;
        else if (B.c < A.a) dx = A.a - B.c;

        int dy = 0;
        if (A.d < B.b) dy = B.b - A.d;
        else if (B.d < A.b) dy = A.b - B.d;

        int penalty = (dx > 0 && dy > 0) ? 10000 : 0;
        return dx + dy + penalty;
    }

    bool pairBlockRepackPass(State& st, double stopTime, int maxGroups) {
        struct PC {
            double key;
            int i, j;
        };

        vector<PC> cand;
        bool stop = false;

        for (int i = 0; i < n && !stop; i++) {
            for (int j = i + 1; j < n; j++) {
                if (((int)cand.size() & 511) == 0 && timer.elapsed() > stopTime) {
                    stop = true;
                    break;
                }

                int g = rectGap(st.rect[i], st.rect[j]);
                double loss = (1.0 - st.val[i]) + (1.0 - st.val[j]);

                if (g > 8000 && loss < 0.05) continue;

                double key = loss - 0.0000015 * g + 0.0001 / (1.0 + g) + 1e-5 * rng.nextDouble();
                cand.push_back({key, i, j});
            }
        }

        sort(cand.begin(), cand.end(), [](const PC& p, const PC& q) {
            return p.key > q.key;
        });

        bool any = false;
        int lim = min(maxGroups, (int)cand.size());

        for (int t = 0; t < lim; t++) {
            if (timer.elapsed() > stopTime) break;
            if (tryRepackGroupClosure(st, vector<int>{cand[t].i, cand[t].j}, stopTime, 3, 8)) any = true;
        }

        return any;
    }

    bool neighborClosureRepackPass(State& st, double stopTime, int maxBase) {
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int u, int v) {
            return st.val[u] < st.val[v];
        });

        bool any = false;
        int bases = min(maxBase, n);

        for (int bi = 0; bi < bases && timer.elapsed() < stopTime; bi++) {
            int base = ord[bi];

            vector<pair<int, int>> near;
            near.reserve(n - 1);
            for (int j = 0; j < n; j++) {
                if (j == base) continue;
                near.push_back({rectGap(st.rect[base], st.rect[j]), j});
            }
            sort(near.begin(), near.end());

            int lim = min(4, (int)near.size());
            for (int t = 0; t < lim && timer.elapsed() < stopTime; t++) {
                if (tryRepackGroupClosure(st, vector<int>{base, near[t].second}, stopTime, 3, 8)) any = true;
            }

            if (near.size() >= 2 && timer.elapsed() < stopTime) {
                vector<int> g{base, near[0].second, near[1].second};
                if (tryRepackGroupClosure(st, g, stopTime, 3, 8)) any = true;
            }

            if (near.size() >= 3 && timer.elapsed() < stopTime) {
                vector<int> g{base, near[0].second, near[1].second, near[2].second};
                if (tryRepackGroupClosure(st, g, stopTime, 2, 8)) any = true;
            }
        }

        return any;
    }

    bool randomBlockRepackAttempts(State& st, double stopTime, int attempts) {
        bool any = false;

        for (int at = 0; at < attempts && timer.elapsed() < stopTime; at++) {
            int base;
            if (rng.nextDouble() < 0.75) base = selectBad(st);
            else base = rng.nextInt(n);

            vector<int> group{base};
            vector<char> used(n, 0);
            used[base] = 1;

            int target = 2 + rng.nextInt(4);

            for (int step = 1; step < target && timer.elapsed() < stopTime; step++) {
                vector<pair<double, int>> cands;

                for (int j = 0; j < n; j++) {
                    if (used[j]) continue;

                    int g = 1e9;
                    for (int id : group) {
                        g = min(g, rectGap(st.rect[id], st.rect[j]));
                    }

                    double key = (double)g - 1800.0 * (1.0 - st.val[j]) + 20.0 * rng.nextDouble();
                    cands.push_back({key, j});
                }

                if (cands.empty()) break;
                sort(cands.begin(), cands.end());

                int lim = min(6, (int)cands.size());
                int pick = 0;
                if (rng.nextDouble() > 0.70) pick = rng.nextInt(lim);

                int add = cands[pick].second;
                used[add] = 1;
                group.push_back(add);

                if ((int)group.size() >= 2) {
                    if (tryRepackGroupClosure(st, group, stopTime, 3, 8)) {
                        any = true;
                        break;
                    }
                }
            }
        }

        return any;
    }

    void randomGreedyOps(State& st, int ops, double stopTime) {
        for (int op = 0; op < ops; op++) {
            if ((op & 255) == 0 && timer.elapsed() > stopTime) break;

            int i;
            if (rng.nextDouble() < 0.85) i = selectBad(st);
            else i = rng.nextInt(n);

            Move mv = bestMove(st, i);
            if (mv.ok && mv.delta > 1e-12) applyMove(st, i, mv);
        }
    }

    bool randomPairMove(State& st) {
        int i;
        if (rng.nextDouble() < 0.80) i = selectBad(st);
        else i = rng.nextInt(n);

        int dir = rng.nextInt(4);

        static constexpr int K = 8;
        int cand[K];
        int gap[K];
        int cnt = 0;

        auto addCand = [&](int j, int g) {
            if (cnt < K) {
                cand[cnt] = j;
                gap[cnt] = g;
                cnt++;
            } else {
                int worst = 0;
                for (int t = 1; t < K; t++) {
                    if (gap[t] > gap[worst]) worst = t;
                }
                if (g < gap[worst] || rng.nextDouble() < 0.02) {
                    cand[worst] = j;
                    gap[worst] = g;
                }
            }
        };

        const Rect& R = st.rect[i];

        for (int j = 0; j < n; j++) if (j != i) {
            const Rect& Q = st.rect[j];

            if (dir == 0) {
                if (Q.c <= R.a && yOverlap(Q, R)) addCand(j, R.a - Q.c);
            } else if (dir == 1) {
                if (R.c <= Q.a && yOverlap(R, Q)) addCand(j, Q.a - R.c);
            } else if (dir == 2) {
                if (Q.d <= R.b && xOverlap(Q, R)) addCand(j, R.b - Q.d);
            } else {
                if (R.d <= Q.b && xOverlap(R, Q)) addCand(j, Q.b - R.d);
            }
        }

        if (cnt == 0) return false;

        int pos = 0;
        for (int t = 1; t < cnt; t++) if (gap[t] < gap[pos]) pos = t;
        if (rng.nextDouble() < 0.35) pos = rng.nextInt(cnt);

        int j = cand[pos];

        PairMove mv;
        if (dir == 0) mv = bestPairVertical(st, j, i);
        else if (dir == 1) mv = bestPairVertical(st, i, j);
        else if (dir == 2) mv = bestPairHorizontal(st, j, i);
        else mv = bestPairHorizontal(st, i, j);

        if (mv.ok && mv.delta > 1e-12) {
            applyPair(st, mv);
            return true;
        }
        return false;
    }

    bool randomResize(State& st, double temp, double progress) {
        int i;
        if (rng.nextDouble() < 0.55) i = selectBad(st);
        else i = rng.nextInt(n);

        int dir = rng.nextInt(4);
        auto [lo, hi] = legalInterval(st, i, dir);
        if (lo > hi) return false;

        const Rect& rc = st.rect[i];
        int cur = getCoord(rc, dir);
        if (lo == hi) return false;

        int coord = cur;
        double q = rng.nextDouble();

        if (q < 0.25) {
            Move mv = bestEdgeDir(st, i, dir);
            if (!mv.ok) return false;
            coord = mv.coord;
        } else if (q < 0.80) {
            long long ar = rectArea(rc);
            bool under = ar < r[i];
            bool preferImprove = rng.nextDouble() < 0.72;

            int sign;
            if (dir == 0 || dir == 2) sign = under ? -1 : +1;
            else sign = under ? +1 : -1;

            if (!preferImprove) sign = -sign;

            int maxd = (sign < 0 ? cur - lo : hi - cur);
            if (maxd <= 0) {
                sign = -sign;
                maxd = (sign < 0 ? cur - lo : hi - cur);
            }

            if (maxd > 0) {
                int step = 1 + (int)(3000.0 * (1.0 - progress) * (1.0 - progress));
                int d = 1 + rng.nextInt(min(maxd, step));
                coord = cur + sign * d;
            } else {
                coord = lo + rng.nextInt(hi - lo + 1);
            }
        } else {
            coord = lo + rng.nextInt(hi - lo + 1);
        }

        if (coord == cur) return false;

        long long newArea = areaAfterCoord(rc, dir, coord);
        double ns = scoreOne(i, newArea);
        double delta = ns - st.val[i];

        if (delta >= 0.0 || rng.nextDouble() < exp(delta / max(temp, 1e-9))) {
            applyCoord(st, i, dir, coord, ns);
            return true;
        }
        return false;
    }

    bool randomShift(State& st, double progress) {
        int i;
        if (rng.nextDouble() < 0.5) i = selectBad(st);
        else i = rng.nextInt(n);

        int orient = rng.nextInt(2);
        Rect& ri = st.rect[i];

        int lo, hi;

        if (orient == 0) {
            lo = max(-ri.a, x[i] + 1 - ri.c);
            hi = min(SZ - ri.c, x[i] - ri.a);

            for (int j = 0; j < n; j++) if (j != i) {
                const Rect& rj = st.rect[j];
                if (!yOverlap(ri, rj)) continue;

                if (rj.c <= ri.a) lo = max(lo, rj.c - ri.a);
                else if (rj.a >= ri.c) hi = min(hi, rj.a - ri.c);
            }

            if (lo > hi || (lo == 0 && hi == 0)) return false;

            int d = 0;
            if (rng.nextDouble() < 0.70) {
                int step = 1 + (int)(1200.0 * (1.0 - progress));
                int L = max(lo, -step);
                int R = min(hi, step);
                if (L <= R) d = L + rng.nextInt(R - L + 1);
            } else {
                d = lo + rng.nextInt(hi - lo + 1);
            }

            if (d == 0) return false;
            ri.a += d;
            ri.c += d;
            return true;
        } else {
            lo = max(-ri.b, y[i] + 1 - ri.d);
            hi = min(SZ - ri.d, y[i] - ri.b);

            for (int j = 0; j < n; j++) if (j != i) {
                const Rect& rj = st.rect[j];
                if (!xOverlap(ri, rj)) continue;

                if (rj.d <= ri.b) lo = max(lo, rj.d - ri.b);
                else if (rj.b >= ri.d) hi = min(hi, rj.b - ri.d);
            }

            if (lo > hi || (lo == 0 && hi == 0)) return false;

            int d = 0;
            if (rng.nextDouble() < 0.70) {
                int step = 1 + (int)(1200.0 * (1.0 - progress));
                int L = max(lo, -step);
                int R = min(hi, step);
                if (L <= R) d = L + rng.nextInt(R - L + 1);
            } else {
                d = lo + rng.nextInt(hi - lo + 1);
            }

            if (d == 0) return false;
            ri.b += d;
            ri.d += d;
            return true;
        }
    }

    bool randomReshape(State& st, double progress) {
        for (int attempt = 0; attempt < 3; attempt++) {
            int i;
            if (rng.nextDouble() < 0.25) i = selectBad(st);
            else i = rng.nextInt(n);

            Rect oldRect = st.rect[i];
            double oldVal = st.val[i];
            double oldTotal = st.total;

            int dir1 = rng.nextInt(4);
            int dir2;
            if (dir1 < 2) dir2 = 2 + rng.nextInt(2);
            else dir2 = rng.nextInt(2);

            auto [lo, hi] = legalInterval(st, i, dir1);
            if (lo > hi) continue;

            int cur = getCoord(st.rect[i], dir1);
            if (lo == hi) continue;

            int coord = cur;
            double q = rng.nextDouble();

            if (q < 0.22) {
                coord = (rng.nextInt(2) ? lo : hi);
            } else {
                int step = 1 + (int)(2600.0 * (1.0 - progress) + 80.0);
                int L = max(lo, cur - step);
                int R = min(hi, cur + step);
                if (L > R) {
                    L = lo;
                    R = hi;
                }
                coord = L + rng.nextInt(R - L + 1);
            }

            if (coord == cur) {
                if (cur > lo) coord = cur - 1;
                else if (cur < hi) coord = cur + 1;
                else continue;
            }

            long long ar1 = areaAfterCoord(st.rect[i], dir1, coord);
            double ns1 = scoreOne(i, ar1);
            applyCoord(st, i, dir1, coord, ns1);

            Move mv = bestEdgeDir(st, i, dir2);
            if (mv.ok) applyMove(st, i, mv);

            bool changed =
                st.rect[i].a != oldRect.a || st.rect[i].b != oldRect.b ||
                st.rect[i].c != oldRect.c || st.rect[i].d != oldRect.d;

            if (changed && st.val[i] + 1e-12 >= oldVal) return true;

            st.rect[i] = oldRect;
            st.val[i] = oldVal;
            st.total = oldTotal;
        }

        return false;
    }

    State initialSolution() {
        constexpr double INIT_END = 0.80;

        State best;
        bool hasBest = false;

        auto consider = [&](const State& st) {
            if (!hasBest || st.total > best.total) {
                best = st;
                hasBest = true;
            }
        };

        {
            vector<Rect> rects = buildRecursive(0.0);
            State st = makeState(rects);
            greedyPasses(st, 5, INIT_END);
            pairGreedyPasses(st, 1, INIT_END);
            boundaryGreedyPasses(st, 1, INIT_END, false);
            randomGreedyOps(st, 5 * n, INIT_END);
            consider(st);
        }

        if (timer.elapsed() < INIT_END) {
            vector<Rect> rects = buildUnit();
            State st = makeState(rects);
            greedyPasses(st, 7, INIT_END);
            randomGreedyOps(st, 12 * n, INIT_END);
            pairGreedyPasses(st, 1, INIT_END);
            consider(st);
        }

        while (timer.elapsed() < INIT_END) {
            double temp = 0.00035 * pow(180.0, rng.nextDouble());
            vector<Rect> rects = buildRecursive(temp);
            State st = makeState(rects);

            greedyPasses(st, 2, INIT_END);
            randomGreedyOps(st, 3 * n, INIT_END);
            consider(st);
        }

        return best;
    }

    State improve(State bestState) {
        State cur = bestState;

        double preEnd = min(TIME_LIMIT - 0.72, timer.elapsed() + 0.38);
        boundaryGreedyPasses(cur, 2, preEnd, true);
        pairGreedyPasses(cur, 1, preEnd);
        greedyPasses(cur, 2, preEnd);
        boundaryGreedyPasses(cur, 1, preEnd, true);

        if (cur.total > bestState.total + 1e-12) bestState = cur;

        double saStart = timer.elapsed();
        double saEnd = TIME_LIMIT - 0.50;

        int iter = 0;
        double progress = 0.0;
        double temp = 0.05;

        while (true) {
            if ((iter & 1023) == 0) {
                double now = timer.elapsed();
                if (now > saEnd) break;

                progress = (now - saStart) / max(1e-9, saEnd - saStart);
                progress = min(1.0, max(0.0, progress));

                double T0 = 0.050;
                double T1 = 0.00001;
                temp = T0 * pow(T1 / T0, progress);
            }

            double q = rng.nextDouble();

            if (q < 0.05) {
                randomShift(cur, progress);
            } else if (q < 0.12) {
                randomReshape(cur, progress);
            } else if (q < 0.34) {
                int i;
                if (rng.nextDouble() < 0.82) i = selectBad(cur);
                else i = rng.nextInt(n);

                Move mv = bestMove(cur, i);
                if (mv.ok && mv.delta > 1e-12) applyMove(cur, i, mv);
            } else if (q < 0.62) {
                randomPairMove(cur);
            } else {
                randomResize(cur, temp, progress);
            }

            if (cur.total > bestState.total + 1e-12) bestState = cur;

            if ((iter & 65535) == 0) {
                double threshold = max(1.0, 0.015 * n);
                if (cur.total < bestState.total - threshold) cur = bestState;
            }

            iter++;
        }

        cur = bestState;

        int stagnant = 0;
        const double finalLoopEnd = TIME_LIMIT - FINAL_RESERVE;

        while (timer.elapsed() < finalLoopEnd) {
            bool imp = false;

            imp |= boundaryGreedyPasses(cur, 1, finalLoopEnd, true);
            if (cur.total > bestState.total + 1e-12) bestState = cur;

            imp |= pairGreedyPasses(cur, 1, finalLoopEnd);
            if (cur.total > bestState.total + 1e-12) bestState = cur;

            imp |= greedyPasses(cur, 1, finalLoopEnd);
            if (cur.total > bestState.total + 1e-12) bestState = cur;

            double rem = finalLoopEnd - timer.elapsed();
            if (rem > 0.18) {
                double blockStop = min(finalLoopEnd, timer.elapsed() + 0.13);

                imp |= componentRepackPass(cur, blockStop, 24);
                if (cur.total > bestState.total + 1e-12) bestState = cur;

                imp |= neighborClosureRepackPass(cur, blockStop, 7);
                if (cur.total > bestState.total + 1e-12) bestState = cur;

                imp |= pairBlockRepackPass(cur, blockStop, 20);
                if (cur.total > bestState.total + 1e-12) bestState = cur;

                imp |= randomBlockRepackAttempts(cur, blockStop, 7);
                if (cur.total > bestState.total + 1e-12) bestState = cur;
            }

            for (int k = 0; k < 240 && timer.elapsed() < finalLoopEnd; k++) {
                double q = rng.nextDouble();

                if (q < 0.28) {
                    if (randomPairMove(cur)) imp = true;
                } else if (q < 0.40) {
                    if (randomReshape(cur, 1.0)) imp = true;
                } else {
                    int i;
                    if (rng.nextDouble() < 0.90) i = selectBad(cur);
                    else i = rng.nextInt(n);

                    Move mv = bestMove(cur, i);
                    if (mv.ok && mv.delta > 1e-12) {
                        applyMove(cur, i, mv);
                        imp = true;
                    }
                }

                if (cur.total > bestState.total + 1e-12) bestState = cur;
            }

            if (!imp) {
                stagnant++;
                if (stagnant >= 4) break;
            } else {
                stagnant = 0;
            }
        }

        State polish = bestState;
        greedyPasses(polish, 2, TIME_LIMIT);
        pairGreedyPasses(polish, 1, TIME_LIMIT);
        boundaryGreedyPasses(polish, 1, TIME_LIMIT, false);
        greedyPasses(polish, 1, TIME_LIMIT);
        if (polish.total > bestState.total + 1e-12) bestState = std::move(polish);

        return bestState;
    }

    bool validateRects(const vector<Rect>& v) const {
        if ((int)v.size() != n) return false;

        for (int i = 0; i < n; i++) {
            const Rect& rc = v[i];
            if (!(0 <= rc.a && rc.a < rc.c && rc.c <= SZ)) return false;
            if (!(0 <= rc.b && rc.b < rc.d && rc.d <= SZ)) return false;
            if (!(rc.a <= x[i] && x[i] + 1 <= rc.c)) return false;
            if (!(rc.b <= y[i] && y[i] + 1 <= rc.d)) return false;
        }

        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (xOverlap(v[i], v[j]) && yOverlap(v[i], v[j])) return false;
            }
        }

        return true;
    }

public:
    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> n;
        x.resize(n);
        y.resize(n);
        r.resize(n);
        rd.resize(n);
        invR.resize(n);

        uint64_t seed = 1234567891234567ULL;
        for (int i = 0; i < n; i++) {
            cin >> x[i] >> y[i] >> r[i];
            rd[i] = (double)r[i];
            invR[i] = 1.0 / rd[i];

            uint64_t z = ((uint64_t)x[i] << 32) ^ ((uint64_t)y[i] << 16) ^ (uint64_t)r[i];
            seed ^= splitmix64_hash(z + seed);
        }
        rng = FastRNG(seed);

        timer.reset();

        State bestState = initialSolution();
        bestState = improve(bestState);

        if (!validateRects(bestState.rect)) {
            bestState = makeState(buildUnit());
        }

        for (int i = 0; i < n; i++) {
            const Rect& rc = bestState.rect[i];
            cout << rc.a << ' ' << rc.b << ' ' << rc.c << ' ' << rc.d << '\n';
        }
    }
};

int main() {
    Solver solver;
    solver.run();
    return 0;
}
