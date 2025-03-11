#include <iostream>

class Solution {
public:
    double myPow(double x, int n) {
        long long N = n;
        if (N < 0) {
            x = 1.0 / x;
            N = -N;
        }

        double result = 1.0;
        while (N) {
            if (N % 2 == 1) {
                result *= x;
            }
            x *= x;
            N /= 2;
        }
        return result;
    }
};

// Driver Code
int main() {
    Solution solution;
    std::cout << solution.myPow(2.0, 10) << std::endl;  // Expected: 1024
    std::cout << solution.myPow(2.1, 3) << std::endl;   // Expected: 9.261
    std::cout << solution.myPow(2.0, -2) << std::endl;  // Expected: 0.25
    return 0;
}