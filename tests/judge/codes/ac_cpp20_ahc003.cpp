#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 30;
static constexpr int LINE_VARS = 2 * N;

static constexpr int BINS = 4;
static constexpr int HBIN_VARS = N * BINS;
static constexpr int BIN_VARS = 2 * N * BINS;

static constexpr int SEG_VARS = 2 * LINE_VARS;

static constexpr int FINE_BINS = 6;
static constexpr int HFINE_VARS = N * FINE_BINS;
static constexpr int FINE_VARS = 2 * N * FINE_BINS;

static constexpr int H_EDGES = N * (N - 1);
static constexpr int EDGE_VARS = 2 * H_EDGES;

static constexpr int EXPLORE_TURNS = 100;

static inline double clampd(double x, double lo, double hi) {
    return min(hi, max(lo, x));
}

static inline int popcnt(uint32_t x) {
    return __builtin_popcount(x);
}

static inline uint32_t lowMask(int x) {
    if (x <= 0) return 0;
    return (1u << x) - 1u;
}

struct RidgeModel {
    int n;
    vector<double> ata;
    vector<double> atb;

    RidgeModel(int n_ = 0) : n(n_), ata(n_ * n_, 0.0), atb(n_, 0.0) {}

    void addObservation(const vector<pair<int, int>>& counts, int steps, double result) {
        if (steps <= 0) return;

        vector<pair<int, double>> f;
        f.reserve(counts.size());

        double inv_steps = 1.0 / steps;
        for (auto [idx, cnt] : counts) {
            if (cnt > 0) f.push_back({idx, cnt * inv_steps});
        }

        double target = result * inv_steps;

        for (auto [ia, va] : f) {
            double* row = &ata[ia * n];
            atb[ia] += va * target;
            for (auto [ib, vb] : f) {
                row[ib] += va * vb;
            }
        }
    }

    void solve(const vector<double>& prior, double lambda, vector<double>& out) const {
        vector<double> a = ata;
        vector<double> b(n);

        for (int i = 0; i < n; i++) {
            a[i * n + i] += lambda;
            b[i] = atb[i] + lambda * prior[i];
        }

        for (int i = 0; i < n; i++) {
            for (int j = 0; j <= i; j++) {
                double sum = a[i * n + j];
                for (int k = 0; k < j; k++) {
                    sum -= a[i * n + k] * a[j * n + k];
                }

                if (i == j) {
                    if (sum < 1e-9) sum = 1e-9;
                    a[i * n + j] = sqrt(sum);
                } else {
                    a[i * n + j] = sum / a[j * n + j];
                }
            }
        }

        vector<double> y(n);
        for (int i = 0; i < n; i++) {
            double sum = b[i];
            for (int k = 0; k < i; k++) sum -= a[i * n + k] * y[k];
            y[i] = sum / a[i * n + i];
        }

        out.assign(n, 0.0);
        for (int i = n - 1; i >= 0; i--) {
            double sum = y[i];
            for (int k = i + 1; k < n; k++) sum -= a[k * n + i] * out[k];
            out[i] = sum / a[i * n + i];
            out[i] = clampd(out[i], 1000.0, 9000.0);
        }
    }
};

struct Observation {
    int result = 0;
    int steps = 0;
    array<uint32_t, LINE_VARS> mask;

    Observation() {
        mask.fill(0);
    }
};

struct Solver {
    RidgeModel lineModel;
    RidgeModel binModel;
    RidgeModel fineModel;

    vector<double> lineEst;
    vector<double> binDelta;
    vector<double> segEst;
    vector<double> fineDelta;
    vector<double> edgeDelta;

    array<int, LINE_VARS> lineSeen{};
    array<int, BIN_VARS> binSeen{};
    array<int, FINE_VARS> fineSeen{};
    array<int, EDGE_VARS> edgeSeen{};
    array<int, EDGE_VARS> edgeLearnSeen{};

    array<int, LINE_VARS> split{};
    array<int, SEG_VARS> segSupport{};

    vector<Observation> observations;

    mt19937 rng;
    int turn = 0;

    double segGlobalConf = 0.0;

    bool fineReady = false;
    double fineValidationConf = 1.0;
    deque<pair<double, double>> fineValidationWindow;

    double edgeValidationConf = 1.0;
    deque<pair<double, double>> edgeValidationWindow;

    Solver()
        : lineModel(LINE_VARS),
          binModel(BIN_VARS),
          fineModel(FINE_VARS),
          lineEst(LINE_VARS, 5000.0),
          binDelta(BIN_VARS, 0.0),
          segEst(SEG_VARS, 5000.0),
          fineDelta(FINE_VARS, 0.0),
          edgeDelta(EDGE_VARS, 0.0),
          rng(1234567) {
        lineSeen.fill(0);
        binSeen.fill(0);
        fineSeen.fill(0);
        edgeSeen.fill(0);
        edgeLearnSeen.fill(0);
        split.fill(14);
        segSupport.fill(0);
    }

