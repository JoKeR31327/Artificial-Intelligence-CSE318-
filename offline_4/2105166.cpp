#include <bits/stdc++.h>
using namespace std;

#define MAX_DEPTH 1000

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

class TreeNode {
public:
    int attribute_in;
    string attribute_val;
    string label;
    unordered_map<string, TreeNode*> children;
    bool is_leaf;
    bool is_numeric_split;
    double threshold;

    TreeNode() : attribute_in(-1), is_leaf(false), is_numeric_split(false), threshold(0) {}
};


class Dataset {
public:
    vector<vector<string>> data;
    vector<string> attributes;
    string target_att;
};

bool missed_value(const vector<string>& row) {
    for (const auto& val : row) {
        if (val.empty() || val == "?") return true;
    }
    return false;
}

class DataHandler {
public:
    static Dataset load_csv(const string& filename) {
    Dataset dataset;
    ifstream file(filename);
    string line;

    if (!file.is_open()) {
        cerr << "Error opening file: " << filename << endl;
        return dataset;
    }

    bool rmv_first_col = false;
    string filename_lower = filename;
    transform(filename_lower.begin(), filename_lower.end(), filename_lower.begin(), ::tolower);
    if (filename_lower.find("iris") != string::npos) {
        rmv_first_col = true;
        cout << "[INFO] Excluding first column (likely ID) for file: " << filename << endl;
    }


    if (getline(file, line)) {
        stringstream ss(line);
        string attribute;
        bool first = true;
        while (getline(ss, attribute, ',')) {
            if (rmv_first_col && first) {
                first = false;
                continue;  
            }
            dataset.attributes.push_back(attribute);
            first = false;
        }
    }

    while (getline(file, line)) {
        stringstream ss(line);
        string value;
        vector<string> row;
        bool first = true;
        while (getline(ss, value, ',')) {
            value.erase(value.begin(), find_if(value.begin(), value.end(), [](unsigned char ch) {
                return !isspace(ch);
            }));
            value.erase(find_if(value.rbegin(), value.rend(), [](unsigned char ch) {
                return !isspace(ch);
            }).base(), value.end());

            if (rmv_first_col && first) {
                first = false;
                continue; 
            }

            row.push_back(value);
            first = false;
        }

        if (!row.empty()) {
            dataset.data.push_back(row);
        }
    }

    return dataset;
}


    static vector<Dataset> test_split(const Dataset& dataset, double test_size) {
        vector<Dataset> result(2);
        result[0].attributes = dataset.attributes;
        result[1].attributes = dataset.attributes;
        result[0].target_att = dataset.target_att;
        result[1].target_att = dataset.target_att;

        vector<size_t> indices(dataset.data.size());
        for (size_t i = 0; i < indices.size(); ++i) {
            indices[i] = i;
        }
        shuffle(indices.begin(), indices.end(), rng);

        size_t split_point = static_cast<size_t>(dataset.data.size() * (1.0 - test_size));

        for (size_t i = 0; i < indices.size(); ++i) {
            if (i < split_point) {
                result[0].data.push_back(dataset.data[indices[i]]);
            } else {
                result[1].data.push_back(dataset.data[indices[i]]);
            }
        }

        return result;
    }

    static bool is_num(const Dataset& dataset, int att_in) {
        for (const auto& row : dataset.data) {
            if (row.size() <= att_in) continue;
            const string& val = row[att_in];
            if (val.empty() || val == "?") continue;
            
            try {
                stod(val);
            } catch (...) {
                return false;
            }
        }
        return true;
    }

        static double mean_num(const Dataset& dataset, int att_in) {
        double sum = 0;
        int count = 0;
        for (const auto& row : dataset.data) {
            if (row.size() <= att_in) continue;
            const string& val = row[att_in];
            if (val.empty() || val == "?") continue;
            try {
                double d = stod(val);
                sum += d;
                count++;
            } catch (...) {}
        }
        return (count > 0) ? (sum / count) : 0;
    }

    static string mode_string(const Dataset& dataset, int att_in) {
        unordered_map<string, int> freq;
        for (const auto& row : dataset.data) {
            if (row.size() <= att_in) continue;
            const string& val = row[att_in];
            if (val.empty() || val == "?") continue;
            freq[val]++;
        }
        string mode_val = "";
        int max_count = 0;
        for (const auto& [val, count] : freq) {
            if (count > max_count) {
                max_count = count;
                mode_val = val;
            }
        }
        return mode_val;
    }

