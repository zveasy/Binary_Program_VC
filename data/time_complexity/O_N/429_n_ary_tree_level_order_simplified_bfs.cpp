/**
 * Problem: 429. N-ary Tree Level Order Traversal (Simplified BFS)
 *
 * Time Complexity: O(N)
 *   - Each node is visited exactly once.
 *
 * Space Complexity: O(N)
 *   - In worst case, we could store nearly all nodes in the "currentLayer" or "previousLayer".
 *
 * Approach (Simplified BFS):
 *   1) If root is null, return empty list.
 *   2) Keep a list 'previousLayer' for the current level.
 *      - Initialize with {root}.
 *   3) While 'previousLayer' is not empty:
 *      - Build a vector of values for the current level.
 *      - Build a list of children -> 'currentLayer' for the next level.
 *      - Move 'currentLayer' into 'previousLayer' for the next iteration.
 */

 #include <bits/stdc++.h>
 using namespace std;
 
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
 
         // 'previousLayer' holds all nodes at the current level
         vector<Node*> previousLayer = {root};
 
         while (!previousLayer.empty()) {
             vector<int> currentVals;
             vector<Node*> currentLayer;  // the next level
 
             // Build the list of values for this level and gather the children for the next level
             for (Node* node : previousLayer) {
                 currentVals.push_back(node->val);
                 for (Node* child : node->children) {
                     currentLayer.push_back(child);
                 }
             }
 
             // Add the current level's values to the result
             result.push_back(currentVals);
             // The next iteration will process 'currentLayer'
             previousLayer = currentLayer;
         }
 
         return result;
     }
 };
 
 // Optional test main
 int main(){
     // Example: root = [1,null,3,2,4,null,5,6]
     Node* node5 = new Node(5);
     Node* node6 = new Node(6);
     Node* node3 = new Node(3, {node5, node6});
     Node* node2 = new Node(2);
     Node* node4 = new Node(4);
     Node* root = new Node(1, {node3, node2, node4});
 
     Solution sol;
     vector<vector<int>> ans = sol.levelOrder(root);
 
     // Print the result
     for (auto &level : ans) {
         for (int val : level) cout << val << " ";
         cout << endl;
     }
     // Expected:
     // 1
     // 3 2 4
     // 5 6
 
     return 0;
 }