    static int hVar(int i, int j) {
        int q = j * BINS / (N - 1);
        return i * BINS + q;
    }

    static int vVar(int i, int j) {
        int q = i * BINS / (N - 1);
        return HBIN_VARS + j * BINS + q;
    }

    static int fineHVar(int i, int j) {
        int q = j * FINE_BINS / (N - 1);
        return i * FINE_BINS + q;
    }

    static int fineVVar(int i, int j) {
        int q = i * FINE_BINS / (N - 1);
        return HFINE_VARS + j * FINE_BINS + q;
    }

    static int hEdge(int i, int j) {
        return i * (N - 1) + j;
    }

    static int vEdge(int i, int j) {
        return H_EDGES + i * N + j;
    }

    double globalWeight() const {
        return clampd(turn / 300.0, 0.0, 1.0);
    }

    double binWeight() const {
        return clampd((turn - 80) / 420.0, 0.0, 1.0);
    }

    double segmentWeight() const {
        double t = clampd((turn - 110) / 390.0, 0.0, 1.0);
        return t * segGlobalConf;
    }

    double fineWeight() const {
        double t = clampd((turn - 300) / 500.0, 0.0, 1.0);
        return 0.40 * t * fineValidationConf;
    }

    double edgeWeight() const {
        double t = clampd((turn - 520) / 400.0, 0.0, 1.0);
        return 0.15 * t * edgeValidationConf;
    }

    double rawStructH(int i, int j) const {
        int line = i;
        int bv = hVar(i, j);

        double bw = binWeight();
        double base = lineEst[line] + bw * binDelta[bv];

        int side = (j < split[line] ? 0 : 1);
        int sv = 2 * line + side;

        double cov = clampd(segSupport[sv] / 25.0, 0.0, 1.0);
        double sw = 0.90 * segmentWeight() * cov;

        double raw = (1.0 - sw) * base + sw * segEst[sv];
        return clampd(raw, 1000.0, 9000.0);
    }

    double rawStructV(int i, int j) const {
        int line = N + j;
        int bv = vVar(i, j);

        double bw = binWeight();
        double base = lineEst[line] + bw * binDelta[bv];

        int side = (i < split[line] ? 0 : 1);
        int sv = 2 * line + side;

        double cov = clampd(segSupport[sv] / 25.0, 0.0, 1.0);
        double sw = 0.90 * segmentWeight() * cov;

        double raw = (1.0 - sw) * base + sw * segEst[sv];
        return clampd(raw, 1000.0, 9000.0);
    }

    double rawNoEdgeH(int i, int j) const {
        double raw = rawStructH(i, j);

        if (fineReady) {
            int fv = fineHVar(i, j);
            double seenConf = clampd((fineSeen[fv] - 3.0) / 12.0, 0.0, 1.0);
            double fw = fineWeight() * seenConf;
            raw = clampd(raw + fw * fineDelta[fv], 1000.0, 9000.0);
        }

        return raw;
    }

    double rawNoEdgeV(int i, int j) const {
        double raw = rawStructV(i, j);

        if (fineReady) {
            int fv = fineVVar(i, j);
            double seenConf = clampd((fineSeen[fv] - 3.0) / 12.0, 0.0, 1.0);
            double fw = fineWeight() * seenConf;
            raw = clampd(raw + fw * fineDelta[fv], 1000.0, 9000.0);
        }

        return raw;
    }

    double hCostNoFine(int i, int j) const {
        double raw = rawStructH(i, j);
        double g = globalWeight();
        return clampd(5000.0 + g * (raw - 5000.0), 1000.0, 9000.0);
    }

    double vCostNoFine(int i, int j) const {
        double raw = rawStructV(i, j);
        double g = globalWeight();
        return clampd(5000.0 + g * (raw - 5000.0), 1000.0, 9000.0);
    }

    double hCostNoEdge(int i, int j) const {
        double raw = rawNoEdgeH(i, j);
        double g = globalWeight();
        return clampd(5000.0 + g * (raw - 5000.0), 1000.0, 9000.0);
    }

    double vCostNoEdge(int i, int j) const {
        double raw = rawNoEdgeV(i, j);
        double g = globalWeight();
        return clampd(5000.0 + g * (raw - 5000.0), 1000.0, 9000.0);
    }

    double hCost(int i, int j) const {
        double raw = rawNoEdgeH(i, j);

        int e = hEdge(i, j);
        double seenConf = clampd((edgeLearnSeen[e] - 2.0) / 8.0, 0.0, 1.0);
        double ew = edgeWeight() * seenConf;
        raw = clampd(raw + ew * edgeDelta[e], 1000.0, 9000.0);

        double g = globalWeight();
        return clampd(5000.0 + g * (raw - 5000.0), 1000.0, 9000.0);
    }

