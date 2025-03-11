#include <vector>
#include <stack>
using namespace std;

class Node {
public:
    int val;
    vector<Node*> children;

    Node() {}

    Node(int _val) {
        val = _val;
    }

    Node(int _val, vector<Node*> _children) {
        val = _val;
        children = _children;
    }
};

class Solution {
public:
    Node* cloneTree(Node* root) {
        if (!root) return nullptr;

        // Stack to simulate DFS traversal
        stack<pair<Node*, Node*>> s;
        Node* newRoot = new Node(root->val);
        s.push({root, newRoot});

        while (!s.empty()) {
            auto [origNode, cloneNode] = s.top();
            s.pop();

            for (Node* child : origNode->children) {
                Node* clonedChild = new Node(child->val);
                cloneNode->children.push_back(clonedChild);
                s.push({child, clonedChild});
            }
        }
        return newRoot;
    }
};

// Driver Code
#include <iostream>

void printTree(Node* root) {
    if (!root) return;
    cout << root->val << " ";
    for (Node* child : root->children) {
        printTree(child);
    }
}

int main() {
    Node* root = new Node(1, {new Node(3, {new Node(5), new Node(6)}), new Node(2), new Node(4)});
    Solution solution;
    Node* clonedRoot = solution.cloneTree(root);

    cout << "Original Tree: ";
    printTree(root);
    cout << "\nCloned Tree: ";
    printTree(clonedRoot);
    cout << endl;
    
    return 0;
}