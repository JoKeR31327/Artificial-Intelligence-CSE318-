#include <iostream>
#include <vector>
#include <map>
#include <fstream>
#include <algorithm>
#include <random>
#include <ctime>
#include <climits>
#include <utility>
#include <iomanip>
#include <sstream>
#include <chrono>


using namespace std;


struct Edge {
    int u, v, w;
};

struct Graph {
    int n, m;
    vector<Edge> edges;
    vector<vector<pair<int, int>>> adj;

    Graph(int n) : n(n), m(0) {
        adj.resize(n);
    }

    void addEdge(int u, int v, int w) {
        edges.push_back({u, v, w});
        adj[u].emplace_back(v, w);
        adj[v].emplace_back(u, w);
        m++;
    }

    int cutWeight(const vector<bool>& X) const {
        int total = 0;
        for (const auto& e : edges) {
            if (X[e.u] != X[e.v]) {
                total += e.w;
            }
        }
        return total;
    }
};

class MaxCutSolver {
public:
    const Graph& g;
    mt19937 rng;
    int local_iter=0;
    int grasp_iter=0;
    int grasp_local_iter=0;

    vector<bool> semiGreedy(double alpha) {
        if (g.edges.empty()) return vector<bool>(g.n, false);

        vector<Edge> sorted = g.edges;
        sort(sorted.begin(), sorted.end(), [](Edge a, Edge b) {
            return a.w > b.w;
        });

        vector<bool> X(g.n, false), assigned(g.n, false);
        int u = sorted[0].u, v = sorted[0].v;
        X[u] = true;
        assigned[u] = assigned[v] = true;

        int left = g.n - 2;
        while (left > 0) {
            vector<pair<int, pair<int, int>>> scores;
            int wmin = INT_MAX, wmax = INT_MIN;

            for (int i = 0; i < g.n; ++i) {
                if (assigned[i]) continue;

                int sx = 0, sy = 0;
                for (auto [nbr, w] : g.adj[i]) {
                    if (!assigned[nbr]) continue;
                    if (X[nbr]) sy += w;
                    else sx += w;
                }

                int s = max(sx, sy);
                scores.emplace_back(i, make_pair(sx, sy));
                wmin = min(wmin, s);
                wmax = max(wmax, s);
            }

            if (scores.empty()) break;

            int mu = wmin + alpha * (wmax - wmin);
            vector<int> RCL;
            for (auto& [i, sigmas] : scores) {
                if (max(sigmas.first, sigmas.second) >= mu) {
                    RCL.push_back(i);
                }
            }

            if (RCL.empty()) {
                int best = scores[0].first;
                int bestScore = max(scores[0].second.first, scores[0].second.second);
                for (auto& [v, s] : scores) {
                    int score = max(s.first, s.second);
                    if (score > bestScore) {
                        bestScore = score;
                        best = v;
                    }
                }
                X[best] = (scores[best].second.first > scores[best].second.second);
                assigned[best] = true;
            } else {
                int pick = RCL[rng() % RCL.size()];
                auto sigmas = scores[pick].second;
                X[pick] = (sigmas.first > sigmas.second);
                assigned[pick] = true;
            }
            left--;
        }
        return X;
    }

    MaxCutSolver(const Graph& graph) : g(graph), rng(time(0)) {}

    double randomized(int trials = 100) {
        int total = 0;
        for (int t = 0; t < trials; ++t) {
            vector<bool> X(g.n);
            for (int i = 0; i < g.n; ++i)
                X[i] = rng() % 2;
            total += g.cutWeight(X);
        }
        return static_cast<double>(total) / trials;
    }

    vector<bool> greedy() {
        vector<Edge> sorted = g.edges;
        sort(sorted.begin(), sorted.end(), [](Edge a, Edge b) {
            return a.w > b.w;
        });

        vector<bool> X(g.n, false);
        int u = sorted[0].u, v = sorted[0].v;
        X[u] = true;
        X[v] = false;

        for (int i = 0; i < g.n; ++i) {
            if (i == u || i == v) continue;
            int wX = 0, wY = 0;
            for (auto [nbr, w] : g.adj[i]) {
                if (X[nbr]) wY += w;
                else wX += w;
            }
            X[i] = (wX > wY);
        }
        return X;
    }

    vector<bool> localSearch(vector<bool> X) {
        bool improved = true;
        int current = g.cutWeight(X);
        local_iter=0;
        while (improved) {
            improved = false;

            for (int v = 0; v < g.n; ++v) {
                int original = 0, flipped = 0;
                for (auto [u, w] : g.adj[v]) {
                    if (X[u] != X[v]) original += w;
                    else flipped += w;
                }

                if (flipped > original) {
                    X[v] = !X[v];
                    current += (flipped - original);
                    improved = true;
                }
            }
            local_iter++;
        }
        return X;
    }

    vector<bool> grasp(int iterations = 50, double alpha = 0.5) {
        grasp_iter=iterations;
        int best = -1;
        vector<bool> bestX;
        grasp_local_iter=0;
        for (int i = 0; i < iterations; ++i) {
            vector<bool> X = semiGreedy(alpha);
            X = localSearch(X);
            grasp_local_iter++;
            int weight = g.cutWeight(X);
            if (weight > best) {
                best = weight;
                bestX = X;
            }
        }
        return bestX;
    }

