/**
 * Problem: 1884. Egg Drop With 2 Eggs and N Floors
 *
 * Time Complexity:
 *   - O(√n), since we solve using the sum formula (m * (m + 1) / 2) ≥ n.
 *   - We increment 'm' until this equation holds, leading to O(√n).
 *
 * Space Complexity:
 *   - O(1), since we only use a few integer variables.
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 class Solution {
 public:
     int twoEggDrop(int n) {
         int m = 1;
         while ((m * (m + 1)) / 2 < n) {
             ++m;
         }
         return m;
     }
 };
 
 // Optional main() for quick testing
 int main() {
     Solution sol;
     cout << sol.twoEggDrop(2) << endl;  // Output: 2
     cout << sol.twoEggDrop(100) << endl;  // Output: 14
     return 0;
 }