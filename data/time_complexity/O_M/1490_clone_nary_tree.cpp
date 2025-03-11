#include <vector>
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

        // Clone the current node
        Node* newRoot = new Node(root->val);

        // Recursively clone children
        for (Node* child : root->children) {
            newRoot->children.push_back(cloneTree(child));
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