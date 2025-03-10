/**
 * Problem: 380. Insert Delete GetRandom O(1)
 *
 * Approach: Use an array (vector) + an unordered_map<int,int> storing each val -> index.
 *  - insert(val):
 *      * Check if val exists in map. If so, return false.
 *      * Otherwise, append val to end of vector and store {val -> last_index} in map.
 *  - remove(val):
 *      * Check if val exists in map. If not, return false.
 *      * Otherwise, let idx be the val's index. Swap the last element of the vector
 *        into this idx. Update map for that moved element. Pop from end of vector.
 *        Remove val from map.
 *  - getRandom():
 *      * Return a random element from the vector.
 *
 * Average Time Complexity: O(1) for insert, remove, getRandom
 * Worst-case Time Complexity: O(n) on rare rehash/resizing of container
 * Space Complexity: O(n)
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 class RandomizedSet {
 private:
     vector<int> nums;                     // array list of values
     unordered_map<int,int> dict;          // val -> index in nums
     mt19937 rng;                          // for random number generation
     uniform_int_distribution<int> dist;   // distribution will be updated
 
 public:
     /** Initialize your data structure here. */
     RandomizedSet() {
         ios_base::sync_with_stdio(false);
         cin.tie(nullptr);
         // Use random_device to seed mt19937
         random_device rd;
         rng = mt19937(rd());
     }
 
     /** Inserts a value to the set. Returns true if the set did not already contain the specified element. */
     bool insert(int val) {
         if (dict.find(val) != dict.end()) {
             return false;  // val already exists
         }
         nums.push_back(val);
         dict[val] = (int)nums.size() - 1;
         return true;
     }
 
     /** Removes a value from the set. Returns true if the set contained the specified element. */
     bool remove(int val) {
         auto it = dict.find(val);
         if (it == dict.end()) {
             return false;  // val not found
         }
         int idx = it->second;
         int lastVal = nums.back();
 
         // Move the last element to the 'idx' position
         nums[idx] = lastVal;
         dict[lastVal] = idx;
 
         // Remove the last element
         nums.pop_back();
         dict.erase(val);
         return true;
     }
 
     /** Get a random element from the set. */
     int getRandom() {
         // create or re-create distribution for current array size
         uniform_int_distribution<int> dist(0, (int)nums.size() - 1);
         int randomIndex = dist(rng);
         return nums[randomIndex];
     }
 };

 int main() {
    // Optionally, you can test your code here or do nothing:
    // e.g. RandomizedSet rs; rs.insert(1); ...
    return 0;
 }
 
 /** 
  * Example usage:
  * int main() {
  *     RandomizedSet randomizedSet;
  *     cout << boolalpha << randomizedSet.insert(1) << "\n";  // true
  *     cout << randomizedSet.remove(2) << "\n";               // false
  *     cout << randomizedSet.insert(2) << "\n";               // true
  *     cout << randomizedSet.getRandom() << "\n";             // could be 1 or 2
  *     cout << randomizedSet.remove(1) << "\n";               // true
  *     cout << randomizedSet.insert(2) << "\n";               // false (2 already in set)
  *     cout << randomizedSet.getRandom() << "\n";             // always 2 now
  *     return 0;
  * }
  */