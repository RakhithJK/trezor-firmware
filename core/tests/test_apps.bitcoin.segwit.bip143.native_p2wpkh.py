from common import *

from apps.bitcoin.scripts import output_derive_script
from apps.bitcoin.sign_tx.bitcoin import Bitcoin
from apps.bitcoin.writers import get_tx_hash
from apps.common import coins
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType
from trezor.messages.TxOutputBinType import TxOutputBinType
from trezor.messages import InputScriptType
from trezor.messages import OutputScriptType
from trezor.crypto import bip39


class TestSegwitBip143NativeP2WPKH(unittest.TestCase):
    # pylint: disable=C0301

    tx = SignTx(coin_name='Bitcoin', version=1, lock_time=0x00000011, inputs_count=2, outputs_count=2)
    inp1 = TxInputType(address_n=[0],
                       # Trezor expects hash in reversed format
                       prev_hash=unhexlify('9f96ade4b41d5433f4eda31e1738ec2b36f6e7d1420d94a6af99801a88f7f7ff'),
                       prev_index=0,
                       amount=625000000,  # 6.25 btc
                       script_type=InputScriptType.SPENDWITNESS,
                       multisig=None,
                       sequence=0xffffffee)
    inp2 = TxInputType(address_n=[1],
                       # Trezor expects hash in reversed format
                       prev_hash=unhexlify('8ac60eb9575db5b2d987e29f301b5b819ea83a5c6579d282d189cc04b8e151ef'),
                       prev_index=1,
                       multisig=None,
                       amount=600000000,  # 6 btc
                       script_type=InputScriptType.SPENDWITNESS,
                       sequence=0xffffffff)
    out1 = TxOutputType(address='1Cu32FVupVCgHkMMRJdYJugxwo2Aprgk7H',  # derived
                        amount=0x0000000006b22c20,
                        script_type=OutputScriptType.PAYTOADDRESS,
                        multisig=None,
                        address_n=[])
    out2 = TxOutputType(address='16TZ8J6Q5iZKBWizWzFAYnrsaox5Z5aBRV',  # derived
                        amount=0x000000000d519390,
                        script_type=OutputScriptType.PAYTOADDRESS,
                        multisig=None,
                        address_n=[])

    def test_prevouts(self):
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bitcoin(self.tx, None, coin)
        bip143.hash143_add_input(self.inp1)
        bip143.hash143_add_input(self.inp2)
        prevouts_hash = get_tx_hash(bip143.h_prevouts, double=coin.sign_hash_double)
        self.assertEqual(hexlify(prevouts_hash), b'96b827c8483d4e9b96712b6713a7b68d6e8003a781feba36c31143470b4efd37')

    def test_sequence(self):
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bitcoin(self.tx, None, coin)
        bip143.hash143_add_input(self.inp1)
        bip143.hash143_add_input(self.inp2)
        sequence_hash = get_tx_hash(bip143.h_sequence, double=coin.sign_hash_double)
        self.assertEqual(hexlify(sequence_hash), b'52b0a642eea2fb7ae638c36f6252b6750293dbe574a806984b8e4d8548339a3b')

    def test_outputs(self):

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bitcoin(self.tx, None, coin)

        for txo in [self.out1, self.out2]:
            txo_bin = TxOutputBinType()
            txo_bin.amount = txo.amount
            script_pubkey = output_derive_script(txo, coin)
            bip143.hash143_add_output(txo_bin, script_pubkey)

        outputs_hash = get_tx_hash(bip143.h_outputs, double=coin.sign_hash_double)
        self.assertEqual(hexlify(outputs_hash), b'863ef3e1a92afbfdb97f31ad0fc7683ee943e9abcf2501590ff8f6551f47e5e5')

    def test_preimage_testdata(self):

        seed = bip39.seed('alcohol woman abuse must during monitor noble actual mixed trade anger aisle', '')
        coin = coins.by_name(self.tx.coin_name)
        bip143 = Bitcoin(self.tx, None, coin)
        bip143.hash143_add_input(self.inp1)
        bip143.hash143_add_input(self.inp2)

        for txo in [self.out1, self.out2]:
            txo_bin = TxOutputBinType()
            txo_bin.amount = txo.amount
            script_pubkey = output_derive_script(txo, coin)
            bip143.hash143_add_output(txo_bin, script_pubkey)

        # test data public key hash
        # only for input 2 - input 1 is not segwit
        result = bip143.hash143_preimage_hash(self.inp2, unhexlify('1d0f172a0ecb48aee1be1f2687d2963ae33f71a1'))
        self.assertEqual(hexlify(result), b'c37af31116d1b27caf68aae9e3ac82f1477929014d5b917657d0eb49478cb670')


if __name__ == '__main__':
    unittest.main()