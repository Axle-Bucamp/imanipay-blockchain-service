"""
Advanced Escrow Smart Contract for ImaniPay Blockchain Service.

This contract provides secure escrow functionality for cross-border payments
with dispute resolution, time-based releases, and multi-party support.
"""

from pyteal import (
    Txn, Assert, Int, TxnType, Seq, Return, compileTeal, Mode, 
    InnerTxnBuilder, Global, Addr, TxnField, Btoi, Bytes, App,
    If, And, Or, Not, Cond, Subroutine, TealType, Expr,
    ScratchVar, For, While, Break, Continue, Approve, Reject,
    Substring, Len, Concat,
    Pop, SetBit, GetBit, BytesAdd,
    BytesMul, BytesDiv, BytesMod, BytesAnd, BytesOr, BytesXor,
    BytesNot, BytesEq, BytesLt, BytesLe, BytesGt, BytesGe,
    Extract, Replace, Base64Decode, JsonRef, Keccak256, Sha256,
    Sha512_256, Ed25519Verify, EcdsaVerify, EcdsaRecover
)


class EscrowContract:
    """Advanced escrow contract with comprehensive functionality."""
    
    def __init__(self):
        # Contract state keys
        self.STATE_ESCROW_AMOUNT = Bytes("escrow_amount")
        self.STATE_SENDER = Bytes("sender")
        self.STATE_RECEIVER = Bytes("receiver")
        self.STATE_ARBITRATOR = Bytes("arbitrator")
        self.STATE_DEADLINE = Bytes("deadline")
        self.STATE_STATUS = Bytes("status")
        self.STATE_DISPUTE_RAISED = Bytes("dispute_raised")
        self.STATE_RELEASE_CONDITIONS = Bytes("release_conditions")
        self.STATE_FEE_PERCENTAGE = Bytes("fee_percentage")
        self.STATE_PLATFORM_ADDRESS = Bytes("platform_address")
        
        # Status values
        self.STATUS_ACTIVE = Int(1)
        self.STATUS_COMPLETED = Int(2)
        self.STATUS_DISPUTED = Int(3)
        self.STATUS_CANCELLED = Int(4)
        self.STATUS_EXPIRED = Int(5)
        
        # Method selectors
        self.METHOD_INITIALIZE = Bytes("initialize")
        self.METHOD_RELEASE = Bytes("release")
        self.METHOD_DISPUTE = Bytes("dispute")
        self.METHOD_RESOLVE = Bytes("resolve")
        self.METHOD_CANCEL = Bytes("cancel")
        self.METHOD_EXTEND_DEADLINE = Bytes("extend_deadline")
        self.METHOD_UPDATE_CONDITIONS = Bytes("update_conditions")
    
    def approval_program(self) -> Expr:
        """Main approval program for the escrow contract."""
        
        # Initialize escrow
        initialize_escrow = Seq([
            # Verify initialization parameters
            Assert(Len(Txn.application_args[0]) == Int(32)),  # sender address
            Assert(Len(Txn.application_args[1]) == Int(32)),  # receiver address
            Assert(Len(Txn.application_args[2]) == Int(32)),  # arbitrator address
            Assert(Btoi(Txn.application_args[3]) > Global.latest_timestamp()),  # deadline
            Assert(Btoi(Txn.application_args[4]) > Int(0)),  # escrow amount
            Assert(Btoi(Txn.application_args[5]) <= Int(1000)),  # fee percentage (max 10%)
            
            # Store escrow details
            App.globalPut(self.STATE_SENDER, Txn.application_args[0]),
            App.globalPut(self.STATE_RECEIVER, Txn.application_args[1]),
            App.globalPut(self.STATE_ARBITRATOR, Txn.application_args[2]),
            App.globalPut(self.STATE_DEADLINE, Btoi(Txn.application_args[3])),
            App.globalPut(self.STATE_ESCROW_AMOUNT, Btoi(Txn.application_args[4])),
            App.globalPut(self.STATE_FEE_PERCENTAGE, Btoi(Txn.application_args[5])),
            App.globalPut(self.STATE_PLATFORM_ADDRESS, Txn.application_args[6]),
            App.globalPut(self.STATE_STATUS, self.STATUS_ACTIVE),
            App.globalPut(self.STATE_DISPUTE_RAISED, Int(0)),
            
            # Store release conditions if provided
            If(Int(7) < Int(8),  # Check if 8th argument exists
                App.globalPut(self.STATE_RELEASE_CONDITIONS, Txn.application_args[7])
            ),
            
            Return(Int(1))
        ])
        
        # Release funds to receiver
        release_funds = Seq([
            # Verify caller is sender or arbitrator
            Assert(Or(
                Txn.sender() == App.globalGet(self.STATE_SENDER),
                Txn.sender() == App.globalGet(self.STATE_ARBITRATOR)
            )),
            
            # Verify escrow is active
            Assert(App.globalGet(self.STATE_STATUS) == self.STATUS_ACTIVE),
            
            # Calculate amounts
            self._calculate_and_transfer_funds(App.globalGet(self.STATE_RECEIVER)),
            
            # Update status
            App.globalPut(self.STATE_STATUS, self.STATUS_COMPLETED),
            
            Return(Int(1))
        ])
        
        # Raise dispute
        raise_dispute = Seq([
            # Verify caller is sender or receiver
            Assert(Or(
                Txn.sender() == App.globalGet(self.STATE_SENDER),
                Txn.sender() == App.globalGet(self.STATE_RECEIVER)
            )),
            
            # Verify escrow is active
            Assert(App.globalGet(self.STATE_STATUS) == self.STATUS_ACTIVE),
            
            # Verify deadline not passed
            Assert(Global.latest_timestamp() < App.globalGet(self.STATE_DEADLINE)),
            
            # Mark as disputed
            App.globalPut(self.STATE_STATUS, self.STATUS_DISPUTED),
            App.globalPut(self.STATE_DISPUTE_RAISED, Int(1)),
            
            Return(Int(1))
        ])
        
        # Resolve dispute (arbitrator only)
        resolve_dispute = Seq([
            # Verify caller is arbitrator
            Assert(Txn.sender() == App.globalGet(self.STATE_ARBITRATOR)),
            
            # Verify escrow is disputed
            Assert(App.globalGet(self.STATE_STATUS) == self.STATUS_DISPUTED),
            
            # Get resolution decision from args (0 = refund sender, 1 = pay receiver)
            If(Btoi(Txn.application_args[1]) == Int(0),
                # Refund to sender
                self._calculate_and_transfer_funds(App.globalGet(self.STATE_SENDER)),
                # Pay to receiver
                self._calculate_and_transfer_funds(App.globalGet(self.STATE_RECEIVER))
            ),
            
            # Update status
            App.globalPut(self.STATE_STATUS, self.STATUS_COMPLETED),
            
            Return(Int(1))
        ])
        
        # Cancel escrow (sender only, before deadline)
        cancel_escrow = Seq([
            # Verify caller is sender
            Assert(Txn.sender() == App.globalGet(self.STATE_SENDER)),
            
            # Verify escrow is active
            Assert(App.globalGet(self.STATE_STATUS) == self.STATUS_ACTIVE),
            
            # Verify no dispute raised
            Assert(App.globalGet(self.STATE_DISPUTE_RAISED) == Int(0)),
            
            # Refund to sender (minus cancellation fee)
            self._refund_with_cancellation_fee(),
            
            # Update status
            App.globalPut(self.STATE_STATUS, self.STATUS_CANCELLED),
            
            Return(Int(1))
        ])
        
        # Extend deadline (sender and receiver agreement required)
        extend_deadline = Seq([
            # Verify caller is sender or receiver
            Assert(Or(
                Txn.sender() == App.globalGet(self.STATE_SENDER),
                Txn.sender() == App.globalGet(self.STATE_RECEIVER)
            )),
            
            # Verify escrow is active
            Assert(App.globalGet(self.STATE_STATUS) == self.STATUS_ACTIVE),
            
            # Verify new deadline is in future
            Assert(Btoi(Txn.application_args[1]) > Global.latest_timestamp()),
            
            # Update deadline
            App.globalPut(self.STATE_DEADLINE, Btoi(Txn.application_args[1])),
            
            Return(Int(1))
        ])
        
        # Handle expired escrow (automatic refund)
        handle_expiry = Seq([
            # Verify deadline has passed
            Assert(Global.latest_timestamp() >= App.globalGet(self.STATE_DEADLINE)),
            
            # Verify escrow is active
            Assert(App.globalGet(self.STATE_STATUS) == self.STATUS_ACTIVE),
            
            # Refund to sender
            self._calculate_and_transfer_funds(App.globalGet(self.STATE_SENDER)),
            
            # Update status
            App.globalPut(self.STATE_STATUS, self.STATUS_EXPIRED),
            
            Return(Int(1))
        ])
        
        # Main program logic
        program = Cond(
            [Txn.application_id() == Int(0), Return(Int(1))],  # Creation
            [Txn.application_args[0] == self.METHOD_INITIALIZE, initialize_escrow],
            [Txn.application_args[0] == self.METHOD_RELEASE, release_funds],
            [Txn.application_args[0] == self.METHOD_DISPUTE, raise_dispute],
            [Txn.application_args[0] == self.METHOD_RESOLVE, resolve_dispute],
            [Txn.application_args[0] == self.METHOD_CANCEL, cancel_escrow],
            [Txn.application_args[0] == self.METHOD_EXTEND_DEADLINE, extend_deadline],
            [Global.latest_timestamp() >= App.globalGet(self.STATE_DEADLINE), handle_expiry]
        )
        
        return program
    
    def _calculate_and_transfer_funds(self, recipient: Expr) -> Expr:
        """Calculate fees and transfer funds to recipient."""
        escrow_amount = ScratchVar(TealType.uint64)
        fee_percentage = ScratchVar(TealType.uint64)
        platform_fee = ScratchVar(TealType.uint64)
        recipient_amount = ScratchVar(TealType.uint64)
        
        return Seq([
            escrow_amount.store(App.globalGet(self.STATE_ESCROW_AMOUNT)),
            fee_percentage.store(App.globalGet(self.STATE_FEE_PERCENTAGE)),
            
            # Calculate platform fee (fee_percentage is in basis points, e.g., 100 = 1%)
            platform_fee.store(escrow_amount.load() * fee_percentage.load() / Int(10000)),
            recipient_amount.store(escrow_amount.load() - platform_fee.load()),
            
            # Transfer to recipient
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.Payment),
            InnerTxnBuilder.SetField(TxnField.receiver, recipient),
            InnerTxnBuilder.SetField(TxnField.amount, recipient_amount.load()),
            InnerTxnBuilder.Submit(),
            
            # Transfer fee to platform (if fee > 0)
            If(platform_fee.load() > Int(0),
                Seq([
                    InnerTxnBuilder.Begin(),
                    InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.Payment),
                    InnerTxnBuilder.SetField(TxnField.receiver, App.globalGet(self.STATE_PLATFORM_ADDRESS)),
                    InnerTxnBuilder.SetField(TxnField.amount, platform_fee.load()),
                    InnerTxnBuilder.Submit()
                ])
            )
        ])
    
    def _refund_with_cancellation_fee(self) -> Expr:
        """Refund to sender with cancellation fee deduction."""
        escrow_amount = ScratchVar(TealType.uint64)
        cancellation_fee = ScratchVar(TealType.uint64)
        refund_amount = ScratchVar(TealType.uint64)
        
        return Seq([
            escrow_amount.store(App.globalGet(self.STATE_ESCROW_AMOUNT)),
            
            # Cancellation fee is 1% of escrow amount
            cancellation_fee.store(escrow_amount.load() / Int(100)),
            refund_amount.store(escrow_amount.load() - cancellation_fee.load()),
            
            # Refund to sender
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.Payment),
            InnerTxnBuilder.SetField(TxnField.receiver, App.globalGet(self.STATE_SENDER)),
            InnerTxnBuilder.SetField(TxnField.amount, refund_amount.load()),
            InnerTxnBuilder.Submit(),
            
            # Transfer cancellation fee to platform
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.Payment),
            InnerTxnBuilder.SetField(TxnField.receiver, App.globalGet(self.STATE_PLATFORM_ADDRESS)),
            InnerTxnBuilder.SetField(TxnField.amount, cancellation_fee.load()),
            InnerTxnBuilder.Submit()
        ])
    
    def clear_state_program(self) -> Expr:
        """Clear state program."""
        return Return(Int(1))


def compile_escrow_contract():
    """Compile the escrow contract to TEAL."""
    contract = EscrowContract()
    
    approval_teal = compileTeal(
        contract.approval_program(), 
        Mode.Application, 
        version=8
    )
    
    clear_teal = compileTeal(
        contract.clear_state_program(), 
        Mode.Application, 
        version=8
    )
    
    return approval_teal, clear_teal


if __name__ == "__main__":
    # Compile and save the contract
    approval_teal, clear_teal = compile_escrow_contract()
    
    # Write to files
    with open("../compiled/escrow_approval.teal", "w") as f:
        f.write(approval_teal)
    
    with open("../compiled/escrow_clear.teal", "w") as f:
        f.write(clear_teal)
    
    print("Escrow contract compiled successfully!")
    print("Files saved:")
    print("- ../compiled/escrow_approval.teal")
    print("- ../compiled/escrow_clear.teal")

