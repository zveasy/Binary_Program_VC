/**
 * Problem: 380. Insert Delete GetRandom O(1)
 *
 * Time Complexity (Average): O(1)
 * Worst-case expansions: O(n) at times
 * Space Complexity: O(n)
 *
 * Explanation:
 *  - We maintain a vector<int> to hold all current elements,
 *    plus an unordered_map<int,int> that maps values to their indices in the vector.
 *  - This data structure grows linearly with the number of elements, thus O(n) space.
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 class RandomizedSet {
 private:
     vector<int> nums;                    
     unordered_map<int,int> dict;         
     mt19937 rng;                         // random engine
 
 public:
     RandomizedSet() {
         ios_base::sync_with_stdio(false);
         cin.tie(nullptr);
         random_device rd;
         rng = mt19937(rd());
     }
 
     bool insert(int val) {
         if (dict.find(val) != dict.end()) {
             return false;  // val already present
         }
         nums.push_back(val);
         dict[val] = nums.size() - 1;
         return true;
     }
 
     bool remove(int val) {
         auto it = dict.find(val);
         if (it == dict.end()) {
             return false; // val not in set
         }
         int idx = it->second;
         int lastVal = nums.back();
 
         // move last element to idx
         nums[idx] = lastVal;
         dict[lastVal] = idx;
 
         nums.pop_back();
         dict.erase(val);
         return true;
     }
 
     int getRandom() {
         // pick a random index in [0..nums.size()-1]
         uniform_int_distribution<int> dist(0, (int)nums.size() - 1);
         int randomIndex = dist(rng);
         return nums[randomIndex];
     }
 };
 
 /**
  * int main() {
  *     RandomizedSet randomizedSet;
  *     randomizedSet.insert(1); 
  *     randomizedSet.remove(2); 
  *     randomizedSet.insert(2);
  *     cout << randomizedSet.getRandom() << endl;
  *     // ...
  *     return 0;
  * }
  */