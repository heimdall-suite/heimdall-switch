
# Usage: awk -v start=LINE -f extract_symbol.awk file
# Extracts a balanced-parenthesis S-expression block starting at line `start`.
BEGIN { depth = 0; started = 0 }
NR < start { next }
{
    line = $0
    n = length(line)
    for (i = 1; i <= n; i++) {
        c = substr(line, i, 1)
        if (c == "(") { depth++; started = 1 }
        else if (c == ")") { depth-- }
    }
    print line
    if (started && depth == 0) { exit }
}
