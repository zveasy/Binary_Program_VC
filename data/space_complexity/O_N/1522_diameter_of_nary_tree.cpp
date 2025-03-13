/**
 * Problem: 1522. Diameter of N-Ary Tree
 *
 * Time Complexity: O(N)
 *   - We do a DFS of the entire N-ary tree exactly once.
 *   - Each node is visited once, and we combine child heights in O(#children).
 *   - The total number of children across all nodes is O(N).
 *
 * Space Complexity: O(N)
 *   - Recursion stack can go up to O(N) in the worst case (a chain-like tree).
 *   - We only store a few variables per node in the recursion (constant).
 *
 * Approach (Height-Based):
 *   1) The "height" of a node is the distance down to its furthest leaf.
 *   2) At each node, pick the top two children's heights: h1, h2.
 *   3) The diameter candidate through this node is h1 + h2 (plus 2 edges).
 *   4) We update the global diameter if h1 + h2 is larger.
 *   5) The height of a node is max(child_height) + 1.
 *
 * Example usage:
 *   Node* root = ...
 *   Solution sol;
 *   int ans = sol.diameterOfNAryTree(root);
 *   // ans = diameter length
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
 private:
     int diameter;  // track the max diameter found
 
     // Return the height of the current node
     // Also update 'diameter' with the longest path bridged by this node
     int height(Node* node) {
         if(!node) return 0;
         if(node->children.empty()) {
             return 0;  // a leaf's height = 0
         }
 
         // track top two largest child heights
         int maxH1 = 0, maxH2 = 0;  
 
         // compute each child's height
         for(Node* child : node->children) {
             int h = height(child) + 1;
             // update top two child heights if needed
             if(h > maxH1) {
                 maxH2 = maxH1;
                 maxH1 = h;
             } else if(h > maxH2) {
                 maxH2 = h;
             }
         }
 
         // the path that passes through this node is maxH1 + maxH2
         // 'distance' in edges is maxH1 + maxH2
         // update the global diameter if needed
         diameter = max(diameter, maxH1 + maxH2);
 
         // return the highest child's height
         return maxH1;
     }
 
 public:
     int diameterOfNAryTree(Node* root) {
         diameter = 0;
         height(root);
         return diameter;
     }
 };
 
 // Optional test main()
 int main() {
     /* Example 1: root = [1,null,3,2,4,null,5,6]
        manually build the tree:
          1
         /|\
        3 2 4
       / \
      5   6
      diameter = 3
     */
     Node* node5 = new Node(5);
     Node* node6 = new Node(6);
     Node* node3 = new Node(3, {node5, node6});
     Node* node2 = new Node(2);
     Node* node4 = new Node(4);
     Node* root = new Node(1, {node3, node2, node4});
 
     Solution sol;
     cout << sol.diameterOfNAryTree(root) << endl; // Expect 3
 
     return 0;
 }