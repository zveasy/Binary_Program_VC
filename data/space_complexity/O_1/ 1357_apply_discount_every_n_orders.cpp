/**
 * Problem: 1357. Apply Discount Every n Orders
 * 
 * Time Complexity: O(1) per call
 *    - We store at most 200 products in a hash map; each getBill() operation loops through 
 *      up to 200 items, which is bounded => O(1) in problem constraints.
 * 
 * Space Complexity: O(1)
 *    - The hash map stores up to 200 entries; bounded => effectively constant space.
 *
 * Example usage:
 *   Cashier cashier(n, discount, products, prices);
 *   double bill = cashier.getBill(product, amount);
 *
 * Explanation:
 *   - 'tags' is an unordered_map<int,int> that stores productId -> price
 *   - 'cnt' tracks how many getBill() calls so far
 *   - Every nth call, a discount is applied: bill * ( (100 - discount) / 100.0 )
 */

 #include <bits/stdc++.h>
 using namespace std;
 
 class Cashier {
 public:
     // Map from product ID -> price
     unordered_map<int, int> tags;  
     int cnt;         // How many calls to getBill so far
     int mod;         // Every 'n' calls, discount is applied
     double pct;      // (100.0 - discount) / 100.0
 
     Cashier(int n, int discount, vector<int>& products, vector<int>& prices) 
     {
         cnt = 0;
         mod = n;
         // discount => e.g. 50 means 50% off => multiply total by 0.5
         pct = (100.0 - discount) / 100.0;
 
         // Build hash map for product -> price
         for (int i = 0; i < (int)products.size(); i++) {
             tags[products[i]] = prices[i];
         }
     }
 
     double getBill(vector<int> product, vector<int> amount) 
     {
         cnt++;  // increment the count of calls
         double total = 0.0;
 
         // compute subtotal
         for (int i = 0; i < (int)product.size(); i++) {
             int prodId = product[i];
             int qty = amount[i];
             total += tags[prodId] * qty;  // sum up item prices
         }
 
         // if this is the nth call, apply discount
         if (cnt % mod == 0) {
             total = total * pct;
         }
 
         return total;
     }
 };
 
 // Optional test main()
 int main() {
     // Example: n=3, discount=50, 7 products
     vector<int> prods = {1,2,3,4,5,6,7};
     vector<int> prices = {100,200,300,400,300,200,100};
     Cashier cashier(3, 50, prods, prices);
 
     // Example usage
     vector<int> p1 = {1, 2};
     vector<int> a1 = {1, 2};
     cout << cashier.getBill(p1, a1) << endl;  // 500.0 (first customer, no discount)
 
     return 0;
 }