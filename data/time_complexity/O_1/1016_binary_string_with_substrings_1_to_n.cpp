/**
 * Problem: 1016. Binary String With Substrings Representing 1 To N
 *
 * Time Complexity:
 *   - We iterate over the binary string 's' once, with two pointers.
 *   - Each iteration does an integer parse of up to 'len = floor(log2(n)) + 1' bits.
 *     => That parse is effectively O(1) since log2(n) <= 30 for n <= 1e9.
 *   - So the outer loop is O(L) (where L = s.length <= 1000).
 *   - Overall: O(L) or O(1000) => effectively O(1) under strict constraints, 
 *     but more precisely O(L * log(n)) in a non-strict sense.
 *
 * Space Complexity:
 *   - We store valid integers in an unordered_set<int>, possibly up to n elements 
 *     but limited by the number of distinct substrings. 
 *   - Worst-case: O(n) if n <= ~30,000 (the maximum distinct substrings for L=1000 & substring length ~30).
 *   - The temporary string 'temp' is at most log2(n)+1 bits => O(1).
 *
 * Explanation:
 *  1) We keep a sliding 'temp' substring no longer than 'len = floor(log2(n)) + 1' bits.
 *  2) Each time we add a bit or remove from front, we parse 'temp' as a binary integer.
 *  3) If it's in [1..n], insert into the set. 
 *  4) Finally, if the set size == n, return true, else false.
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 class Solution {
 public:
     bool queryString(string s, int n) {
         // Set of found integers [1..n] 
         unordered_set<int> st;
 
         // Maximum binary length needed to represent n
         int len = floor(log2(n)) + 1;
 
         // Two pointers tracking the substring "temp"
         int start = 0, end = 0;
         string temp = "";
 
         while (end < (int)s.size()) {
             // Expand temp until it has at most 'len' bits
             if ((int)temp.size() < len) {
                 temp.push_back(s[end]);
                 end++;
 
                 // Convert binary substring to int
                 int num = stoi(temp, nullptr, 2);
                 if (num >= 1 && num <= n) {
                     st.insert(num);
                 }
             } 
             else {
                 // If substring is already 'len' bits, remove front bit
                 temp = temp.substr(1);
                 start++;
 
                 // Parse again if not empty
                 if (!temp.empty()) {
                     int num = stoi(temp, nullptr, 2);
                     if (num >= 1 && num <= n) {
                         st.insert(num);
                     }
                 }
             }
         }
 
         // If we found exactly 'n' distinct valid integers, return true
         return (int)st.size() == n;
     }
 };
 
 // Optional main() for quick testing
 int main(){
     Solution sol;
     cout << boolalpha << sol.queryString("0110", 3) << endl; // true
     cout << boolalpha << sol.queryString("0110", 4) << endl; // false
     return 0;
 }