    double vCost(int i, int j) const {
        double raw = rawNoEdgeV(i, j);

        int e = vEdge(i, j);
        double seenConf = clampd((edgeLearnSeen[e] - 2.0) / 8.0, 0.0, 1.0);
        double ew = edgeWeight() * seenConf;
        raw = clampd(raw + ew * edgeDelta[e], 1000.0, 9000.0);

        double g = globalWeight();
        return clampd(5000.0 + g * (raw - 5000.0), 1000.0, 9000.0);
    }

    static void appendVertical(string& s, int from, int to) {
        if (to > from) s.append(to - from, 'D');
        else s.append(from - to, 'U');
    }

    static void appendHorizontal(string& s, int from, int to) {
        if (to > from) s.append(to - from, 'R');
        else s.append(from - to, 'L');
    }

    string makeDirect(int si, int sj, int ti, int tj, bool horizontalFirst) const {
        string s;
        if (horizontalFirst) {
            appendHorizontal(s, sj, tj);
            appendVertical(s, si, ti);
        } else {
            appendVertical(s, si, ti);
            appendHorizontal(s, sj, tj);
        }
        return s;
    }

    string makeViaRow(int si, int sj, int ti, int tj, int r) const {
        string s;
        appendVertical(s, si, r);
        appendHorizontal(s, sj, tj);
        appendVertical(s, r, ti);
        return s;
    }

    string makeViaCol(int si, int sj, int ti, int tj, int c) const {
        string s;
        appendHorizontal(s, sj, c);
        appendVertical(s, si, ti);
        appendHorizontal(s, c, tj);
        return s;
    }

    bool validatePath(int si, int sj, int ti, int tj, const string& path) const {
        array<char, N * N> vis{};
        int r = si, c = sj;
        vis[r * N + c] = 1;

        for (char ch : path) {
            if (ch == 'U') r--;
            else if (ch == 'D') r++;
            else if (ch == 'L') c--;
            else if (ch == 'R') c++;
            else return false;

            if (r < 0 || r >= N || c < 0 || c >= N) return false;

            int id = r * N + c;
            if (vis[id]) return false;
            vis[id] = 1;
        }

        return r == ti && c == tj;
    }

    double estimatePathCost(int si, int sj, const string& path) const {
        int r = si, c = sj;
        double total = 0.0;

        for (char ch : path) {
            if (ch == 'R') {
                total += hCost(r, c);
                c++;
            } else if (ch == 'L') {
                total += hCost(r, c - 1);
                c--;
            } else if (ch == 'D') {
                total += vCost(r, c);
                r++;
            } else if (ch == 'U') {
                total += vCost(r - 1, c);
                r--;
            }
        }

        return total;
    }

    double estimatePathCostNoEdge(int si, int sj, const string& path) const {
        int r = si, c = sj;
        double total = 0.0;

        for (char ch : path) {
            if (ch == 'R') {
                total += hCostNoEdge(r, c);
                c++;
            } else if (ch == 'L') {
                total += hCostNoEdge(r, c - 1);
                c--;
            } else if (ch == 'D') {
                total += vCostNoEdge(r, c);
                r++;
            } else if (ch == 'U') {
                total += vCostNoEdge(r - 1, c);
                r--;
            }
        }

        return total;
    }

    double estimatePathCostNoFine(int si, int sj, const string& path) const {
        int r = si, c = sj;
        double total = 0.0;

        for (char ch : path) {
            if (ch == 'R') {
                total += hCostNoFine(r, c);
                c++;
            } else if (ch == 'L') {
                total += hCostNoFine(r, c - 1);
                c--;
            } else if (ch == 'D') {
                total += vCostNoFine(r, c);
                r++;
            } else if (ch == 'U') {
                total += vCostNoFine(r - 1, c);
                r--;
            }
        }

        return total;
    }

    double explorationSeenScore(int si, int sj, const string& path) const {
        array<char, LINE_VARS> lu{};
        array<char, BIN_VARS> bu{};

        int r = si, c = sj;

        for (char ch : path) {
            int line = -1, bv = -1;

            if (ch == 'R') {
                line = r;
                bv = hVar(r, c);
                c++;
            } else if (ch == 'L') {
                c--;
                line = r;
                bv = hVar(r, c);
            } else if (ch == 'D') {
                line = N + c;
                bv = vVar(r, c);
                r++;
            } else if (ch == 'U') {
                r--;
                line = N + c;
                bv = vVar(r, c);
            }

            if (line >= 0) lu[line] = 1;
            if (bv >= 0) bu[bv] = 1;
        }

        double score = 0.0;
        for (int i = 0; i < LINE_VARS; i++) {
            if (lu[i]) score += lineSeen[i];
        }
        for (int i = 0; i < BIN_VARS; i++) {
            if (bu[i]) score += 0.35 * binSeen[i];
        }

        return score;
    }

