"""
Smart Contract Manager for ImaniPay Blockchain Service.

This module provides comprehensive smart contract deployment, interaction,
and management functionality for all contract types.
"""

import logging
import asyncio
import base64
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID

from algosdk import account, mnemonic, transaction, logic
from algosdk.v2client import algod, indexer
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer, AccountTransactionSigner, TransactionWithSigner
)
from algosdk.abi import Contract, Method
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import get_async_session_context
# from app.models import SmartContract, ContractDeployment, ContractInteraction
from app.schemas import (
    ContractDeploymentRequest, ContractDeploymentResponse,
    ContractInteractionRequest, ContractInteractionResponse
)
from app.services.algorand_client import AlgorandClient
from app.services.encryption import EncryptionService

# Import contract templates
from app.contracts.templates.escrow_contract import compile_escrow_contract
from app.contracts.templates.multisig_contract import compile_multisig_contract
from app.contracts.templates.batch_transaction_contract import compile_batch_contract

logger = logging.getLogger(__name__)
settings = get_settings()


class ContractManagerError(Exception):
    """Base exception for contract manager errors."""
    pass


class ContractDeploymentError(ContractManagerError):
    """Exception raised for contract deployment errors."""
    pass


class ContractInteractionError(ContractManagerError):
    """Exception raised for contract interaction errors."""
    pass


class ContractCompilationError(ContractManagerError):
    """Exception raised for contract compilation errors."""
    pass


