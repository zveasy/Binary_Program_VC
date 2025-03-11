#include <iostream>

class Solution {
public:
    double binaryExp(double x, long long n) {
        if (n == 0) {
            return 1.0;
        }

        // Handle case where n is negative
        if (n < 0) {
            x = 1.0 / x;
            n = -n;
        }

        double result = 1.0;
        while (n > 0) {
            if (n % 2 == 1) {  // If n is odd, multiply result with x
                result *= x;
                n -= 1;
            }
            x *= x;  // Square x
            n /= 2;  // Reduce n by half
        }

        return result;
    }

    double myPow(double x, int n) {
        return binaryExp(x, static_cast<long long>(n));
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