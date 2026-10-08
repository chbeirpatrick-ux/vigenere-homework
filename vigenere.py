"""Vigenere substitution followed by reversible row/column permutations.

Run: python vigenere.py
Only Python's standard library is required. Permutation positions are 1-based.
"""

import json


def validate_keyword(keyword):
    if not keyword or any(not ('A' <= c <= 'Z' or 'a' <= c <= 'z')
                          for c in keyword):
        raise ValueError('Keyword must contain only English letters A-Z.')
    return keyword.upper()


def vigenere(text, keyword, decrypt=False):
    """Shift ASCII letters; preserve case and all other characters exactly.

    Spaces, punctuation and non-ASCII characters do not consume key letters.
    """
    keyword = validate_keyword(keyword)
    result = []
    key_index = 0
    for char in text:
        if 'A' <= char <= 'Z':
            base = ord('A')
        elif 'a' <= char <= 'z':
            base = ord('a')
        else:
            result.append(char)
            continue
        shift = ord(keyword[key_index % len(keyword)]) - ord('A')
        if decrypt:
            shift = -shift
        result.append(chr(base + (ord(char) - base + shift) % 26))
        key_index += 1
    return ''.join(result)


def validate_order(order, size):
    """A permutation must contain every position exactly once."""
    if (any(type(x) is not int for x in order)
            or sorted(order) != list(range(1, size + 1))):
        raise ValueError(f'Order must contain every integer from 1 to {size} once.')


def inverse_order(order):
    """For example, the inverse of [3, 1, 2] is [2, 3, 1]."""
    validate_order(order, len(order))
    inverse = [0] * len(order)
    for new_position, old_position in enumerate(order, start=1):
        inverse[old_position - 1] = new_position
    return inverse


def permute(grid, kind, order, undo=False):
    """Output position i takes input position order[i] (using 1-based keys)."""
    if kind not in ('row', 'column'):
        raise ValueError('Round type must be row or column.')
    size = len(grid) if kind == 'row' else len(grid[0])
    validate_order(order, size)
    if undo:
        order = inverse_order(order)
    if kind == 'row':
        return [grid[position - 1][:] for position in order]
    return [[row[position - 1] for position in order] for row in grid]


def flatten(grid):
    return ''.join(''.join(row) for row in grid)


def emit(trace, label, value):
    if trace is not None:
        trace(label, value)


