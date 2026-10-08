"""Run with: python -m unittest -v"""
import json
import random
import unittest

from vigenere import decrypt, encrypt, inverse_order, parse_packet, vigenere


class CipherTests(unittest.TestCase):
    def test_standard_known_vector(self):
        self.assertEqual(vigenere('ATTACKATDAWN', 'LEMON'), 'LXFOPVEFRNHR')
        self.assertEqual(vigenere('LXFOPVEFRNHR', 'LEMON', True), 'ATTACKATDAWN')

    def test_documented_permutation_example(self):
        rounds = [('column', [3, 1, 4, 2]), ('row', [2, 3, 1])]
        packet = encrypt('ATTACKATDAWN', 'LEMON', 4, rounds)
        self.assertEqual(json.loads(packet)['ciphertext'], 'EPFVHRRNFLOX')
        self.assertEqual(decrypt(packet, 'LEMON', rounds), 'ATTACKATDAWN')

    def test_case_and_punctuation(self):
        self.assertEqual(vigenere('Attack at dawn!', 'LEMON'), 'Lxfopv ef rnhr!')

    def test_non_self_inverse_order(self):
        self.assertEqual(inverse_order([2, 3, 1]), [3, 1, 2])

    def test_exact_round_trips(self):
        # Repeated column rounds detect failure to reverse round order.
        messages = ['', 'A', '  Hello, World!  ', '1234!?',
                    'Line 1\nLine 2\t ', 'Caf\u00e9 \u0645\u0631\u062d\u0628\u0627 \U0001f642', '\x00 X  ']
        for text in messages:
            rows = max(1, (len(text) + 3) // 4)
            rounds = [('column', [3, 1, 4, 2]),
                      ('row', list(range(rows, 0, -1))),
                      ('column', [2, 3, 1, 4])]
            with self.subTest(text=text):
                self.assertEqual(decrypt(encrypt(text, 'Key', 4, rounds),
                                         'Key', rounds), text)

    def test_random_round_trips(self):
        rng = random.Random(42)
        for _ in range(100):
            text = ''.join(rng.choice('Abz XY!?09\n\t\u00e9')
                           for _ in range(rng.randrange(70)))
            columns = rng.randint(1, 9)
            rows = max(1, (len(text) + columns - 1) // columns)
            rounds = []
            for kind in ['column', 'row', 'column', 'row']:
                order = list(range(1, (rows if kind == 'row' else columns) + 1))
                rng.shuffle(order)
                rounds.append((kind, order))
            self.assertEqual(decrypt(encrypt(text, 'Lemon', columns, rounds),
                                     'Lemon', rounds), text)

    def test_invalid_inputs(self):
        for key in ['', 'K3Y', '\u00e9']:
            with self.assertRaises(ValueError):
                vigenere('ABC', key)
        for order in [[1, 1, 3], [0, 1, 2], [1, 2], [True, 2, 3]]:
            with self.assertRaises(ValueError):
                encrypt('ABC', 'KEY', 3, [('column', order)])
        with self.assertRaises(ValueError):
            encrypt('ABC', 'KEY', 0, [('row', [1])])
        with self.assertRaises(ValueError):
            encrypt('ABC', 'KEY', 3, [])
        for packet in ['not JSON', '[]', '{}',
                       '{"version":1,"length":8,"columns":4,"ciphertext":"X"}']:
            with self.assertRaises(ValueError):
                parse_packet(packet)


if __name__ == '__main__':
    unittest.main()