    static void fill_missing_values(Dataset& dataset) {
        int num_attributes = dataset.attributes.size();
        vector<bool> numeric_flags(num_attributes, false);

        for (int i = 0; i < num_attributes; i++) {
            numeric_flags[i] = is_num(dataset, i);
        }

        vector<string> fill_values(num_attributes);

        for (int i = 0; i < num_attributes; i++) {
            if (numeric_flags[i]) {
                double m = mean_num(dataset, i);
                fill_values[i] = to_string(m);
            } else {
                fill_values[i] = mode_string(dataset, i);
            }
        }

        for (auto& row : dataset.data) {
            for (int i = 0; i < num_attributes; i++) {
                if (row.size() <= i || row[i].empty() || row[i] == "?") {
                    row[i] = fill_values[i];
                }
            }
        }
    }
 
};

class DecisionTree {
private:
    TreeNode* root;
    string criterion;
    int max_depth;

    double entropy(const Dataset& dataset) {
        unordered_map<string, int> class_counts;
        int total = 0;
        int target_index = dataset.attributes.size() - 1;

        for (const auto& row : dataset.data) {
            if (row.size() <= target_index) continue;
            class_counts[row[target_index]]++;
            total++;
        }

        if (total == 0) return 0;

        double ent = 0;
        for (const auto& pair : class_counts) {
            double p = static_cast<double>(pair.second) / total;
            ent -= p * log2(p);
        }

        return ent;
    }

    double info_gain(const Dataset& dataset, int attribute_in) {
        double ent = entropy(dataset);
        if (ent == 0) return 0;

        unordered_map<string, vector<vector<string>>> subsets;
        int total = 0;

        for (const auto& row : dataset.data) {
            if (row.size() <= attribute_in) continue;
            subsets[row[attribute_in]].push_back(row);
            total++;
        }

        double weighted_ent = 0;
        for (const auto& pair : subsets) {
            Dataset subset;
            subset.attributes = dataset.attributes;
            subset.data = pair.second;
            subset.target_att = dataset.target_att;

            double subset_ent = entropy(subset);
            weighted_ent += (static_cast<double>(pair.second.size()) / total) * subset_ent;
        }

        return ent - weighted_ent;
    }

    double gain_ratio(const Dataset& dataset, int attribute_in) {
        double information_gain = info_gain(dataset, attribute_in);
        if (information_gain == 0) return 0;

        unordered_map<string, int> value_counts;
        int total = 0;

        for (const auto& row : dataset.data) {
            if (row.size() <= attribute_in) continue;
            value_counts[row[attribute_in]]++;
            total++;
        }

        double iv = 0;
        for (const auto& pair : value_counts) {
            double p = static_cast<double>(pair.second) / total;
            iv -= p * log2(p);
        }

        if (iv == 0) return 0;
        return information_gain / iv;
    }

    double nwig(const Dataset& dataset, int attribute_in) {
        double information_gain = info_gain(dataset, attribute_in);
        if (information_gain == 0) return 0;

        unordered_map<string, int> value_counts;
        int total = 0;

        for (const auto& row : dataset.data) {
            if (row.size() <= attribute_in) continue;
            value_counts[row[attribute_in]]++;
            total++;
        }

        int k = value_counts.size();
        if (k == 0 || total == 0) return 0;

        double denominator = log2(k + 1);
        double second_term = 1.0 - static_cast<double>(k - 1) / total;

        return (information_gain / denominator) * second_term;
    }

