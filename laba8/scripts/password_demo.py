import hashlib
import time

from app.security import hash_password, verify_password

PASSWORD = 'Passw0rd123'

print('=== 1. Plain text (NEVER do this) ===')
print(
    f'  stored in DB: {PASSWORD}  -> anyone who reads the DB knows the password'
)

print('\n=== 2. Fast hash: SHA-256 without salt ===')
print('  hash #1:', hashlib.sha256(PASSWORD.encode()).hexdigest())
print(
    '  hash #2:',
    hashlib.sha256(PASSWORD.encode()).hexdigest(),
    '(identical: rainbow tables work)',
)
started = time.perf_counter()
for _ in range(100_000):
    hashlib.sha256(PASSWORD.encode()).hexdigest()
print(
    f'  100000 guesses took {time.perf_counter() - started:.2f} s (a GPU does billions per second)'
)

print('\n=== 3. bcrypt: random salt + slow by design ===')
first = hash_password(PASSWORD)
second = hash_password(PASSWORD)
print('  hash #1:', first)
print('  hash #2:', second, '(different: random salt)')
print('  correct password:', verify_password(PASSWORD, first))
print('  wrong password  :', verify_password('WrongPass1', first))
started = time.perf_counter()
verify_password(PASSWORD, first)
one = time.perf_counter() - started
print(
    f'  one check takes {one * 1000:.0f} ms -> 100000 guesses would take about {one * 100000 / 3600:.1f} hours'
)
