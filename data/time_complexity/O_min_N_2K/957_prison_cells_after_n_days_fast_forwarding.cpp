#include <vector>
#include <unordered_map>

using namespace std;

class Solution {
public:
    vector<int> prisonAfterNDays(vector<int>& cells, int N) {
        unordered_map<int, int> seen;
        bool isFastForwarded = false;

        int stateBitmap = cellsToBitmap(cells);

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

        return bitmapToCells(stateBitmap);
    }

private:
    int cellsToBitmap(vector<int>& cells) {
        int stateBitmap = 0;
        for (int cell : cells) {
            stateBitmap <<= 1;
            stateBitmap |= cell;
        }
        return stateBitmap;
    }

    vector<int> bitmapToCells(int stateBitmap) {
        vector<int> cells(8, 0);
        for (int i = 7; i >= 0; i--) {
            cells[i] = stateBitmap & 1;
            stateBitmap >>= 1;
        }
        return cells;
    }

    int nextDay(int stateBitmap) {
        return (~(stateBitmap << 1) ^ (stateBitmap >> 1)) & 0x7E;
    }
};