   int select_best_attribute(const Dataset& dataset, double& best_threshold, bool& is_numeric, const string& criterion) {
    int best_attribute = -1;
    double best_score = -1;
    best_threshold = 0;
    is_numeric = false;

    int num_attributes = dataset.attributes.size() - 1;

    for (int i = 0; i < num_attributes; ++i) {
        bool numeric = DataHandler::is_num(dataset, i);

        if (numeric) {
            auto [thresh, gain] = best_threshold_info_gain(dataset, i, criterion);
            if (gain > best_score) {
                best_score = gain;
                best_attribute = i;
                best_threshold = thresh;
                is_numeric = true;
            }
        } else {
            double gain = 0;
            if (criterion == "IG") {
                gain = info_gain(dataset, i);
            } else if (criterion == "IGR") {
                gain = gain_ratio(dataset, i);
            } else if (criterion == "NWIG") {
                gain = nwig(dataset, i);
            }

            if (gain > best_score) {
                best_score = gain;
                best_attribute = i;
                is_numeric = false;
            }
        }
    }

    return best_attribute;
}


double info_gain(const Dataset& parent, const Dataset& left, const Dataset& right) {
    double parent_entropy = entropy(parent);
    int total = parent.data.size();
    int left_size = left.data.size();
    int right_size = right.data.size();

    double weighted_entropy = 0;
    if (left_size > 0)
        weighted_entropy += (static_cast<double>(left_size) / total) * entropy(left);
    if (right_size > 0)
        weighted_entropy += (static_cast<double>(right_size) / total) * entropy(right);

    return parent_entropy - weighted_entropy;
}

double gain_ratio(const Dataset& parent, const Dataset& left, const Dataset& right) {
    double ig = info_gain(parent, left, right);
    if (ig == 0) return 0;

    int total = parent.data.size();
    int left_size = left.data.size();
    int right_size = right.data.size();

    double split_info = 0;
    if (left_size > 0) {
        double p = static_cast<double>(left_size) / total;
        split_info -= p * log2(p);
    }
    if (right_size > 0) {
        double p = static_cast<double>(right_size) / total;
        split_info -= p * log2(p);
    }

    if (split_info == 0) return 0;
    return ig / split_info;
}

double normalized_weighted_info_gain(const Dataset& parent, const Dataset& left, const Dataset& right) {
    double ig = info_gain(parent, left, right);
    if (ig == 0) return 0;

    int total = parent.data.size();
    int k = 2;
    double denominator = log2(k + 1);
    double second_term = 1.0 - static_cast<double>(k - 1) / total;

    return (ig / denominator) * second_term;
}




pair<double, double> best_threshold_info_gain(const Dataset& dataset, int attr_index, const string& criterion) {
    vector<pair<double, string>> values;

    for (const auto& row : dataset.data) {
        try {
            double val = stod(row[attr_index]);
            values.emplace_back(val, row.back());
        } catch (...) {}
    }

    sort(values.begin(), values.end());

    double best_threshold = 0;
    double best_score = -1e9;

    for (size_t i = 1; i < values.size(); ++i) {
        if (values[i - 1].second == values[i].second) continue;

        double threshold = (values[i - 1].first + values[i].first) / 2.0;

        Dataset left, right;
        left.attributes = right.attributes = dataset.attributes;

        for (const auto& row : dataset.data) {
            try {
                double val = stod(row[attr_index]);
                if (val <= threshold) left.data.push_back(row);
                else right.data.push_back(row);
            } catch (...) {}
        }

        if (left.data.empty() || right.data.empty()) continue;

        double gain = 0;

        if (criterion == "IG") {
            gain = info_gain(dataset, left, right);
        } else if (criterion == "IGR") {
            gain = gain_ratio(dataset, left, right);
        } else if (criterion == "NWIG") {
            gain = normalized_weighted_info_gain(dataset, left, right);
        }

        if (gain > best_score) {
            best_score = gain;
            best_threshold = threshold;
        }
    }

    return {best_threshold, best_score};
}


TreeNode* build(const Dataset& dataset, int depth) {
    TreeNode* node = new TreeNode();

    if (dataset.data.empty()) {
        node->is_leaf = true;
        node->label = "Unknown";
        return node;
    }

    string first_label = dataset.data[0].back();
    bool same = all_of(dataset.data.begin(), dataset.data.end(),
                       [&](const auto& row) { return row.back() == first_label; });

    if (same || dataset.attributes.size() <= 1 || (depth == max_depth)) {
        node->is_leaf = true;
        unordered_map<string, int> counts;
        for (const auto& row : dataset.data)
            counts[row.back()]++;

        node->label = max_element(counts.begin(), counts.end(),
                                  [](auto& a, auto& b) { return a.second < b.second; })->first;
        return node;
    }

    double best_thresh;
    bool is_num;
    int best_attr = select_best_attribute(dataset, best_thresh, is_num, criterion);

    if (best_attr == -1) {
        node->is_leaf = true;
        node->label = first_label;
        return node;
    }

    node->attribute_in = best_attr;
    node->attribute_val = dataset.attributes[best_attr];
    node->is_numeric_split = is_num;
    node->threshold = best_thresh;

    if (is_num) {
        Dataset left, right;
        left.attributes = right.attributes = dataset.attributes;

        for (const auto& row : dataset.data) {
            try {
                double val = stod(row[best_attr]);
                if (val <= best_thresh) left.data.push_back(row);
                else right.data.push_back(row);
            } catch (...) {
            }
        }

        if (left.data.empty() && right.data.empty()) {
            node->is_leaf = true;
            node->label = first_label;
            return node;
        }

        if (!left.data.empty())
            node->children["<="] = build(left, depth + 1);
        if (!right.data.empty())
            node->children[">"] = build(right, depth + 1);

    } else {
        unordered_map<string, Dataset> splits;
        for (const auto& row : dataset.data)
            splits[row[best_attr]].data.push_back(row);

        for (auto& [val, part] : splits) {
            part.attributes = dataset.attributes;
            if (!part.data.empty())
                node->children[val] = build(part, depth + 1);
        }
    }

    return node;
}


