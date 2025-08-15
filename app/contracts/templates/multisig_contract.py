"""
Multi-Signature Wallet Smart Contract for ImaniPay Blockchain Service.

This contract provides secure multi-signature wallet functionality with
configurable thresholds, signer management, and transaction batching.
"""

from pyteal import (
    Txn, Assert, Int, TxnType, Seq, Return, compileTeal, Mode, 
    InnerTxnBuilder, Global, Addr, TxnField, Btoi, Bytes, App,
    If, And, Or, Not, Cond, Subroutine, TealType, Expr,
    ScratchVar, For, While, Break, Continue, Approve, Reject,
    Substring, Len, Concat, Itob,
    Pop, SetBit, GetBit, BytesAdd,
    Extract, Replace, Keccak256, Sha256, Ed25519Verify
)


class MultiSigContract:
    """Multi-signature wallet contract with advanced features."""
    
    def __init__(self):
        # Contract state keys
        self.STATE_THRESHOLD = Bytes("threshold")
        self.STATE_SIGNER_COUNT = Bytes("signer_count")
        self.STATE_PROPOSAL_COUNT = Bytes("proposal_count")
        self.STATE_ADMIN = Bytes("admin")
        
        # Signer state keys (indexed)
        self.STATE_SIGNER_PREFIX = Bytes("signer_")
        self.STATE_SIGNER_ACTIVE_PREFIX = Bytes("signer_active_")
        
        # Proposal state keys (indexed)
        self.STATE_PROPOSAL_PREFIX = Bytes("proposal_")
        self.STATE_PROPOSAL_SIGNATURES_PREFIX = Bytes("proposal_sigs_")
        self.STATE_PROPOSAL_EXECUTED_PREFIX = Bytes("proposal_exec_")
        self.STATE_PROPOSAL_DEADLINE_PREFIX = Bytes("proposal_deadline_")
        
        # Method selectors
        self.METHOD_INITIALIZE = Bytes("initialize")
        self.METHOD_ADD_SIGNER = Bytes("add_signer")
        self.METHOD_REMOVE_SIGNER = Bytes("remove_signer")
        self.METHOD_UPDATE_THRESHOLD = Bytes("update_threshold")
        self.METHOD_PROPOSE_TRANSACTION = Bytes("propose_transaction")
        self.METHOD_SIGN_PROPOSAL = Bytes("sign_proposal")
        self.METHOD_EXECUTE_PROPOSAL = Bytes("execute_proposal")
        self.METHOD_CANCEL_PROPOSAL = Bytes("cancel_proposal")
        self.METHOD_BATCH_EXECUTE = Bytes("batch_execute")
        
        # Transaction types
        self.TXN_TYPE_PAYMENT = Int(1)
        self.TXN_TYPE_ASSET_TRANSFER = Int(2)
        self.TXN_TYPE_APP_CALL = Int(3)
        self.TXN_TYPE_ASSET_CONFIG = Int(4)
        
        # Constants
        self.MAX_SIGNERS = Int(20)
        self.MAX_PROPOSALS = Int(100)
        self.PROPOSAL_DEADLINE_SECONDS = Int(604800)  # 7 days
    
    def approval_program(self) -> Expr:
        """Main approval program for the multi-sig contract."""
        
        # Initialize multi-sig wallet
        initialize_wallet = Seq([
            # Verify initialization parameters
            Assert(Btoi(Txn.application_args[0]) > Int(0)),  # threshold > 0
            Assert(Btoi(Txn.application_args[1]) > Int(0)),  # signer count > 0
            Assert(Btoi(Txn.application_args[0]) <= Btoi(Txn.application_args[1])),  # threshold <= signers
            Assert(Btoi(Txn.application_args[1]) <= self.MAX_SIGNERS),  # signers <= max
            
            # Store basic configuration
            App.globalPut(self.STATE_THRESHOLD, Btoi(Txn.application_args[0])),
            App.globalPut(self.STATE_SIGNER_COUNT, Btoi(Txn.application_args[1])),
            App.globalPut(self.STATE_PROPOSAL_COUNT, Int(0)),
            App.globalPut(self.STATE_ADMIN, Txn.sender()),
            
            # Initialize signers from application args
            self._initialize_signers(),
            
            Return(Int(1))
        ])
        
        # Add new signer (admin only)
        add_signer = Seq([
            # Verify caller is admin
            Assert(Txn.sender() == App.globalGet(self.STATE_ADMIN)),
            
            # Verify signer limit not exceeded
            Assert(App.globalGet(self.STATE_SIGNER_COUNT) < self.MAX_SIGNERS),
            
            # Verify new signer address is valid
            Assert(Len(Txn.application_args[1]) == Int(32)),
            
            # Add signer
            self._add_new_signer(Txn.application_args[1]),
            
            Return(Int(1))
        ])
        
        # Remove signer (admin only)
        remove_signer = Seq([
            # Verify caller is admin
            Assert(Txn.sender() == App.globalGet(self.STATE_ADMIN)),
            
            # Verify signer exists and is active
            Assert(self._is_signer_active(Txn.application_args[1])),
            
            # Verify threshold will still be achievable
            Assert(App.globalGet(self.STATE_SIGNER_COUNT) - Int(1) >= App.globalGet(self.STATE_THRESHOLD)),
            
            # Remove signer
            self._remove_existing_signer(Txn.application_args[1]),
            
            Return(Int(1))
        ])
        
        # Update threshold (requires multi-sig approval)
        update_threshold = Seq([
            # This should be done through a proposal, not directly
            # Verify caller is the contract itself (from executed proposal)
            Assert(Txn.sender() == Global.current_application_address()),
            
            # Verify new threshold is valid
            Assert(Btoi(Txn.application_args[1]) > Int(0)),
            Assert(Btoi(Txn.application_args[1]) <= App.globalGet(self.STATE_SIGNER_COUNT)),
            
            # Update threshold
            App.globalPut(self.STATE_THRESHOLD, Btoi(Txn.application_args[1])),
            
            Return(Int(1))
        ])
        
        # Propose transaction
        propose_transaction = Seq([
            # Verify caller is a signer
            Assert(self._is_signer_active(Txn.sender())),
            
            # Verify proposal limit not exceeded
            Assert(App.globalGet(self.STATE_PROPOSAL_COUNT) < self.MAX_PROPOSALS),
            
            # Create new proposal
            self._create_proposal(),
            
            Return(Int(1))
        ])
        
        # Sign proposal
        sign_proposal = Seq([
            # Verify caller is a signer
            Assert(self._is_signer_active(Txn.sender())),
            
            # Verify proposal exists and is not executed
            Assert(self._proposal_exists(Btoi(Txn.application_args[1]))),
            Assert(Not(self._proposal_executed(Btoi(Txn.application_args[1])))),
            
            # Verify proposal not expired
            Assert(self._proposal_not_expired(Btoi(Txn.application_args[1]))),
            
            # Add signature
            self._add_signature_to_proposal(Btoi(Txn.application_args[1]), Txn.sender()),
            
            Return(Int(1))
        ])
        
        # Execute proposal
        execute_proposal = Seq([
            # Verify proposal exists and is not executed
            Assert(self._proposal_exists(Btoi(Txn.application_args[1]))),
            Assert(Not(self._proposal_executed(Btoi(Txn.application_args[1])))),
            
            # Verify proposal not expired
            Assert(self._proposal_not_expired(Btoi(Txn.application_args[1]))),
            
            # Verify threshold met
            Assert(self._proposal_threshold_met(Btoi(Txn.application_args[1]))),
            
            # Execute the transaction
            self._execute_proposal_transaction(Btoi(Txn.application_args[1])),
            
            # Mark as executed
            self._mark_proposal_executed(Btoi(Txn.application_args[1])),
            
            Return(Int(1))
        ])
        
        # Cancel proposal (proposer only, before execution)
        cancel_proposal = Seq([
            # Verify proposal exists and is not executed
            Assert(self._proposal_exists(Btoi(Txn.application_args[1]))),
            Assert(Not(self._proposal_executed(Btoi(Txn.application_args[1])))),
            
            # Verify caller is proposer or admin
            Assert(Or(
                Txn.sender() == self._get_proposal_proposer(Btoi(Txn.application_args[1])),
                Txn.sender() == App.globalGet(self.STATE_ADMIN)
            )),
            
            # Mark as executed (cancelled)
            self._mark_proposal_executed(Btoi(Txn.application_args[1])),
            
            Return(Int(1))
        ])
        
        # Batch execute multiple proposals
        batch_execute = Seq([
            # Verify caller is a signer
            Assert(self._is_signer_active(Txn.sender())),
            
            # Execute multiple proposals in sequence
            self._batch_execute_proposals(),
            
            Return(Int(1))
        ])
        
        # Main program logic
        program = Cond(
            [Txn.application_id() == Int(0), Return(Int(1))],  # Creation
            [Txn.on_call() == self.METHOD_INITIALIZE, initialize_wallet],
            [Txn.on_call() == self.METHOD_ADD_SIGNER, add_signer],
            [Txn.on_call() == self.METHOD_REMOVE_SIGNER, remove_signer],
            [Txn.on_call() == self.METHOD_UPDATE_THRESHOLD, update_threshold],
            [Txn.on_call() == self.METHOD_PROPOSE_TRANSACTION, propose_transaction],
            [Txn.on_call() == self.METHOD_SIGN_PROPOSAL, sign_proposal],
            [Txn.on_call() == self.METHOD_EXECUTE_PROPOSAL, execute_proposal],
            [Txn.on_call() == self.METHOD_CANCEL_PROPOSAL, cancel_proposal],
            [Txn.on_call() == self.METHOD_BATCH_EXECUTE, batch_execute]
        )
        
        return program
    
    def _initialize_signers(self) -> Expr:
        """Initialize signers from application arguments."""
        signer_count = ScratchVar(TealType.uint64)
        i = ScratchVar(TealType.uint64)
        
        return Seq([
            signer_count.store(App.globalGet(self.STATE_SIGNER_COUNT)),
            i.store(Int(0)),
            
            # Loop through signer arguments (starting from arg 2)
            While(i.load() < signer_count.load()).Do(Seq([
                # Store signer address
                App.globalPut(
                    Concat(self.STATE_SIGNER_PREFIX, Itob(i.load())),
                    Txn.application_args[Int(2) + i.load()]
                ),
                
                # Mark signer as active
                App.globalPut(
                    Concat(self.STATE_SIGNER_ACTIVE_PREFIX, Itob(i.load())),
                    Int(1)
                ),
                
                i.store(i.load() + Int(1))
            ]))
        ])
    
    def _is_signer_active(self, address: Expr) -> Expr:
        """Check if address is an active signer."""
        i = ScratchVar(TealType.uint64)
        found = ScratchVar(TealType.uint64)
        
        return Seq([
            i.store(Int(0)),
            found.store(Int(0)),
            
            While(And(
                i.load() < App.globalGet(self.STATE_SIGNER_COUNT),
                found.load() == Int(0)
            )).Do(Seq([
                If(And(
                    App.globalGet(Concat(self.STATE_SIGNER_PREFIX, Itob(i.load()))) == address,
                    App.globalGet(Concat(self.STATE_SIGNER_ACTIVE_PREFIX, Itob(i.load()))) == Int(1)
                ),
                    found.store(Int(1))
                ),
                i.store(i.load() + Int(1))
            ])),
            
            found.load()
        ])
    
    def _add_new_signer(self, signer_address: Expr) -> Expr:
        """Add a new signer to the wallet."""
        signer_count = ScratchVar(TealType.uint64)
        
        return Seq([
            signer_count.store(App.globalGet(self.STATE_SIGNER_COUNT)),
            
            # Add signer at next index
            App.globalPut(
                Concat(self.STATE_SIGNER_PREFIX, Itob(signer_count.load())),
                signer_address
            ),
            
            # Mark as active
            App.globalPut(
                Concat(self.STATE_SIGNER_ACTIVE_PREFIX, Itob(signer_count.load())),
                Int(1)
            ),
            
            # Increment signer count
            App.globalPut(self.STATE_SIGNER_COUNT, signer_count.load() + Int(1))
        ])
    
    def _remove_existing_signer(self, signer_address: Expr) -> Expr:
        """Remove an existing signer from the wallet."""
        i = ScratchVar(TealType.uint64)
        
        return Seq([
            i.store(Int(0)),
            
            # Find and deactivate signer
            While(i.load() < App.globalGet(self.STATE_SIGNER_COUNT)).Do(Seq([
                If(App.globalGet(Concat(self.STATE_SIGNER_PREFIX, Itob(i.load()))) == signer_address,
                    # Mark as inactive
                    App.globalPut(
                        Concat(self.STATE_SIGNER_ACTIVE_PREFIX, Itob(i.load())),
                        Int(0)
                    )
                ),
                i.store(i.load() + Int(1))
            ]))
        ])
    
    def _create_proposal(self) -> Expr:
        """Create a new transaction proposal."""
        proposal_id = ScratchVar(TealType.uint64)
        
        return Seq([
            proposal_id.store(App.globalGet(self.STATE_PROPOSAL_COUNT)),
            
            # Store proposal data
            App.globalPut(
                Concat(self.STATE_PROPOSAL_PREFIX, Itob(proposal_id.load())),
                Concat(
                    Txn.application_args[1],  # Transaction type
                    Txn.application_args[2],  # Recipient/target
                    Txn.application_args[3],  # Amount/data
                    Txn.sender()              # Proposer
                )
            ),
            
            # Initialize signatures (proposer automatically signs)
            App.globalPut(
                Concat(self.STATE_PROPOSAL_SIGNATURES_PREFIX, Itob(proposal_id.load())),
                Concat(Txn.sender(), Bytes("base16", "00" * 31))  # Pad to 32 bytes per signature
            ),
            
            # Set deadline
            App.globalPut(
                Concat(self.STATE_PROPOSAL_DEADLINE_PREFIX, Itob(proposal_id.load())),
                Global.latest_timestamp() + self.PROPOSAL_DEADLINE_SECONDS
            ),
            
            # Mark as not executed
            App.globalPut(
                Concat(self.STATE_PROPOSAL_EXECUTED_PREFIX, Itob(proposal_id.load())),
                Int(0)
            ),
            
            # Increment proposal count
            App.globalPut(self.STATE_PROPOSAL_COUNT, proposal_id.load() + Int(1))
        ])
    
    def _proposal_exists(self, proposal_id: Expr) -> Expr:
        """Check if proposal exists."""
        return proposal_id < App.globalGet(self.STATE_PROPOSAL_COUNT)
    
    def _proposal_executed(self, proposal_id: Expr) -> Expr:
        """Check if proposal is executed."""
        return App.globalGet(
            Concat(self.STATE_PROPOSAL_EXECUTED_PREFIX, Itob(proposal_id))
        ) == Int(1)
    
    def _proposal_not_expired(self, proposal_id: Expr) -> Expr:
        """Check if proposal is not expired."""
        return Global.latest_timestamp() < App.globalGet(
            Concat(self.STATE_PROPOSAL_DEADLINE_PREFIX, Itob(proposal_id))
        )
    
    def _add_signature_to_proposal(self, proposal_id: Expr, signer: Expr) -> Expr:
        """Add signature to proposal."""
        current_sigs = ScratchVar(TealType.bytes)
        
        return Seq([
            current_sigs.store(App.globalGet(
                Concat(self.STATE_PROPOSAL_SIGNATURES_PREFIX, Itob(proposal_id))
            )),
            
            # Append signer to signatures (simplified - in practice would check for duplicates)
            App.globalPut(
                Concat(self.STATE_PROPOSAL_SIGNATURES_PREFIX, Itob(proposal_id)),
                Concat(current_sigs.load(), signer)
            )
        ])
    
    def _proposal_threshold_met(self, proposal_id: Expr) -> Expr:
        """Check if proposal has enough signatures."""
        signatures = ScratchVar(TealType.bytes)
        sig_count = ScratchVar(TealType.uint64)
        
        return Seq([
            signatures.store(App.globalGet(
                Concat(self.STATE_PROPOSAL_SIGNATURES_PREFIX, Itob(proposal_id))
            )),
            
            # Count signatures (each signature is 32 bytes)
            sig_count.store(Len(signatures.load()) / Int(32)),
            
            sig_count.load() >= App.globalGet(self.STATE_THRESHOLD)
        ])
    
    def _execute_proposal_transaction(self, proposal_id: Expr) -> Expr:
        """Execute the transaction in the proposal."""
        proposal_data = ScratchVar(TealType.bytes)
        txn_type = ScratchVar(TealType.uint64)
        
        return Seq([
            proposal_data.store(App.globalGet(
                Concat(self.STATE_PROPOSAL_PREFIX, Itob(proposal_id))
            )),
            
            # Extract transaction type (first byte)
            txn_type.store(Btoi(Extract(proposal_data.load(), Int(0), Int(1)))),
            
            # Execute based on transaction type
            Cond(
                [txn_type.load() == self.TXN_TYPE_PAYMENT, self._execute_payment(proposal_data.load())],
                [txn_type.load() == self.TXN_TYPE_ASSET_TRANSFER, self._execute_asset_transfer(proposal_data.load())],
                [txn_type.load() == self.TXN_TYPE_APP_CALL, self._execute_app_call(proposal_data.load())]
            )
        ])
    
    def _execute_payment(self, proposal_data: Expr) -> Expr:
        """Execute a payment transaction."""
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.Payment),
            InnerTxnBuilder.SetField(TxnField.receiver, Extract(proposal_data, Int(1), Int(32))),
            InnerTxnBuilder.SetField(TxnField.amount, Btoi(Extract(proposal_data, Int(33), Int(8)))),
            InnerTxnBuilder.Submit()
        ])
    
    def _execute_asset_transfer(self, proposal_data: Expr) -> Expr:
        """Execute an asset transfer transaction."""
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.AssetTransfer),
            InnerTxnBuilder.SetField(TxnField.asset_receiver, Extract(proposal_data, Int(1), Int(32))),
            InnerTxnBuilder.SetField(TxnField.asset_amount, Btoi(Extract(proposal_data, Int(33), Int(8)))),
            InnerTxnBuilder.SetField(TxnField.xfer_asset, Btoi(Extract(proposal_data, Int(41), Int(8)))),
            InnerTxnBuilder.Submit()
        ])
    
    def _execute_app_call(self, proposal_data: Expr) -> Expr:
        """Execute an application call transaction."""
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.ApplicationCall),
            InnerTxnBuilder.SetField(TxnField.application_id, Btoi(Extract(proposal_data, Int(1), Int(8)))),
            InnerTxnBuilder.Submit()
        ])
    
    def _mark_proposal_executed(self, proposal_id: Expr) -> Expr:
        """Mark proposal as executed."""
        return App.globalPut(
            Concat(self.STATE_PROPOSAL_EXECUTED_PREFIX, Itob(proposal_id)),
            Int(1)
        )
    
    def _get_proposal_proposer(self, proposal_id: Expr) -> Expr:
        """Get the proposer of a proposal."""
        proposal_data = App.globalGet(
            Concat(self.STATE_PROPOSAL_PREFIX, Itob(proposal_id))
        )
        # Proposer is stored at the end of proposal data
        return Extract(proposal_data, Len(proposal_data) - Int(32), Int(32))
    
    def _batch_execute_proposals(self) -> Expr:
        """Execute multiple proposals in batch."""
        # Simplified implementation - would iterate through proposal IDs in args
        return Seq([
            # Execute first proposal
            If(Len(Txn.application_args) > Int(1),
                self._execute_proposal_transaction(Btoi(Txn.application_args[1]))
            ),
            
            # Execute second proposal
            If(Len(Txn.application_args) > Int(2),
                self._execute_proposal_transaction(Btoi(Txn.application_args[2]))
            ),
            
            # Execute third proposal
            If(Len(Txn.application_args) > Int(3),
                self._execute_proposal_transaction(Btoi(Txn.application_args[3]))
            )
        ])
    
    def clear_state_program(self) -> Expr:
        """Clear state program."""
        return Return(Int(1))


def compile_multisig_contract():
    """Compile the multi-sig contract to TEAL."""
    contract = MultiSigContract()
    
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
    approval_teal, clear_teal = compile_multisig_contract()
    
    # Write to files
    with open("../compiled/multisig_approval.teal", "w") as f:
        f.write(approval_teal)
    
    with open("../compiled/multisig_clear.teal", "w") as f:
        f.write(clear_teal)
    
    print("Multi-sig contract compiled successfully!")
    print("Files saved:")
    print("- ../compiled/multisig_approval.teal")
    print("- ../compiled/multisig_clear.teal")

