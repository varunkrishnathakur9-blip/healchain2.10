import json
import glob
from pathlib import Path
from eth_utils import keccak, to_bytes, to_checksum_address


def encode_packed_uint256_bytes32_string_address(score_uint: int, nonce_hex: str, task_id: str, address: str) -> bytes:
    # uint256: big-endian unsigned 32-byte
    score_bytes = score_uint.to_bytes(32, byteorder='big')
    # bytes32: parse hex (with or without 0x), pad/truncate to 32
    nh = nonce_hex[2:] if nonce_hex.startswith('0x') else nonce_hex
    nonce_bytes = bytes.fromhex(nh)
    if len(nonce_bytes) != 32:
        raise ValueError('nonce must be 32 bytes')
    # string: task_id encoded as utf-8 (no length prefix)
    task_bytes = task_id.encode('utf-8')
    # address: 20 bytes (hex), lowercased; we'll accept 0x prefixed
    ah = address[2:] if address.startswith('0x') else address
    addr_bytes = bytes.fromhex(ah.rjust(40, '0'))

    return score_bytes + nonce_bytes + task_bytes + addr_bytes


def main():
    p = Path(__file__).parent.parent / 'reveal_exports'
    files = sorted(glob.glob(str(p / 'task_040__*.json')))
    if not files:
        print('No reveal files found for task_040')
        return

    for f in files:
        data = json.load(open(f, 'r', encoding='utf-8'))
        score = data.get('score')
        score_uint = data.get('scoreUint')
        nonce = data.get('nonce')
        commit = data.get('commit')
        taskid = data.get('taskID')
        miner = data.get('minerAddress')

        print(f'File: {Path(f).name}')
        print('  miner:', miner)
        print('  score:', score)
        print('  scoreUint:', score_uint)
        print('  nonce:', nonce)
        print('  commit:', commit)

        try:
            packed = encode_packed_uint256_bytes32_string_address(int(score_uint), nonce, taskid, miner)
            h = keccak(packed).hex()
            h_hex = '0x' + h
            ok = (h_hex.lower() == commit.lower())
            print('  recomputed:', h_hex, 'MATCH' if ok else 'MISMATCH')
        except Exception as e:
            print('  error verifying:', e)

        print()


if __name__ == '__main__':
    main()
