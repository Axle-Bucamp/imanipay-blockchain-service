# /imanipay-blockchain-service/app/services/transactions.py
import logging
from algosdk.v2client import algod
from algosdk import transaction, account, mnemonic
from algosdk.transaction import ApplicationCallTxn, SuggestedParams, PaymentTxn, AssetTransferTxn, assign_group_id
from algosdk.encoding import encode_address, decode_address
from app.core.config import settings
from app.schemas import SendPaymentRequest, SendPaymentResponse
import json
import struct

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the transaction fee tiers.
TRANSACTION_FEES = [
    {"min": 0, "max": 100, "percentageCharge": 0.01, "flatCharge": 0},
    {"min": 100, "max": 1000, "percentageCharge": 0.005, "flatCharge": 0},
    {"min": 1000, "percentageCharge": 0, "flatCharge": 5},
]

class TransactionService:
    def __init__(self):
        self.algod_client = algod.AlgodClient(settings.algorand.algod_token, settings.algorand.algod_address)
        self.admin_wallet_address = settings.algorand.master_wallet_mnemonic  # Use master wallet as admin
        self.deployer_private_key = settings.algorand.hot_wallet_mnemonic  # Use hot wallet as deployer
        if not self.deployer_private_key:
            raise ValueError("DEPLOYER_PRIVATE_KEY is not set. Cannot send fees.")
        # Convert mnemonic to private key if needed
        if self.deployer_private_key and len(self.deployer_private_key.split()) > 1:
            # It's a mnemonic phrase
            self.sender_account = account.Account.from_mnemonic(self.deployer_private_key)
        else:
            # It's already a private key
            self.sender_account = account.Account.from_private_key(self.deployer_private_key)
        self.app_id = settings.algorand.platform_token_id # Use platform token ID as app ID
        if not self.app_id:
            raise ValueError("PAYMENT_CONTRACT_APP_ID is not set.  You must deploy the contract.")

    def calculate_transaction_fee(self, amount: float) -> float:
        """Calculates the transaction fee based on the amount."""
        for tier in TRANSACTION_FEES:
            if tier.get("max") is None and amount >= tier["min"]:
                return amount * tier.get("percentageCharge", 0) + tier.get("flatCharge", 0)
            if tier.get("min", 0) <= amount <= tier.get("max", float('inf')):
                return amount * tier.get("percentageCharge", 0) + tier.get("flatCharge", 0)
        return 0  # Default to no fee

    async def send_payment(self, payment_in: SendPaymentRequest) -> SendPaymentResponse:
        """
        Calculates the transaction details and sends the transaction to the Algorand blockchain
        using a smart contract.
        """
        algod_client = self.algod_client
        sender = self.sender_account.address
        sender_private_key = self.deployer_private_key  # Use the deployer key
        app_id = self.app_id

        # 1. Calculate the transaction fee.
        fee_amount = self.calculate_transaction_fee(payment_in.amount)
        total_amount_to_send = payment_in.amount + fee_amount # Sender pays amount + fee
        actual_payment_amount = payment_in.amount  # Contract sends the amount

        print(f"Calculated fee: {fee_amount}, Total amount from sender: {total_amount_to_send}, Amount to receiver: {actual_payment_amount}")

        # 2. Get transaction parameters.
        params: SuggestedParams = algod_client.suggested_params()

        # 3. Prepare the smart contract call.
        app_call_txn = ApplicationCallTxn(
            sender=sender,
            sp=params,
            index=app_id,  # The Application ID of the deployed contract
            on_complete=transaction.OnComplete.NoOpOC,  # NoOp call
            app_args=[
                encode_address(payment_in.receiver_wallet_address),  # Receiver address (encoded)
                bytearray(struct.pack("f", actual_payment_amount)),  # Amount (as bytes)
                bytearray(struct.pack("f",fee_amount)), # Fee amount (as bytes)
            ],
        )

        # 4. Create a transaction that pays the smart contract, including the fee.
        payment_txn = PaymentTxn(
            sender=sender,
            sp=params,
            receiver=sender,  # Send to yourself (contract address will handle it)
            amt=total_amount_to_send, # Sender pays amount + fee
        )
        # Group the transactions
        assign_group_id([app_call_txn, payment_txn])


        # 5. Sign the transactions
        signed_app_call = app_call_txn.sign(self.sender_account.private_key)
        signed_payment = payment_txn.sign(self.sender_account.private_key)
        # signed_txn = app_call_txn.sign(sender_private_key)  # Sign the transaction

        # 6. Send the transactions to the blockchain
        try:
            txid = algod_client.send_transactions([signed_app_call, signed_payment]) # Send the group
            logger.info(f"Transaction group sent with ID: {txid}")
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            raise  # Re-raise the exception to be handled by FastAPI

        # 7. Return the transaction data. Include the txid.
        return SendPaymentResponse(
            sender_wallet_address=sender,
            receiver_wallet_address=payment_in.receiver_wallet_address,
            amount=payment_in.amount,
            actual_payment_amount=actual_payment_amount,
            fee_amount=fee_amount,
            params={
                "fee": params.fee,
                "first": params.first,
                "last": params.last,
                "ghash": params.genesis_hash if hasattr(params, 'genesis_hash') else None,
                "genesisID": params.genesis_id if hasattr(params, 'genesis_id') else None,
                "genesisHash": params.genesis_hash if hasattr(params, 'genesis_hash') else None,
            },
            asset_id=payment_in.asset_id,
            admin_wallet_address=self.admin_wallet_address,
            txid=txid,  # Include the transaction ID in the response
        )