def encrypt(plaintext, keyword, columns, rounds, trace=None):
    """Return a JSON ciphertext packet; the keys are supplied separately."""
    if type(columns) is not int or columns < 1:
        raise ValueError('Column count must be a positive integer.')
    if not rounds:
        raise ValueError('Use at least one permutation round.')
    substituted = vigenere(plaintext, keyword)
    emit(trace, 'After Vigenere', substituted)
    # Store original length so genuine trailing spaces are never stripped.
    rows = max(1, (len(substituted) + columns - 1) // columns)
    padded = substituted.ljust(rows * columns)
    grid = [list(padded[i:i + columns])
            for i in range(0, len(padded), columns)]
    emit(trace, 'Padded grid', grid)
    for number, (kind, order) in enumerate(rounds, start=1):
        grid = permute(grid, kind, order)
        emit(trace, f'After round {number} ({kind})', grid)
    packet = {'version': 1, 'length': len(plaintext),
              'columns': columns, 'ciphertext': flatten(grid)}
    # JSON escaping keeps newlines and spaces safe in one copyable line.
    return json.dumps(packet, ensure_ascii=True, separators=(',', ':'))


def parse_packet(packet):
    """Validate the format and grid dimensions before using a pasted packet."""
    try:
        data = json.loads(packet)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError('Paste the complete JSON ciphertext packet.') from exc
    if not isinstance(data, dict):
        raise ValueError('Ciphertext packet must be a JSON object.')
    if type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Unsupported packet version.')
    length, columns = data.get('length'), data.get('columns')
    ciphertext = data.get('ciphertext')
    if (type(length) is not int or length < 0
            or type(columns) is not int or columns < 1
            or not isinstance(ciphertext, str)):
        raise ValueError('Packet has invalid length, columns, or ciphertext.')
    rows = max(1, (length + columns - 1) // columns)
    if len(ciphertext) != rows * columns:
        raise ValueError('Ciphertext size does not match the packet dimensions.')
    return data


def decrypt(packet, keyword, rounds, trace=None):
    """Undo rounds in reverse order, remove padding, then undo substitution."""
    validate_keyword(keyword)
    if not rounds:
        raise ValueError('Use the same permutation rounds as encryption.')
    data = parse_packet(packet)
    columns = data['columns']
    ciphertext = data['ciphertext']
    grid = [list(ciphertext[i:i + columns])
            for i in range(0, len(ciphertext), columns)]
    for index in range(len(rounds) - 1, -1, -1):
        kind, order = rounds[index]
        grid = permute(grid, kind, order, undo=True)
        emit(trace, f'Undo round {index + 1} ({kind})', grid)
    substituted = flatten(grid)[:data['length']]
    emit(trace, 'After removing padding', substituted)
    plaintext = vigenere(substituted, keyword, decrypt=True)
    emit(trace, 'After Vigenere decryption', plaintext)
    return plaintext


def show_trace(label, value):
    print(f'\n{label}:')
    if isinstance(value, list):
        for row in value:
            print('  ' + repr(''.join(row)))
    else:
        print('  ' + repr(value))


def read_positive(prompt):
    while True:
        try:
            value = int(input(prompt))
            if value < 1:
                raise ValueError
            return value
        except ValueError:
            print('Please enter a positive integer.')


def read_keyword():
    while True:
        try:
            return validate_keyword(input('Secret keyword (A-Z): '))
        except ValueError as exc:
            print(exc)


def read_rounds(rows, columns):
    print(f'Grid: {rows} rows x {columns} columns.')
    print('Enter rounds in ENCRYPTION order, even when decrypting.')
    count = read_positive('Number of permutation rounds: ')
    rounds = []
    for number in range(1, count + 1):
        while True:
            kind = input(f'Round {number} type (row/column): ').strip().lower()
            if kind in ('row', 'column'):
                break
            print('Enter row or column.')
        size = rows if kind == 'row' else columns
        while True:
            try:
                order = [int(x) for x in input(
                    f'Order (1 through {size}, separated by spaces): ').split()]
                validate_order(order, size)
                break
            except ValueError as exc:
                print(f'Invalid permutation: {exc}')
        rounds.append((kind, order))
    return rounds


def main():
    print('VIGENERE CIPHER + ROW/COLUMN PERMUTATIONS')
    print('Preserves case, spaces and punctuation.')
    while True:
        mode = input('\nMode (E=encrypt, D=decrypt, Q=quit): ').strip().upper()
        if mode == 'Q':
            print('Goodbye!')
            return
        if mode not in ('E', 'D'):
            print('Please choose E, D, or Q.')
            continue
        try:
            if mode == 'E':
                text = input('Plaintext: ')  # Do not strip real spaces.
                keyword = read_keyword()
                columns = read_positive('Number of columns: ')
                rows = max(1, (len(text) + columns - 1) // columns)
                rounds = read_rounds(rows, columns)
                packet = encrypt(text, keyword, columns, rounds, show_trace)
                print('\nCOPY THIS ENTIRE CIPHERTEXT PACKET:')
                print(packet)
                print('Keep the keyword and permutation orders for decryption.')
            else:
                packet = input('Paste ciphertext packet: ')
                data = parse_packet(packet)
                keyword = read_keyword()
                rounds = read_rounds(len(data['ciphertext']) // data['columns'],
                                     data['columns'])
                text = decrypt(packet, keyword, rounds, show_trace)
                print('\nRECOVERED PLAINTEXT:')
                print(text)
                print('Exact representation:', repr(text))
        except ValueError as exc:
            print(f'Error: {exc}')


if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print('\nGoodbye!')
