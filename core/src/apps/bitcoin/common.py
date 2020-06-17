from micropython import const

from trezor import wire
from trezor.crypto import bech32, bip32, der
from trezor.crypto.curve import secp256k1
from trezor.messages import InputScriptType, OutputScriptType
from trezor.utils import ensure

from apps.common.coininfo import CoinInfo

if False:
    from typing import Dict, List, Tuple
    from trezor.messages.TxInputType import EnumTypeInputScriptType
    from trezor.messages.TxOutputType import EnumTypeOutputScriptType

# Default signature hash type in Bitcoin which signs all inputs and all outputs of the transaction.
SIGHASH_ALL = const(0x01)

# supported witness version for bech32 addresses
_BECH32_WITVER = const(0x00)

MULTISIG_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDMULTISIG,
    InputScriptType.SPENDP2SHWITNESS,
    InputScriptType.SPENDWITNESS,
)
MULTISIG_OUTPUT_SCRIPT_TYPES = (
    OutputScriptType.PAYTOMULTISIG,
    OutputScriptType.PAYTOP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS,
)

CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES = {
    OutputScriptType.PAYTOADDRESS: InputScriptType.SPENDADDRESS,
    OutputScriptType.PAYTOMULTISIG: InputScriptType.SPENDMULTISIG,
    OutputScriptType.PAYTOP2SHWITNESS: InputScriptType.SPENDP2SHWITNESS,
    OutputScriptType.PAYTOWITNESS: InputScriptType.SPENDWITNESS,
}  # type: Dict[EnumTypeOutputScriptType, EnumTypeInputScriptType]
INTERNAL_INPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.values())
CHANGE_OUTPUT_SCRIPT_TYPES = tuple(CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES.keys())

SEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDP2SHWITNESS,
    InputScriptType.SPENDWITNESS,
)

NONSEGWIT_INPUT_SCRIPT_TYPES = (
    InputScriptType.SPENDADDRESS,
    InputScriptType.SPENDMULTISIG,
)


def ecdsa_sign(node: bip32.HDNode, digest: bytes) -> bytes:
    sig = secp256k1.sign(node.private_key(), digest)
    sigder = der.encode_seq((sig[1:33], sig[33:65]))
    return sigder


def ecdsa_verify(public_key: bytes, der_signature: bytes, digest: bytes) -> bool:
    seq, offset = der.decode_seq(der_signature, 0)
    if offset != len(der_signature) or len(seq) != 2:
        raise ValueError

    signature = bytearray(64)
    signature[32 - len(seq[0]) : 32] = seq[0]
    signature[64 - len(seq[1]) : 64] = seq[1]

    return secp256k1.verify(public_key, signature, digest)


def ecdsa_hash_pubkey(pubkey: bytes, coin: CoinInfo) -> bytes:
    if pubkey[0] == 0x04:
        ensure(len(pubkey) == 65)  # uncompressed format
    elif pubkey[0] == 0x00:
        ensure(len(pubkey) == 1)  # point at infinity
    else:
        ensure(len(pubkey) == 33)  # compresssed format

    return coin.script_hash(pubkey)


def encode_bech32_address(prefix: str, script: bytes) -> bytes:
    address = bech32.encode(prefix, _BECH32_WITVER, script)
    if address is None:
        raise wire.ProcessError("Invalid address")
    return address


def decode_bech32_address(prefix: str, address: str) -> bytes:
    witver, raw = bech32.decode(prefix, address)
    if witver != _BECH32_WITVER:
        raise wire.ProcessError("Invalid address witness program")
    return bytes(raw)


class SignatureVerifier:
    def __init__(
        self,
        public_keys: List[bytes],
        signatures: List[Tuple[bytes, int]],
        threshold: int = 1,
    ):
        self.public_keys = public_keys
        self.signatures = signatures
        self.threshold = threshold

    def check_sighhash_type(self, sighash_type: int) -> bool:
        for signature in self.signatures:
            if signature[1] != sighash_type:
                return False
        return True

    def verify(self, digest: bytes) -> None:
        if self.threshold != len(self.signatures):
            raise wire.DataError("Invalid signature")

        try:
            i = 0
            for signature in self.signatures:
                while not ecdsa_verify(self.public_keys[i], signature[0], digest):
                    i += 1
        except Exception:
            raise wire.DataError("Invalid signature")