    string chooseBestDirect(int si, int sj, int ti, int tj) const {
        string p1 = makeDirect(si, sj, ti, tj, true);
        string p2 = makeDirect(si, sj, ti, tj, false);

        double c1 = estimatePathCost(si, sj, p1);
        double c2 = estimatePathCost(si, sj, p2);

        return (c1 <= c2 ? p1 : p2);
    }

    string chooseExplorationPath(int si, int sj, int ti, int tj) {
        string p1 = makeDirect(si, sj, ti, tj, true);
        string p2 = makeDirect(si, sj, ti, tj, false);

        double c1 = estimatePathCost(si, sj, p1);
        double c2 = estimatePathCost(si, sj, p2);

        double s1 = explorationSeenScore(si, sj, p1);
        double s2 = explorationSeenScore(si, sj, p2);

        double bonus = 1500.0 * (1.0 - turn / double(EXPLORE_TURNS));

        double v1 = c1 + bonus * s1;
        double v2 = c2 + bonus * s2;

        if (abs(v1 - v2) < 1e-9) {
            return (rng() & 1) ? p1 : p2;
        }
        return (v1 <= v2 ? p1 : p2);
    }

    string bestCorridorPath(int si, int sj, int ti, int tj) const {
        string best;
        double bestCost = 1e100;

        auto consider = [&](const string& p) {
            if (!validatePath(si, sj, ti, tj, p)) return;

            double c = estimatePathCost(si, sj, p);
            if (c < bestCost - 1e-9 ||
                (abs(c - bestCost) < 1e-9 && (best.empty() || p.size() < best.size()))) {
                bestCost = c;
                best = p;
            }
        };

        consider(makeDirect(si, sj, ti, tj, true));
        consider(makeDirect(si, sj, ti, tj, false));

        for (int r = 0; r < N; r++) {
            consider(makeViaRow(si, sj, ti, tj, r));
        }
        for (int c = 0; c < N; c++) {
            consider(makeViaCol(si, sj, ti, tj, c));
        }

        if (best.empty()) best = chooseBestDirect(si, sj, ti, tj);
        return best;
    }

    string dijkstra(int si, int sj, int ti, int tj, bool useFine, bool useEdge) const {
        int S = si * N + sj;
        int T = ti * N + tj;

        const double INF = 1e100;
        vector<double> dist(N * N, INF);
        vector<int> pre(N * N, -1);
        vector<char> pmove(N * N, 0);

        using P = pair<double, int>;
        priority_queue<P, vector<P>, greater<P>> pq;

        dist[S] = 0.0;
        pre[S] = S;
        pq.push({0.0, S});

        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();

            if (d > dist[u] + 1e-9) continue;
            if (u == T) break;

            int r = u / N;
            int c = u % N;

            int dirs[4];
            bool used[4] = {};
            int m = 0;

            auto addDir = [&](int x) {
                if (!used[x]) {
                    used[x] = true;
                    dirs[m++] = x;
                }
            };

            if (ti < r) addDir(0);
            if (ti > r) addDir(1);
            if (tj < c) addDir(2);
            if (tj > c) addDir(3);
            for (int x = 0; x < 4; x++) addDir(x);

            for (int idx = 0; idx < 4; idx++) {
                int dir = dirs[idx];

                int nr = r, nc = c;
                char mv = '?';
                double w = 0.0;

                if (dir == 0) {
                    if (r == 0) continue;
                    nr = r - 1;
                    mv = 'U';
                    if (!useFine) w = vCostNoFine(r - 1, c);
                    else if (!useEdge) w = vCostNoEdge(r - 1, c);
                    else w = vCost(r - 1, c);
                } else if (dir == 1) {
                    if (r == N - 1) continue;
                    nr = r + 1;
                    mv = 'D';
                    if (!useFine) w = vCostNoFine(r, c);
                    else if (!useEdge) w = vCostNoEdge(r, c);
                    else w = vCost(r, c);
                } else if (dir == 2) {
                    if (c == 0) continue;
                    nc = c - 1;
                    mv = 'L';
                    if (!useFine) w = hCostNoFine(r, c - 1);
                    else if (!useEdge) w = hCostNoEdge(r, c - 1);
                    else w = hCost(r, c - 1);
                } else {
                    if (c == N - 1) continue;
                    nc = c + 1;
                    mv = 'R';
                    if (!useFine) w = hCostNoFine(r, c);
                    else if (!useEdge) w = hCostNoEdge(r, c);
                    else w = hCost(r, c);
                }

                int v = nr * N + nc;
                double nd = d + w;

                if (nd + 1e-9 < dist[v]) {
                    dist[v] = nd;
                    pre[v] = u;
                    pmove[v] = mv;
                    pq.push({nd, v});
                }
            }
        }

