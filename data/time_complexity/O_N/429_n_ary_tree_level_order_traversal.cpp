/**
 * Problem: 429. N-ary Tree Level Order Traversal
 *
 * Time Complexity: O(N)
 *   - We visit each node exactly once, adding/removing them from a queue.
 *
 * Space Complexity: O(N)
 *   - In the worst case (e.g., a very bushy tree), the queue can hold nearly all nodes at once.
 *
 * Approach (BFS with a Queue):
 *   1) If root is null, return an empty list.
 *   2) Initialize a queue with the root node.
 *   3) While queue not empty:
 *      - get the current queue size = # nodes in this level
 *      - pop each node in this level, push the node's children to the queue
 *      - store their values in a sub-list
 *   4) Append that sub-list to the final result
 *
 * Example usage:
 *   Node* root = ...; // build N-ary tree
 *   Solution sol;
 *   vector<vector<int>> levels = sol.levelOrder(root);
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 // Definition for an N-ary tree node.
 class Node {
 public:
     int val;
     vector<Node*> children;
 
     Node() {}
     Node(int _val) { val = _val; }
     Node(int _val, vector<Node*> _children) {
         val = _val;
         children = _children;
     }
 };
 
 class Solution {
 public:
     vector<vector<int>> levelOrder(Node* root) {
         vector<vector<int>> result;
         if (!root) return result;
 
         // Standard BFS approach with queue
         queue<Node*> q;
         q.push(root);
 
         while (!q.empty()) {
             int levelSize = q.size();       // number of nodes in this level
             vector<int> level;             // to store values of the current level
 
             for (int i = 0; i < levelSize; i++) {
                 Node* node = q.front();    // get next node
                 q.pop();
 
                 level.push_back(node->val);
                 // enqueue all children
                 for (Node* child : node->children) {
                     q.push(child);
                 }
             }
             // add this level's values to the result
             result.push_back(level);
         }
 
         return result;
     }
 };
 
 // Optional test main()
 int main() {
     // Example: root = [1,null,3,2,4,null,5,6]
     // Build a small N-ary tree:
     Node* node5 = new Node(5);
     Node* node6 = new Node(6);
     Node* node3 = new Node(3, {node5, node6});
     Node* node2 = new Node(2);
     Node* node4 = new Node(4);
     Node* root = new Node(1, {node3, node2, node4});
 
     Solution sol;
     vector<vector<int>> ans = sol.levelOrder(root);
 
     // Print result
     for (auto &level : ans) {
         for (int val : level) cout << val << " ";
         cout << endl;
     }
     // Expected output:
     // 1
     // 3 2 4
     // 5 6
 
     return 0;
 }