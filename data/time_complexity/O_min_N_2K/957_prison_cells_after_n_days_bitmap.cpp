#include <vector>
#include <unordered_map>

using namespace std;

class Solution {
public:
    vector<int> prisonAfterNDays(vector<int>& cells, int N) {
        unordered_map<int, int> seen;
        bool isFastForwarded = false;

        int stateBitmap = encodeCells(cells);

        while (N > 0) {
            if (!isFastForwarded) {
                if (seen.find(stateBitmap) != seen.end()) {
                    // Cycle detected, fast forward
                    N %= seen[stateBitmap] - N;
                    isFastForwarded = true;
                } else {
                    seen[stateBitmap] = N;
                }
            }

            if (N > 0) {
                N--;
                stateBitmap = nextDay(stateBitmap);
            }
        }

        return decodeCells(stateBitmap);
    }

private:
    int encodeCells(vector<int>& cells) {
        int state = 0;
        for (int cell : cells) {
            state <<= 1;
            state |= cell;
        }
        return state;
    }

    vector<int> decodeCells(int state) {
        vector<int> cells(8, 0);
        for (int i = 7; i >= 0; i--) {
            cells[i] = (state & 1);
            state >>= 1;
        }
        return cells;
    }

    int nextDay(int state) {
        return (~(state << 1) ^ (state >> 1)) & 0x7E;
    }
};