    string classify(const TreeNode* node, const vector<string>& instance) const {
        if (node->is_leaf) return node->label;
        if (node->attribute_in >= instance.size()) return node->label;

        if (node->is_numeric_split) {
            try {
                double val = stod(instance[node->attribute_in]);
                if (val <= node->threshold && node->children.count("<=")) {
                    return classify(node->children.at("<="), instance);
                } else if (node->children.count(">")) {
                    return classify(node->children.at(">"), instance);
                }
            } catch (...) {
                return node->label;
            }
        } else {
            string value = instance[node->attribute_in];
            if (node->children.count(value))
                return classify(node->children.at(value), instance);
        }

        return node->label;
}


    void delete_tree(TreeNode* node) {
        if (!node) return;
        
        for (auto& pair : node->children) {
            delete_tree(pair.second);
        }
        
        delete node;
    }

public:
    DecisionTree(const string& criterion, int max_depth) : criterion(criterion), max_depth(max_depth), root(nullptr) {}
    ~DecisionTree() { delete_tree(root); }

    void train(const Dataset& dataset) {
        root = build(dataset, 0);
    }

    string predict(const vector<string>& instance) const {
        if (!root) return "Unknown";
        return classify(root, instance);
    }

    double evaluate(const Dataset& test_data) const {
        if (test_data.data.empty() || !root) return 0;

        int correct = 0;
        int target_index = test_data.attributes.size() - 1;

        for (const auto& row : test_data.data) {
            string predicted = predict(row);
            if (predicted == row[target_index]) {
                correct++;
            }
        }

        return static_cast<double>(correct) / test_data.data.size();
    }
    int count_nodes(TreeNode* node) const {
    if (!node) return 0;
    int count = 1;
    for (auto& child : node->children)
        count += count_nodes(child.second);
    return count;
}

int count_nodes() const {
    return count_nodes(root);
}
};






int main(int argc, char* argv[]) {
    if (argc != 4) {
        cerr << "Usage: " << argv[0] << " <dataset.csv> <criterion(IG|IGR|NWIG)> <maxDepth>" << endl;
        return 1;
    }

    string filename = argv[1];
    string criterion = argv[2];
    int max_depth = stoi(argv[3]);

    if (criterion != "IG" && criterion != "IGR" && criterion != "NWIG") {
        cerr << "Invalid criterion. Use IG, IGR, or NWIG." << endl;
        return 1;
    }

    Dataset dataset = DataHandler::load_csv(filename);
    if (dataset.data.empty()) {
        cerr << "Failed to load dataset or dataset is empty." << endl;
        return 1;
    }
    DataHandler::fill_missing_values(dataset); 
    dataset.target_att = dataset.attributes.back();


    const int num_experiments = 20;
    double total_accuracy = 0;
    vector<double> accuracies;
    if (max_depth == 0) max_depth = MAX_DEPTH;

    cout << "Running " << num_experiments << " experiments with " << criterion 
         << " criterion and max depth " << max_depth << endl;

    for (int i = 0; i < num_experiments; ++i) {
        vector<Dataset> splits = DataHandler::test_split(dataset, 0.2);
        Dataset train_data = splits[0];
        Dataset test_data = splits[1];

        DecisionTree tree(criterion, max_depth);
        tree.train(train_data);

        double accuracy = tree.evaluate(test_data);
        accuracies.push_back(accuracy);
        total_accuracy += accuracy;
    }

    double average_accuracy = total_accuracy / num_experiments;

    cout << fixed << setprecision(2);
    cout << "\nResults after " << num_experiments << " experiments:" << endl;
    cout << "Average accuracy: " << average_accuracy * 100 << "%" << endl;

    return 0;
}