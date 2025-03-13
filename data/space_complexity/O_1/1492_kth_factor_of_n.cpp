/**
 * Problem: 1492. The kth Factor of n
 * 
 * Time Complexity: O(n)
 *   - We iterate from 1 to n and check divisibility. Each check is O(1), 
 *     so total is O(n).
 * 
 * Space Complexity: O(1)
 *   - We use only constant extra space (no additional data structures).
 * 
 * Explanation:
 *   - We loop through integers i = 1..n.
 *   - If i divides n (n % i == 0), decrement k. 
 *   - Once k == 0, we return i because it's the k-th factor.
 *   - If we finish the loop without hitting k == 0, return -1.
 * 
 * Follow-Up:
 *   Could we do better than O(n)? 
 *   - For large n, yes, we can search factors up to sqrt(n). But given n<=1000,
 *     O(n) is acceptable here.
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 class Solution {
 public:
     int kthFactor(int n, int k) {
         for(int curr = 1; curr <= n; curr++) {
             if(n % curr == 0) {
                 k--;
                 if(k == 0) {
                     return curr;
                 }
             }
         }
         return -1;
     }
 };
 
 // Optional test main()
 int main() {
     Solution sol;
     cout << sol.kthFactor(12, 3) << endl; // Expected 3
     cout << sol.kthFactor(7, 2) << endl;  // Expected 7
     cout << sol.kthFactor(4, 4) << endl;  // Expected -1
     return 0;
 }