        if (pre[T] == -1) return "";

        string path;
        int cur = T;
        while (cur != S) {
            path.push_back(pmove[cur]);
            cur = pre[cur];
            if (cur < 0) return "";
        }

        reverse(path.begin(), path.end());
        return path;
    }

    string choosePath(int si, int sj, int ti, int tj) {
        if (turn < EXPLORE_TURNS) {
            return chooseExplorationPath(si, sj, ti, tj);
        }

        string safe = bestCorridorPath(si, sj, ti, tj);
        string p = dijkstra(si, sj, ti, tj, true, true);

        if (p.empty() || !validatePath(si, sj, ti, tj, p)) {
            return safe;
        }

        if (turn >= 620 && edgeWeight() > 1e-9) {
            string pne = dijkstra(si, sj, ti, tj, true, false);

            if (!pne.empty() && validatePath(si, sj, ti, tj, pne)) {
                double cfP = estimatePathCost(si, sj, p);
                double ceP = estimatePathCostNoEdge(si, sj, p);
                double cfN = estimatePathCost(si, sj, pne);
                double ceN = estimatePathCostNoEdge(si, sj, pne);

                double trustEdge = clampd(0.65 + 0.25 * edgeValidationConf, 0.70, 0.90);
                double scoreP = trustEdge * cfP + (1.0 - trustEdge) * ceP;
                double scoreN = trustEdge * cfN + (1.0 - trustEdge) * ceN;

                if (scoreN < scoreP * 0.998 && (int)pne.size() <= (int)p.size() + 35) {
                    p = pne;
                }
            }
        }

        if (fineReady && turn >= 380) {
            string pn = dijkstra(si, sj, ti, tj, false, false);

            if (!pn.empty() && validatePath(si, sj, ti, tj, pn)) {
                double cfP = estimatePathCost(si, sj, p);
                double csP = estimatePathCostNoFine(si, sj, p);
                double cfN = estimatePathCost(si, sj, pn);
                double csN = estimatePathCostNoFine(si, sj, pn);

                double trustFine = clampd(0.70 + 0.22 * fineValidationConf, 0.80, 0.92);

                double scoreP = trustFine * cfP + (1.0 - trustFine) * csP;
                double scoreN = trustFine * cfN + (1.0 - trustFine) * csN;

                if (scoreN < scoreP * 0.997 && (int)pn.size() <= (int)p.size() + 40) {
                    p = pn;
                }
            }
        }

        int manhattan = abs(si - ti) + abs(sj - tj);

        int extraLimit;
        if (turn < 200) extraLimit = 12;
        else if (turn < 350) extraLimit = 25;
        else if (turn < 500) extraLimit = 45;
        else if (turn < 700) extraLimit = 65;
        else extraLimit = 80 + int(20.0 * segGlobalConf);

        double cd = estimatePathCost(si, sj, p);
        double cs = estimatePathCost(si, sj, safe);

        int extra = int(p.size()) - manhattan;

        if (extra > extraLimit) {
            if ((int)p.size() > manhattan + 130) return safe;
            if (cd > cs * 0.82) return safe;
        }

        int lenDiff = int(p.size()) - int(safe.size());
        if (lenDiff > 30) {
            double requiredRatio = 1.0 - min(0.08, 0.001 * lenDiff);
            if (cd > cs * requiredRatio) return safe;
        }

        return p;
    }

    void updateFineValidation(int si, int sj, const string& path, int result) {
        if (!fineReady || turn < 350 || result <= 0) return;

        double ps = estimatePathCostNoFine(si, sj, path);
        double pf = estimatePathCostNoEdge(si, sj, path);

        double denom = max(1.0, double(result));
        double es = (ps - result) / denom;
        double ef = (pf - result) / denom;

        double es2 = min(0.25, es * es);
        double ef2 = min(0.25, ef * ef);

        fineValidationWindow.push_back({es2, ef2});
        if ((int)fineValidationWindow.size() > 220) fineValidationWindow.pop_front();

        if ((int)fineValidationWindow.size() < 120) {
            fineValidationConf = 1.0;
            return;
        }

        double ss = 0.0;
        double sf = 0.0;
        for (auto [a, b] : fineValidationWindow) {
            ss += a;
            sf += b;
        }

        ss /= fineValidationWindow.size();
        sf /= fineValidationWindow.size();

        double worse = sf - ss;

        if (worse <= 0.0008) {
            fineValidationConf = 1.0;
        } else {
            fineValidationConf = clampd(1.0 - (worse - 0.0008) / 0.0030 * 0.45, 0.55, 1.0);
        }
    }

    void updateEdgeValidation(int si, int sj, const string& path, int result) {
        if (turn < 600 || result <= 0) return;

        double ps = estimatePathCostNoEdge(si, sj, path);
        double pe = estimatePathCost(si, sj, path);

        double denom = max(1.0, double(result));
        double es = (ps - result) / denom;
        double ee = (pe - result) / denom;

        double es2 = min(0.25, es * es);
        double ee2 = min(0.25, ee * ee);

        edgeValidationWindow.push_back({es2, ee2});
        if ((int)edgeValidationWindow.size() > 180) edgeValidationWindow.pop_front();

        if ((int)edgeValidationWindow.size() < 90) {
            edgeValidationConf = 1.0;
            return;
        }

        double ss = 0.0;
        double se = 0.0;
        for (auto [a, b] : edgeValidationWindow) {
            ss += a;
            se += b;
        }

        ss /= edgeValidationWindow.size();
        se /= edgeValidationWindow.size();

        double worse = se - ss;

        if (worse <= 0.0006) {
            edgeValidationConf = 1.0;
        } else {
            edgeValidationConf = clampd(1.0 - (worse - 0.0006) / 0.0025 * 0.50, 0.50, 1.0);
        }
    }

    void updateEdgeResidual(int si, int sj, const string& path, int result, const vector<int>& edgeList) {
        if (turn < 300 || result <= 0 || path.empty()) return;

        double pred = estimatePathCostNoEdge(si, sj, path);
        double residual = result - pred;

        double per = residual / double(path.size());
        per = clampd(per, -2200.0, 2200.0);

        double prog = clampd((turn - 300) / 500.0, 0.0, 1.0);
        double lr = 0.10 + 0.08 * prog;

        for (int e : edgeList) {
            edgeLearnSeen[e]++;
            int c = max(1, edgeLearnSeen[e]);
            double rate = lr / sqrt(1.0 + 0.04 * c);
            edgeDelta[e] += rate * per;
            edgeDelta[e] = clampd(edgeDelta[e], -1800.0, 1800.0);
        }
    }

    void updateModelsWithResult(int si, int sj, const string& path, int result) {
        updateFineValidation(si, sj, path, result);
        updateEdgeValidation(si, sj, path, result);

        Observation ob;
        ob.result = result;
        ob.steps = (int)path.size();

        array<int, LINE_VARS> lineCnt{};
        array<int, BIN_VARS> binCnt{};
        array<int, FINE_VARS> fineCnt{};

        vector<int> edgeList;
        edgeList.reserve(path.size());

        int r = si;
        int c = sj;

        for (char ch : path) {
            if (ch == 'R') {
                int line = r;
                int pos = c;
                int bv = hVar(r, c);
                int fv = fineHVar(r, c);
                int ev = hEdge(r, c);

                lineCnt[line]++;
                binCnt[bv]++;
                fineCnt[fv]++;
                edgeSeen[ev]++;
                edgeList.push_back(ev);

                ob.mask[line] |= (1u << pos);
                c++;
            } else if (ch == 'L') {
                c--;

                int line = r;
                int pos = c;
                int bv = hVar(r, c);
                int fv = fineHVar(r, c);
                int ev = hEdge(r, c);

                lineCnt[line]++;
                binCnt[bv]++;
                fineCnt[fv]++;
                edgeSeen[ev]++;
                edgeList.push_back(ev);

                ob.mask[line] |= (1u << pos);
            } else if (ch == 'D') {
                int line = N + c;
                int pos = r;
                int bv = vVar(r, c);
                int fv = fineVVar(r, c);
                int ev = vEdge(r, c);

                lineCnt[line]++;
                binCnt[bv]++;
                fineCnt[fv]++;
                edgeSeen[ev]++;
                edgeList.push_back(ev);

                ob.mask[line] |= (1u << pos);
                r++;
            } else if (ch == 'U') {
                r--;

                int line = N + c;
                int pos = r;
                int bv = vVar(r, c);
                int fv = fineVVar(r, c);
                int ev = vEdge(r, c);

                lineCnt[line]++;
                binCnt[bv]++;
                fineCnt[fv]++;
                edgeSeen[ev]++;
                edgeList.push_back(ev);

                ob.mask[line] |= (1u << pos);
            }
        }

        vector<pair<int, int>> lf;
        vector<pair<int, int>> bf;
        vector<pair<int, int>> ff;

        for (int i = 0; i < LINE_VARS; i++) {
            if (lineCnt[i] > 0) {
                lf.push_back({i, lineCnt[i]});
                lineSeen[i]++;
            }
        }

        for (int i = 0; i < BIN_VARS; i++) {
            if (binCnt[i] > 0) {
                bf.push_back({i, binCnt[i]});
                binSeen[i]++;
            }
        }

        for (int i = 0; i < FINE_VARS; i++) {
            if (fineCnt[i] > 0) {
                ff.push_back({i, fineCnt[i]});
                fineSeen[i]++;
            }
        }

        lineModel.addObservation(lf, ob.steps, result);
        binModel.addObservation(bf, ob.steps, result);
        fineModel.addObservation(ff, ob.steps, result);

        observations.push_back(ob);

        updateEdgeResidual(si, sj, path, result, edgeList);
    }

    double predictObsSegment(const Observation& ob) const {
        double sum = 0.0;

        for (int line = 0; line < LINE_VARS; line++) {
            uint32_t m = ob.mask[line];
            if (!m) continue;

            int total = popcnt(m);
            int x = split[line];
            int cl = popcnt(m & lowMask(x));
            int cr = total - cl;

            sum += segEst[2 * line] * cl;
            sum += segEst[2 * line + 1] * cr;
        }

        return sum / ob.steps;
    }

    void seedSplitsFromBin() {
        static const int bounds[3] = {8, 15, 22};

        for (int line = 0; line < LINE_VARS; line++) {
            if (lineSeen[line] < 2) continue;

            double val[BINS];

            for (int q = 0; q < BINS; q++) {
                int idx;
                if (line < N) idx = line * BINS + q;
                else idx = HBIN_VARS + (line - N) * BINS + q;

                val[q] = lineEst[line] + binDelta[idx];
            }

            double bestDiff = 0.0;
            int bestBoundary = split[line];

            for (int q = 0; q + 1 < BINS; q++) {
                double d = abs(val[q + 1] - val[q]);
                if (d > bestDiff) {
                    bestDiff = d;
                    bestBoundary = bounds[q];
                }
            }

            double segDiff = abs(segEst[2 * line] - segEst[2 * line + 1]);

            if (bestDiff > 450.0 &&
                (segDiff < 700.0 || observations.size() < 180)) {
                split[line] = bestBoundary;
            }
        }
    }

    void solveSegmentRidge(double lambda) {
        RidgeModel model(SEG_VARS);
        segSupport.fill(0);

        for (const auto& ob : observations) {
            vector<pair<int, int>> f;
            f.reserve(16);

            for (int line = 0; line < LINE_VARS; line++) {
                uint32_t m = ob.mask[line];
                if (!m) continue;

                int total = popcnt(m);
                int x = split[line];
                int cl = popcnt(m & lowMask(x));
                int cr = total - cl;

                if (cl > 0) {
                    f.push_back({2 * line, cl});
                    segSupport[2 * line] += cl;
                }
                if (cr > 0) {
                    f.push_back({2 * line + 1, cr});
                    segSupport[2 * line + 1] += cr;
                }
            }

            model.addObservation(f, ob.steps, ob.result);
        }

        vector<double> prior(SEG_VARS);
        for (int i = 0; i < SEG_VARS; i++) {
            prior[i] = lineEst[i / 2];
        }

        model.solve(prior, lambda, segEst);
    }

    void refineSplits() {
        int m = (int)observations.size();
        if (m < 60) return;

        vector<double> pred(m);
        vector<double> target(m);

        for (int i = 0; i < m; i++) {
            pred[i] = predictObsSegment(observations[i]);
            target[i] = observations[i].result / double(observations[i].steps);
        }

        for (int line = 0; line < LINE_VARS; line++) {
            double v0 = segEst[2 * line];
            double v1 = segEst[2 * line + 1];

            if (abs(v0 - v1) < 250.0) continue;

            int active = 0;
            for (const auto& ob : observations) {
                if (ob.mask[line]) active++;
            }

            if (active < 8) continue;

            int oldX = split[line];
            uint32_t oldMask = lowMask(oldX);

            double bestSSE = 1e100;
            double oldSSE = 1e100;
            int bestX = oldX;

            for (int x = 1; x <= 28; x++) {
                uint32_t xm = lowMask(x);
                double sse = 0.0;

                for (int idx = 0; idx < m; idx++) {
                    const auto& ob = observations[idx];
                    uint32_t mask = ob.mask[line];
                    if (!mask) continue;

                    int total = popcnt(mask);

                    int oldLeft = popcnt(mask & oldMask);
                    double oldContr = (v0 * oldLeft + v1 * (total - oldLeft)) / ob.steps;

                    double baseResidualTarget = target[idx] - pred[idx] + oldContr;

                    int newLeft = popcnt(mask & xm);
                    double newContr = (v0 * newLeft + v1 * (total - newLeft)) / ob.steps;

                    double res = baseResidualTarget - newContr;
                    sse += res * res;
                }

                if (x == oldX) oldSSE = sse;

                if (sse < bestSSE) {
                    bestSSE = sse;
                    bestX = x;
                }
            }

            double threshold = max(20000.0, 0.001 * oldSSE);

            if (bestX != oldX && bestSSE + threshold < oldSSE) {
                uint32_t newMask = lowMask(bestX);

                for (int idx = 0; idx < m; idx++) {
                    const auto& ob = observations[idx];
                    uint32_t mask = ob.mask[line];
                    if (!mask) continue;

                    int total = popcnt(mask);

                    int oldLeft = popcnt(mask & oldMask);
                    double oldContr = (v0 * oldLeft + v1 * (total - oldLeft)) / ob.steps;

                    int newLeft = popcnt(mask & newMask);
                    double newContr = (v0 * newLeft + v1 * (total - newLeft)) / ob.steps;

                    pred[idx] += newContr - oldContr;
                }

                split[line] = bestX;
            }
        }
    }

    void updateSegmentConfidence() {
        int strong = 0;
        int usable = 0;
        double sumConf = 0.0;

        for (int line = 0; line < LINE_VARS; line++) {
            if (lineSeen[line] < 3) continue;
            if (segSupport[2 * line] < 6) continue;
            if (segSupport[2 * line + 1] < 6) continue;

            usable++;

            double d = abs(segEst[2 * line] - segEst[2 * line + 1]);

            if (d > 900.0) strong++;
            sumConf += clampd((d - 500.0) / 1500.0, 0.0, 1.0);
        }

        double c1 = clampd((strong - 4) / 18.0, 0.0, 1.0);

        double c2 = 0.0;
        if (usable > 0) {
            double avg = sumConf / usable;
            c2 = clampd((avg - 0.12) / 0.38, 0.0, 1.0);
        }

        segGlobalConf = max(c1, 0.8 * c2);
    }

    double priorFineValue(int line, int q) const {
        double sum = 0.0;
        int cnt = 0;

        for (int pos = 0; pos < N - 1; pos++) {
            int qq = pos * FINE_BINS / (N - 1);
            if (qq != q) continue;

            if (line < N) {
                sum += rawStructH(line, pos);
            } else {
                int col = line - N;
                sum += rawStructV(pos, col);
            }
            cnt++;
        }

        if (cnt == 0) return lineEst[line];
        return sum / cnt;
    }

    void solveFineModel(int observationsCount) {
        vector<double> prior(FINE_VARS, 5000.0);

        for (int line = 0; line < LINE_VARS; line++) {
            for (int q = 0; q < FINE_BINS; q++) {
                int idx;
                if (line < N) idx = line * FINE_BINS + q;
                else idx = HFINE_VARS + (line - N) * FINE_BINS + q;

                prior[idx] = priorFineValue(line, q);
            }
        }

        double prog = min(1.0, observationsCount / 900.0);
        double lambdaFine = 1.05 - 0.45 * prog;

        vector<double> absFine;
        fineModel.solve(prior, lambdaFine, absFine);

        for (int i = 0; i < FINE_VARS; i++) {
            fineDelta[i] = clampd(absFine[i] - prior[i], -1300.0, 1300.0);
        }

        fineReady = true;
    }

    void solveModels(int observationsCount) {
        vector<double> priorLine(LINE_VARS, 5000.0);
        lineModel.solve(priorLine, 0.1, lineEst);

        int binPeriod = (observationsCount < 300 ? 10 : 20);
        if (observationsCount % binPeriod == 0) {
            vector<double> priorBin(BIN_VARS);

            for (int i = 0; i < N; i++) {
                for (int q = 0; q < BINS; q++) {
                    priorBin[i * BINS + q] = lineEst[i];
                }
            }

            for (int j = 0; j < N; j++) {
                for (int q = 0; q < BINS; q++) {
                    priorBin[HBIN_VARS + j * BINS + q] = lineEst[N + j];
                }
            }

            double prog = min(1.0, observationsCount / 800.0);
            double lambdaBin = 1.5 - prog;

            vector<double> absBin;
            binModel.solve(priorBin, lambdaBin, absBin);

            for (int i = 0; i < BIN_VARS; i++) {
                binDelta[i] = absBin[i] - priorBin[i];
            }
        }

        if (observationsCount >= 80) {
            int segPeriod = (observationsCount < 300 ? 20 : 30);

            if (observationsCount % segPeriod == 0) {
                seedSplitsFromBin();

                double prog = min(1.0, observationsCount / 900.0);
                double lambdaSeg = 0.9 - 0.55 * prog;

                solveSegmentRidge(lambdaSeg);
                refineSplits();
                solveSegmentRidge(lambdaSeg);
                updateSegmentConfidence();
            }
        }

        if (observationsCount >= 280 && (observationsCount - 280) % 80 == 0) {
            solveFineModel(observationsCount);
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver solver;

    for (int k = 0; k < 1000; k++) {
        int si, sj, ti, tj;
        if (!(cin >> si >> sj >> ti >> tj)) return 0;

        solver.turn = k;

        string path = solver.choosePath(si, sj, ti, tj);

        cout << path << '\n' << flush;

        int result;
        if (!(cin >> result)) return 0;

        solver.updateModelsWithResult(si, sj, path, result);

        if (k + 1 < 1000) {
            solver.solveModels(k + 1);
        }
    }

    return 0;
}
