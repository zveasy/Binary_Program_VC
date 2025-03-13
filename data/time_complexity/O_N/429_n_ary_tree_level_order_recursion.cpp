/**
 * Problem: 429. N-ary Tree Level Order Traversal (Recursion)
 *
 * Time Complexity: O(N)
 *   - Each node visited once. In total, O(N) calls.
 *
 * Space Complexity: O(N)
 *   - Worst-case recursion depth can be O(N) if the tree is skewed (like a linked list).
 *   - 'result' also stores all node values, but that is required output space.
 *
 * Approach (Recursion):
 *   1) We'll maintain a 'result' vector of vectors (levels).
 *   2) A helper function traverse(node, level):
 *      - If level == result.size(), we push_back a new empty vector to represent that level.
 *      - Append node->val to result[level].
 *      - For each child, call traverse(child, level+1).
 *   3) This is effectively a DFS, but we label nodes by their depth "level".
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
 private:
     vector<vector<int>> result;
 
     void traverse(Node* node, int level) {
         if (!node) return;
 
         // if we haven't yet created a vector for this level, create it
         if (level == (int)result.size()) {
             result.push_back({});
         }
 
         // add the current node's value to this level
         result[level].push_back(node->val);
 
         // recurse on all children, with level + 1
         for (Node* child : node->children) {
             traverse(child, level + 1);
         }
     }
 
 public:
     vector<vector<int>> levelOrder(Node* root) {
         result.clear();
         if (root) traverse(root, 0);
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