class ContractManager:
    """Comprehensive smart contract management service."""
    
    def __init__(self):
        self.logger = logger
        self.algorand_client = AlgorandClient()
        self.encryption_service = EncryptionService()
        
        # Contract templates
        self.contract_templates = {
            "escrow": {
                "name": "Escrow Contract",
                "description": "Advanced escrow with dispute resolution",
                "compile_function": compile_escrow_contract,
                "global_schema": {"num_uints": 10, "num_byte_slices": 10},
                "local_schema": {"num_uints": 5, "num_byte_slices": 5}
            },
            "multisig": {
                "name": "Multi-Signature Wallet",
                "description": "Multi-signature wallet with threshold voting",
                "compile_function": compile_multisig_contract,
                "global_schema": {"num_uints": 15, "num_byte_slices": 50},
                "local_schema": {"num_uints": 2, "num_byte_slices": 2}
            },
            "batch": {
                "name": "Batch Transaction Processor",
                "description": "Atomic transaction batching with rollback",
                "compile_function": compile_batch_contract,
                "global_schema": {"num_uints": 10, "num_byte_slices": 20},
                "local_schema": {"num_uints": 1, "num_byte_slices": 1}
            }
        }
        
        # Deployed contract cache
        self.deployed_contracts = {}
    
    # ========================================================================
    # Contract Deployment
    # ========================================================================
    
    async def deploy_contract(
        self,
        contract_type: str,
        deployment_request: ContractDeploymentRequest,
        session: Optional[AsyncSession] = None
    ) -> ContractDeploymentResponse:
        """
        Deploy a smart contract to the Algorand blockchain.
        
        Args:
            contract_type: Type of contract to deploy
            deployment_request: Deployment configuration
            session: Database session
            
        Returns:
            ContractDeploymentResponse: Deployment results
            
        Raises:
            ContractDeploymentError: If deployment fails
        """
        async def _deploy_contract(db_session: AsyncSession) -> ContractDeploymentResponse:
            try:
                # Validate contract type
                if contract_type not in self.contract_templates:
                    raise ContractDeploymentError(f"Unknown contract type: {contract_type}")
                
                template = self.contract_templates[contract_type]
                
                # Compile contract
                self.logger.info(f"Compiling {contract_type} contract...")
                approval_teal, clear_teal = template["compile_function"]()
                
                # Compile TEAL to bytecode
                approval_program = await self._compile_teal_to_bytecode(approval_teal)
                clear_program = await self._compile_teal_to_bytecode(clear_teal)
                
                # Create deployment transaction
                deployer_account = await self._get_deployer_account(deployment_request.deployer_address)
                
                # Build application creation transaction
                app_create_txn = await self._build_app_create_transaction(
                    deployer_account,
                    approval_program,
                    clear_program,
                    template["global_schema"],
                    template["local_schema"],
                    deployment_request.app_args or []
                )
                
                # Sign and submit transaction
                signed_txn = app_create_txn.sign(deployer_account["private_key"])
                txn_id = await self.algorand_client.submit_transaction(signed_txn)
                
                # Wait for confirmation
                confirmed_txn = await self.algorand_client.wait_for_confirmation(txn_id)
                app_id = confirmed_txn["application-index"]
                
                # Store deployment in database
                # contract_deployment = ContractDeployment(
                #     contract_type=contract_type,
                #     app_id=app_id,
                #     deployer_address=deployment_request.deployer_address,
                #     transaction_id=txn_id,
                #     approval_program=base64.b64encode(approval_program).decode(),
                #     clear_program=base64.b64encode(clear_program).decode(),
                #     global_schema=template["global_schema"],
                #     local_schema=template["local_schema"],
                #     deployment_args=deployment_request.app_args or [],
                #     status="deployed",
                #     network=settings.algorand.network
                # )
                
                # db_session.add(contract_deployment)
                # await db_session.commit()
                # await db_session.refresh(contract_deployment)
                
                # Cache deployed contract
                self.deployed_contracts[app_id] = {
                    "type": contract_type,
                    "deployment": None # Removed deployment model
                }
                
                self.logger.info(f"Successfully deployed {contract_type} contract with app ID: {app_id}")
                
                return ContractDeploymentResponse(
                    app_id=app_id,
                    transaction_id=txn_id,
                    contract_type=contract_type,
                    deployer_address=deployment_request.deployer_address,
                    status="deployed",
                    deployment_timestamp=datetime.utcnow(),
                    contract_address=logic.get_application_address(app_id)
                )
                
            except Exception as e:
                self.logger.error(f"Contract deployment failed: {e}")
                raise ContractDeploymentError(f"Deployment failed: {str(e)}")
        
        if session:
            return await _deploy_contract(session)
        else:
            async with get_async_session_context() as db_session:
                return await _deploy_contract(db_session)
    
    async def update_contract(
        self,
        app_id: int,
        new_approval_program: bytes,
        new_clear_program: bytes,
        updater_address: str,
        session: Optional[AsyncSession] = None
    ) -> ContractInteractionResponse:
        """
        Update an existing smart contract.
        
        Args:
            app_id: Application ID
            new_approval_program: New approval program bytecode
            new_clear_program: New clear program bytecode
            updater_address: Address of the updater
            session: Database session
            
        Returns:
            ContractInteractionResponse: Update results
        """
        async def _update_contract(db_session: AsyncSession) -> ContractInteractionResponse:
            try:
                # Get updater account
                updater_account = await self._get_deployer_account(updater_address)
                
                # Build application update transaction
                app_update_txn = await self._build_app_update_transaction(
                    app_id,
                    updater_account,
                    new_approval_program,
                    new_clear_program
                )
                
                # Sign and submit transaction
                signed_txn = app_update_txn.sign(updater_account["private_key"])
                txn_id = await self.algorand_client.submit_transaction(signed_txn)
                
                # Wait for confirmation
                await self.algorand_client.wait_for_confirmation(txn_id)
                
                # Update database record
                # await db_session.execute(
                #     update(ContractDeployment)
                #     .where(ContractDeployment.app_id == app_id)
                #     .values(
                #         approval_program=base64.b64encode(new_approval_program).decode(),
                #         clear_program=base64.b64encode(new_clear_program).decode(),
                #         updated_at=datetime.utcnow()
                #     )
                # )
                # await db_session.commit()
                
                self.logger.info(f"Successfully updated contract {app_id}")
                
                return ContractInteractionResponse(
                    transaction_id=txn_id,
                    app_id=app_id,
                    status="success",
                    message="Contract updated successfully"
                )
                
            except Exception as e:
                self.logger.error(f"Contract update failed: {e}")
                raise ContractInteractionError(f"Update failed: {str(e)}")
        
        if session:
            return await _update_contract(session)
        else:
            async with get_async_session_context() as db_session:
                return await _update_contract(db_session)
    
    async def delete_contract(
        self,
        app_id: int,
        deleter_address: str,
        session: Optional[AsyncSession] = None
    ) -> ContractInteractionResponse:
        """
        Delete a smart contract.
        
        Args:
            app_id: Application ID
            deleter_address: Address of the deleter
            session: Database session
            
        Returns:
            ContractInteractionResponse: Deletion results
        """
        async def _delete_contract(db_session: AsyncSession) -> ContractInteractionResponse:
            try:
                # Get deleter account
                deleter_account = await self._get_deployer_account(deleter_address)
                
                # Build application delete transaction
                app_delete_txn = await self._build_app_delete_transaction(app_id, deleter_account)
                
                # Sign and submit transaction
                signed_txn = app_delete_txn.sign(deleter_account["private_key"])
                txn_id = await self.algorand_client.submit_transaction(signed_txn)
                
                # Wait for confirmation
                await self.algorand_client.wait_for_confirmation(txn_id)
                
                # Update database record
                # await db_session.execute(
                #     update(ContractDeployment)
                #     .where(ContractDeployment.app_id == app_id)
                #     .values(
                #         status="deleted",
                #         updated_at=datetime.utcnow()
                #     )
                # )
                # await db_session.commit()
                
                # Remove from cache
                if app_id in self.deployed_contracts:
                    del self.deployed_contracts[app_id]
                
                self.logger.info(f"Successfully deleted contract {app_id}")
                
                return ContractInteractionResponse(
                    transaction_id=txn_id,
                    app_id=app_id,
                    status="success",
                    message="Contract deleted successfully"
                )
                
            except Exception as e:
                self.logger.error(f"Contract deletion failed: {e}")
                raise ContractInteractionError(f"Deletion failed: {str(e)}")
        
        if session:
            return await _delete_contract(session)
        else:
            async with get_async_session_context() as db_session:
                return await _delete_contract(db_session)
    
    # ========================================================================
    # Contract Interaction
    # ========================================================================
    
    async def call_contract(
        self,
        interaction_request: ContractInteractionRequest,
        session: Optional[AsyncSession] = None
    ) -> ContractInteractionResponse:
        """
        Call a smart contract method.
        
        Args:
            interaction_request: Contract interaction request
            session: Database session
            
        Returns:
            ContractInteractionResponse: Interaction results
        """
        async def _call_contract(db_session: AsyncSession) -> ContractInteractionResponse:
            try:
                # Get caller account
                caller_account = await self._get_deployer_account(interaction_request.caller_address)
                
                # Build application call transaction
                app_call_txn = await self._build_app_call_transaction(
                    interaction_request.app_id,
                    caller_account,
                    interaction_request.method_name,
                    interaction_request.method_args or [],
                    interaction_request.accounts or [],
                    interaction_request.foreign_apps or [],
                    interaction_request.foreign_assets or []
                )
                
                # Sign and submit transaction
                signed_txn = app_call_txn.sign(caller_account["private_key"])
                txn_id = await self.algorand_client.submit_transaction(signed_txn)
                
                # Wait for confirmation
                confirmed_txn = await self.algorand_client.wait_for_confirmation(txn_id)
                
                # Extract logs and return values
                logs = confirmed_txn.get("logs", [])
                inner_txns = confirmed_txn.get("inner-txns", [])
                
                # Store interaction in database
                # contract_interaction = ContractInteraction(
                #     app_id=interaction_request.app_id,
                #     caller_address=interaction_request.caller_address,
                #     method_name=interaction_request.method_name,
                #     method_args=interaction_request.method_args or [],
                #     transaction_id=txn_id,
                #     status="success",
                #     logs=logs,
                #     inner_transactions=inner_txns
                # )
                
                # db_session.add(contract_interaction)
                # await db_session.commit()
                
                self.logger.info(f"Successfully called {interaction_request.method_name} on contract {interaction_request.app_id}")
                
                return ContractInteractionResponse(
                    transaction_id=txn_id,
                    app_id=interaction_request.app_id,
                    status="success",
                    message="Contract call successful",
                    logs=logs,
                    inner_transactions=inner_txns
                )
                
            except Exception as e:
                self.logger.error(f"Contract call failed: {e}")
                raise ContractInteractionError(f"Contract call failed: {str(e)}")
        
        if session:
            return await _call_contract(session)
        else:
            async with get_async_session_context() as db_session:
                return await _call_contract(db_session)
    
    async def read_contract_state(
        self,
        app_id: int,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Read the global state of a smart contract.
        
        Args:
            app_id: Application ID
            session: Database session
            
        Returns:
            Dict[str, Any]: Contract global state
        """
        try:
            app_info = await self.algorand_client.get_application_info(app_id)
            
            if not app_info:
                raise ContractInteractionError(f"Contract {app_id} not found")
            
            global_state = {}
            
            # Parse global state
            if "global-state" in app_info["params"]:
                for state_item in app_info["params"]["global-state"]:
                    key = base64.b64decode(state_item["key"]).decode('utf-8')
                    
                    if state_item["value"]["type"] == 1:  # bytes
                        value = base64.b64decode(state_item["value"]["bytes"])
                    else:  # uint
                        value = state_item["value"]["uint"]
                    
                    global_state[key] = value
            
            return global_state
            
        except Exception as e:
            self.logger.error(f"Failed to read contract state: {e}")
            raise ContractInteractionError(f"Failed to read state: {str(e)}")
    
    # ========================================================================
    # Specialized Contract Operations
    # ========================================================================
    
    async def create_escrow(
        self,
        sender_address: str,
        receiver_address: str,
        arbitrator_address: str,
        amount: int,
        deadline_timestamp: int,
        fee_percentage: int = 100,  # 1%
        session: Optional[AsyncSession] = None
    ) -> ContractInteractionResponse:
        """
        Create a new escrow contract instance.
        
        Args:
            sender_address: Sender address
            receiver_address: Receiver address
            arbitrator_address: Arbitrator address
            amount: Escrow amount in microAlgos
            deadline_timestamp: Deadline timestamp
            fee_percentage: Fee percentage in basis points
            session: Database session
            
        Returns:
            ContractInteractionResponse: Escrow creation results
        """
        # Deploy escrow contract
        deployment_request = ContractDeploymentRequest(
            deployer_address=sender_address,
            app_args=[
                sender_address.encode(),
                receiver_address.encode(),
                arbitrator_address.encode(),
                str(deadline_timestamp).encode(),
                str(amount).encode(),
                str(fee_percentage).encode(),
                settings.algorand.platform_address.encode()
            ]
        )
        
        deployment_response = await self.deploy_contract("escrow", deployment_request, session)
        
        # Initialize escrow
        interaction_request = ContractInteractionRequest(
            app_id=deployment_response.app_id,
            caller_address=sender_address,
            method_name="initialize",
            method_args=deployment_request.app_args
        )
        
        return await self.call_contract(interaction_request, session)
    
    async def create_multisig_wallet(
        self,
        admin_address: str,
        threshold: int,
        signer_addresses: List[str],
        session: Optional[AsyncSession] = None
    ) -> ContractInteractionResponse:
        """
        Create a new multi-signature wallet.
        
        Args:
            admin_address: Admin address
            threshold: Signature threshold
            signer_addresses: List of signer addresses
            session: Database session
            
        Returns:
            ContractInteractionResponse: Multi-sig creation results
        """
        # Prepare arguments
        app_args = [
            str(threshold).encode(),
            str(len(signer_addresses)).encode()
        ]
        app_args.extend([addr.encode() for addr in signer_addresses])
        
        # Deploy multi-sig contract
        deployment_request = ContractDeploymentRequest(
            deployer_address=admin_address,
            app_args=app_args
        )
        
        deployment_response = await self.deploy_contract("multisig", deployment_request, session)
        
        # Initialize multi-sig wallet
        interaction_request = ContractInteractionRequest(
            app_id=deployment_response.app_id,
            caller_address=admin_address,
            method_name="initialize",
            method_args=app_args
        )
        
        return await self.call_contract(interaction_request, session)
    
    async def create_batch_processor(
        self,
        admin_address: str,
        max_batch_size: int = 16,
        session: Optional[AsyncSession] = None
    ) -> ContractInteractionResponse:
        """
        Create a new batch transaction processor.
        
        Args:
            admin_address: Admin address
            max_batch_size: Maximum batch size
            session: Database session
            
        Returns:
            ContractInteractionResponse: Batch processor creation results
        """
        # Deploy batch contract
        deployment_request = ContractDeploymentRequest(
            deployer_address=admin_address,
            app_args=[
                str(max_batch_size).encode(),
                admin_address.encode()
            ]
        )
        
        deployment_response = await self.deploy_contract("batch", deployment_request, session)
        
        # Initialize batch processor
        interaction_request = ContractInteractionRequest(
            app_id=deployment_response.app_id,
            caller_address=admin_address,
            method_name="initialize",
            method_args=deployment_request.app_args
        )
        
        return await self.call_contract(interaction_request, session)
    
    # ========================================================================
    # Contract Management
    # ========================================================================
    
    async def get_deployed_contracts(
        self,
        contract_type: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of deployed contracts.
        
        Args:
            contract_type: Filter by contract type
            session: Database session
            
        Returns:
            List[Dict[str, Any]]: List of deployed contracts
        """
        async def _get_contracts(db_session: AsyncSession) -> List[Dict[str, Any]]:
            # query = select(ContractDeployment).where(ContractDeployment.status == "deployed")
            
            # if contract_type:
            #     query = query.where(ContractDeployment.contract_type == contract_type)
            
            # result = await db_session.execute(query)
            # deployments = result.scalars().all()
            
            contracts = []
            # for deployment in deployments:
            #     contracts.append({
            #         "app_id": deployment.app_id,
            #         "contract_type": deployment.contract_type,
            #         "deployer_address": deployment.deployer_address,
            #         "contract_address": logic.get_application_address(deployment.app_id),
            #         "deployment_timestamp": deployment.created_at,
            #         "transaction_id": deployment.transaction_id,
            #         "network": deployment.network
            #     })
            
            return contracts
        
        if session:
            return await _get_contracts(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_contracts(db_session)
    
    async def get_contract_interactions(
        self,
        app_id: int,
        limit: int = 100,
        session: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get contract interaction history.
        
        Args:
            app_id: Application ID
            limit: Maximum number of interactions to return
            session: Database session
            
        Returns:
            List[Dict[str, Any]]: List of contract interactions
        """
        async def _get_interactions(db_session: AsyncSession) -> List[Dict[str, Any]]:
            # result = await db_session.execute(
            #     select(ContractInteraction)
            #     .where(ContractInteraction.app_id == app_id)
            #     .order_by(ContractInteraction.created_at.desc())
            #     .limit(limit)
            # )
            
            # interactions = result.scalars().all()
            
            return [] # Removed ContractInteraction model
        
        if session:
            return await _get_interactions(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_interactions(db_session)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _compile_teal_to_bytecode(self, teal_code: str) -> bytes:
        """Compile TEAL code to bytecode."""
        try:
            compile_response = await self.algorand_client.compile_teal(teal_code)
            return base64.b64decode(compile_response["result"])
        except Exception as e:
            raise ContractCompilationError(f"TEAL compilation failed: {str(e)}")
    
    async def _get_deployer_account(self, address: str) -> Dict[str, Any]:
        """Get deployer account information."""
        # In production, this would retrieve the private key securely
        # For now, return a mock account structure
        return {
            "address": address,
            "private_key": "mock_private_key"  # This should be retrieved securely
        }
    
    async def _build_app_create_transaction(
        self,
        deployer_account: Dict[str, Any],
        approval_program: bytes,
        clear_program: bytes,
        global_schema: Dict[str, int],
        local_schema: Dict[str, int],
        app_args: List[bytes]
    ) -> transaction.ApplicationCreateTxn:
        """Build application creation transaction."""
        params = await self.algorand_client.get_suggested_params()
        
        return transaction.ApplicationCreateTxn(
            sender=deployer_account["address"],
            sp=params,
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval_program,
            clear_program=clear_program,
            global_schema=transaction.StateSchema(
                num_uints=global_schema["num_uints"],
                num_byte_slices=global_schema["num_byte_slices"]
            ),
            local_schema=transaction.StateSchema(
                num_uints=local_schema["num_uints"],
                num_byte_slices=local_schema["num_byte_slices"]
            ),
            app_args=app_args
        )
    
    async def _build_app_update_transaction(
        self,
        app_id: int,
        updater_account: Dict[str, Any],
        approval_program: bytes,
        clear_program: bytes
    ) -> transaction.ApplicationUpdateTxn:
        """Build application update transaction."""
        params = await self.algorand_client.get_suggested_params()
        
        return transaction.ApplicationUpdateTxn(
            sender=updater_account["address"],
            sp=params,
            index=app_id,
            approval_program=approval_program,
            clear_program=clear_program
        )
    
    async def _build_app_delete_transaction(
        self,
        app_id: int,
        deleter_account: Dict[str, Any]
    ) -> transaction.ApplicationDeleteTxn:
        """Build application delete transaction."""
        params = await self.algorand_client.get_suggested_params()
        
        return transaction.ApplicationDeleteTxn(
            sender=deleter_account["address"],
            sp=params,
            index=app_id
        )
    
    async def _build_app_call_transaction(
        self,
        app_id: int,
        caller_account: Dict[str, Any],
        method_name: str,
        method_args: List[Any],
        accounts: List[str],
        foreign_apps: List[int],
        foreign_assets: List[int]
    ) -> transaction.ApplicationCallTxn:
        """Build application call transaction."""
        params = await self.algorand_client.get_suggested_params()
        
        # Convert method name and args to bytes
        app_args = [method_name.encode()]
        for arg in method_args:
            if isinstance(arg, str):
                app_args.append(arg.encode())
            elif isinstance(arg, int):
                app_args.append(arg.to_bytes(8, 'big'))
            elif isinstance(arg, bytes):
                app_args.append(arg)
            else:
                app_args.append(str(arg).encode())
        
        return transaction.ApplicationCallTxn(
            sender=caller_account["address"],
            sp=params,
            index=app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=app_args,
            accounts=accounts,
            foreign_apps=foreign_apps,
            foreign_assets=foreign_assets
        )