    vector<bool> runSemiGreedy(double alpha) {
        return semiGreedy(alpha);
    }
};

Graph readGraphFromFile(const string& filename) {
    ifstream file(filename);
    if (!file.is_open()) {
        cerr << "Error: Could not open file " << filename << endl;
        exit(1);
    }

    int n, m;
    file >> n >> m;
    Graph g(n);
    int u, v, w;
    while (file >> u >> v >> w) {
        g.addEdge(u - 1, v - 1, w);
    }
    return g;
}

int avglocal(Graph g,MaxCutSolver solver, vector<bool> semi_X, int n=25){
    int totalCutweight=0;
    for (int i = 0; i < n; i++) 
    {
    auto local_X = solver.localSearch(semi_X);
    int val = g.cutWeight(local_X);                
    totalCutweight += val;
    }
    return totalCutweight / n;
}


void generatecsv(const vector<string>& benchmark_files, const map<string, string>& known_bests) {
    ofstream csv("2105166.csv");
    if (!csv.is_open()) {
        cerr << "Error: Could not create CSV file." << endl;
        return;
    }

    csv << ",Problem,,,Constructive algorithm,,Local Search,,GRASP,,Known best solution\n";
    csv <<",,,,,,Simple Local-1,,,,\n";

    csv << "name,|V|,|E|,Simple Randomized,Simple Greedy,Semi-greedy-1,"
        << "No. of iterations,Average value,"
        << "No. of iterations,Best value,\n";

    for (const string& filename : benchmark_files) {
        string problem_name = filename.substr(0, filename.find('.'));

        ifstream test(filename);
        if (!test.is_open()) {
            csv << problem_name << ",N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,"
                << (known_bests.count(problem_name) ? known_bests.at(problem_name) : "N/A") << "\n";
            continue;
        }
        test.close();

        Graph g = readGraphFromFile(filename);
        MaxCutSolver solver(g);
        
        double rand_avg = solver.randomized();
        auto greedy_X = solver.greedy();
        int greedy_val = g.cutWeight(greedy_X);
        auto semi_X = solver.runSemiGreedy(0.5);
        int semi_val = g.cutWeight(semi_X);
        auto local_X = solver.localSearch(semi_X);
        int local_val = g.cutWeight(local_X);
        int local_iters = solver.local_iter; 
        // int local_iters= avglocal(g,solver,semi_x,25);
        auto grasp_X = solver.grasp(25, 0.5);
        int grasp_val = g.cutWeight(grasp_X);
        int grasp_iters = solver.grasp_iter;  
        

        csv << problem_name << ","
            << g.n << ","
            << g.m << ","
            << fixed << setprecision(2) << rand_avg << ","
            << greedy_val << ","
            << semi_val << ","
            << local_iters << "," << local_val << ","
            << grasp_iters << "," << grasp_val << ","
            << (known_bests.count(problem_name) ? known_bests.at(problem_name) : "N/A") << "\n";
    }

    csv.close();
    cout << "CSV file generated: 2105166.csv" << endl;
}




int main() {

    // Graph g = readGraphFromFile("test.txt");
    // MaxCutSolver solver(g);

    // // cout << "Randomized: " << solver.randomized() << endl;

    // // auto greedyX = solver.greedy();
    // // cout << "Greedy: " << g.cutWeight(greedyX) << endl;

    // auto semi = solver.runSemiGreedy(0.5);
    // cout << "Semi-Greedy: " << g.cutWeight(semi) << endl;

    // // cout << "Before Local Search: " << g.cutWeight(semi) << endl;
    // // auto local = solver.localSearch(semi);
    // // cout << "After Local Search: " << g.cutWeight(local) << endl;

    // // auto best = solver.grasp(50, 0.5);
    // // cout << "GRASP Best: " << g.cutWeight(best) << endl;


    using namespace std::chrono;

    auto start = high_resolution_clock::now();

    vector<string> files;
    string ext = ".rud";
    for (int i = 1; i <= 54; i++) {
        string s = "g" + to_string(i) + ext;
        files.push_back(s);
    }


    map<string, string> known_bests = {
        {"g1", "12078"}, {"g2", "12084"}, {"g3", "12077"},
        {"g11", "627"}, {"g12", "621"}, {"g13", "645"},
        {"g14", "3187"}, {"g15", "3169"}, {"g16", "3172"},
        {"g22", "14123"}, {"g23", "14129"}, {"g24", "14131"},
        {"g32", "1560"}, {"g33", "1537"}, {"g34", "1541"},
        {"g35", "8000"}, {"g36", "7996"}, {"g37", "8009"},
        {"g43", "7027"}, {"g44", "7022"}, {"g45", "7020"},
        {"g48", "6000"}, {"g49", "6000"}, {"g50", "5988"}
    };
    generatecsv(files, known_bests);

    auto end = high_resolution_clock::now();
    auto duration = duration_cast<milliseconds>(end - start);

    cout << "Time taken: " << duration.count() << " ms" << endl;

    return 0;
}