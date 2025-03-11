#include <bits/stdc++.h>
using namespace std;

/**
 * This solution focuses on the SPACE complexity aspect (O(2^K)).
 * We store each state in a hash map to detect cycles.
 * The maximum possible states = 2^8 = 256, so in the worst case,
 * we store 256 entries in the map => O(2^K) space.
 */

class Solution {
public:
    vector<int> prisonAfterNDays(vector<int>& cells, int N) {
        // Map: state -> step index
        unordered_map<int,int> seen;  
        bool isFastForwarded = false;

        // Convert current cells to a bit-based state
        int stateBitmap = encode(cells);

        while (N > 0) {
            // If we haven't found a cycle yet
            if (!isFastForwarded) {
                // If this state is seen before, cycle is found
                if (seen.count(stateBitmap)) {
                    // cycle length = (previous step idx) - (current step idx)
                    // "seen[stateBitmap]" = last time we saw this state
                    N %= seen[stateBitmap] - N; 
                    isFastForwarded = true;
                } else {
                    // record the step index for the current state
                    seen[stateBitmap] = N;
                }
            }
            // If we still have steps to simulate
            if (N > 0) {
                N--;
                // compute the next state
                stateBitmap = nextDay(stateBitmap);
            }
        }

        // Decode the final bit-based state back to cells
        return decode(stateBitmap);
    }

private:
    // Convert cells array [0/1,...] into a single integer (bitmask)
    int encode(const vector<int>& cells) {
        int state = 0;
        for (int c : cells) {
            state <<= 1;
            state |= c;
        }
        return state;
    }

    // Convert integer bitmask back to cells array
    vector<int> decode(int state) {
        vector<int> cells(8, 0);
        for (int i = 7; i >= 0; i--) {
            cells[i] = state & 1;
            state >>= 1;
        }
        return cells;
    }

    // Transition to the next day's state (using bitwise ops)
    int nextDay(int state) {
        // The rule: (left == right) => 1, else 0, ignoring the first & last
        // Implementation with bitwise: ~(state<<1) ^ (state>>1)
        // Then mask out the outer bits with 0x7E = b01111110
        return (~(state << 1) ^ (state >> 1)) & 0x7E;
    }
};

// Optional main() for testing
int main(){
    vector<int> cells = {0,1,0,1,1,0,0,1};
    int N = 7;
    Solution sol;
    vector<int> result = sol.prisonAfterNDays(cells, N);

    cout << "Result after 7 days: ";
    for(int r : result) cout << r << " ";
    cout << endl;

    return 0;
}