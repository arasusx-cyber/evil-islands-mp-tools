// SPDX-License-Identifier: GPL-3.0-or-later
// Independent decoder/parser supplied with the previous editor.
#include <algorithm>
#include <iostream>
#include "upstream-mp_file.hpp"
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    mp::Character c;
    std::string error;
    if (!mp::Load(argv[1], c, error)) {
        std::cerr << error << '\n';
        return 1;
    }
    const auto raw = mp::Serialize(c);
    std::ofstream output(argv[2], std::ios::binary);
    output.write(reinterpret_cast<const char*>(raw.data()), raw.size());
    if (!output) return 1;
    std::cout << "PASS: C++ reference decoder + parser + exact serialization; gold=" << mp::Money(c)
              << "; xp=" << mp::GetF(c.members[0].stats, 4) << "; raw=" << raw.size() << '\n';
}
