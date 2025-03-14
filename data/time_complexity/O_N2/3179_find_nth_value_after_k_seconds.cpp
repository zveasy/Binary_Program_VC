/**
 * Problem: 3179. Find the N-th Value After K Seconds
 *
 * Time Complexity:
 *   - O(N²), as we iterate `k` times over `n` elements.
 *
 * Space Complexity:
 *   - O(N), using a single DP array instead of a full 2D matrix.
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 class Solution {
 public:
     int valueAfterKSeconds(int n, int k) {
         vector<int> dp(n, 1);
         int mod = 1e9 + 7;
 
         for (int i = 1; i <= k; i++) {
             for (int j = 1; j < n; j++) {
                 dp[j] = (dp[j] + dp[j - 1]) % mod;
             }
         }
         return dp[n - 1];
     }
 };
 
 // Optional main() for testing
 int main() {
     Solution sol;
     cout << sol.valueAfterKSeconds(4, 5) << endl;  // Output: 56
     cout << sol.valueAfterKSeconds(5, 3) << endl;  // Output: 35
     return 0;
 }