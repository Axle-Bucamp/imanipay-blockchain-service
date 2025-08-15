"""
Compliance service for ImaniPay Blockchain Service.

This module provides comprehensive KYC (Know Your Customer) and AML 
(Anti-Money Laundering) compliance functionality for regulatory adherence.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import enum

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.database import get_async_session_context
from app.models import (
     User, UserProfile, KYCVerification, AMLScreening, Transaction
)
from app.schemas import (
    KYCVerificationRequest, KYCVerificationResponse, RiskAssessment, RiskLevel, TransactionType
)

from app.schemas.enumerate import KYCStatus
from models import AMLScreening, Transaction, User

logger = logging.getLogger(__name__)
settings = get_settings()

class ComplianceError(Exception):
    """Base exception for compliance errors."""
    pass


class KYCError(ComplianceError):
    """Exception raised for KYC-related errors."""
    pass


class AMLError(ComplianceError):
    """Exception raised for AML-related errors."""
    pass


class RiskAssessmentError(ComplianceError):
    """Exception raised for risk assessment errors."""
    pass


class ComplianceService:
    """Comprehensive compliance service for KYC/AML operations."""
    
    def __init__(self):
        self.logger = logger
        
        # Risk scoring weights
        self.risk_weights = {
            "country_risk": 0.25,
            "transaction_pattern": 0.20,
            "kyc_completeness": 0.15,
            "account_age": 0.10,
            "transaction_volume": 0.15,
            "velocity": 0.10,
            "external_screening": 0.05
        }
        
        # High-risk countries (simplified list)
        self.high_risk_countries = {
            "AF", "BY", "MM", "KP", "IR", "IQ", "LY", "ML", "NI", "SO", "SS", "SD", "SY", "YE", "ZW"
        }
        
        # Medium-risk countries
        self.medium_risk_countries = {
            "AL", "BB", "BF", "KH", "JM", "JO", "LA", "LB", "MR", "MN", "MA", "MZ", "NP", "PK", "PA", "PH", "SN", "LK", "TZ", "TT", "UG", "VU", "ZM"
        }
    
    # ========================================================================
    # KYC Management
    # ========================================================================
    
    async def initiate_kyc_verification(
        self,
        user_id: UUID,
        verification_request: KYCVerificationRequest,
        session: Optional[AsyncSession] = None
    ) -> KYCVerificationResponse:
        """
        Initiate KYC verification process for a user.
        
        Args:
            user_id: User ID
            verification_request: KYC verification request data
            session: Database session
            
        Returns:
            KYCVerificationResponse: KYC verification details
            
        Raises:
            KYCError: If KYC initiation fails
        """
        async def _initiate_kyc(db_session: AsyncSession) -> KYCVerificationResponse:
            try:
                # Get user
                user_result = await db_session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise KYCError("User not found")
                
                # Check if user already has pending/approved KYC
                existing_kyc = await db_session.execute(
                    select(KYCVerification)
                    .where(
                        and_(
                            KYCVerification.user_id == user_id,
                            KYCVerification.status.in_([
                                KYCStatus.IN_PROGRESS,
                                KYCStatus.PENDING_REVIEW,
                                KYCStatus.APPROVED
                            ])
                        )
                    )
                    .order_by(KYCVerification.created_at.desc())
                )
                
                existing = existing_kyc.scalar_one_or_none()
                if existing and existing.status == KYCStatus.APPROVED:
                    raise KYCError("User already has approved KYC verification")
                
                # Create new KYC verification
                kyc_verification = KYCVerification(
                    user_id=user_id,
                    verification_level=verification_request.verification_level,
                    status=KYCStatus.IN_PROGRESS,
                    provider=settings.compliance.kyc_provider,
                    documents_submitted=verification_request.documents,
                    verification_data=verification_request.personal_info,
                    submitted_at=datetime.utcnow()
                )
                
                db_session.add(kyc_verification)
                await db_session.commit()
                await db_session.refresh(kyc_verification)
                
                # Update user KYC status
                await db_session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(kyc_status=KYCStatus.IN_PROGRESS)
                )
                await db_session.commit()
                
                # Perform initial risk assessment
                risk_score = await self._calculate_kyc_risk_score(
                    verification_request.personal_info, db_session
                )
                
                kyc_verification.risk_score = risk_score
                await db_session.commit()
                
                self.logger.info(f"Initiated KYC verification for user {user_id}")
                
                return KYCVerificationResponse.model_validate(kyc_verification)
                
            except Exception as e:
                self.logger.error(f"Failed to initiate KYC for user {user_id}: {e}")
                raise KYCError(f"KYC initiation failed: {str(e)}")
        
        if session:
            return await _initiate_kyc(session)
        else:
            async with get_async_session_context() as db_session:
                return await _initiate_kyc(db_session)
    
    async def update_kyc_status(
        self,
        kyc_id: UUID,
        status: KYCStatus,
        reviewer_notes: Optional[str] = None,
        rejection_reasons: Optional[List[str]] = None,
        session: Optional[AsyncSession] = None
    ) -> KYCVerificationResponse:
        """
        Update KYC verification status.
        
        Args:
            kyc_id: KYC verification ID
            status: New status
            reviewer_notes: Optional reviewer notes
            rejection_reasons: Optional rejection reasons
            session: Database session
            
        Returns:
            KYCVerificationResponse: Updated KYC verification
            
        Raises:
            KYCError: If status update fails
        """
        async def _update_status(db_session: AsyncSession) -> KYCVerificationResponse:
            try:
                # Get KYC verification
                kyc_result = await db_session.execute(
                    select(KYCVerification).where(KYCVerification.id == kyc_id)
                )
                kyc_verification = kyc_result.scalar_one_or_none()
                
                if not kyc_verification:
                    raise KYCError("KYC verification not found")
                
                # Update status and timestamps
                kyc_verification.status = status
                kyc_verification.reviewer_notes = reviewer_notes
                kyc_verification.rejection_reasons = rejection_reasons or []
                kyc_verification.reviewed_at = datetime.utcnow()
                
                if status == KYCStatus.APPROVED:
                    kyc_verification.approved_at = datetime.utcnow()
                    # Set expiration (e.g., 2 years)
                    kyc_verification.expires_at = datetime.utcnow() + timedelta(days=730)
                elif status == KYCStatus.REJECTED:
                    kyc_verification.rejected_at = datetime.utcnow()
                
                # Update user KYC status
                await db_session.execute(
                    update(User)
                    .where(User.id == kyc_verification.user_id)
                    .values(kyc_status=status)
                )
                
                await db_session.commit()
                
                self.logger.info(f"Updated KYC {kyc_id} status to {status}")
                
                return KYCVerificationResponse.model_validate(kyc_verification)
                
            except Exception as e:
                self.logger.error(f"Failed to update KYC status for {kyc_id}: {e}")
                raise KYCError(f"KYC status update failed: {str(e)}")
        
        if session:
            return await _update_status(session)
        else:
            async with get_async_session_context() as db_session:
                return await _update_status(db_session)
    
    async def get_user_kyc_status(
        self,
        user_id: UUID,
        session: Optional[AsyncSession] = None
    ) -> Optional[KYCVerificationResponse]:
        """
        Get user's current KYC verification status.
        
        Args:
            user_id: User ID
            session: Database session
            
        Returns:
            KYCVerificationResponse: Current KYC verification or None
        """
        async def _get_kyc_status(db_session: AsyncSession) -> Optional[KYCVerificationResponse]:
            result = await db_session.execute(
                select(KYCVerification)
                .where(KYCVerification.user_id == user_id)
                .order_by(KYCVerification.created_at.desc())
            )
            
            kyc_verification = result.scalar_one_or_none()
            
            if kyc_verification:
                return KYCVerificationResponse.model_validate(kyc_verification)
            return None
        
        if session:
            return await _get_kyc_status(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_kyc_status(db_session)
    
    # ========================================================================
    # AML Screening
    # ========================================================================
    
    async def screen_user_for_aml(
        self,
        user_id: UUID,
        screening_type: str = "onboarding",
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Perform AML screening for a user.
        
        Args:
            user_id: User ID
            screening_type: Type of screening (onboarding, periodic, transaction)
            session: Database session
            
        Returns:
            Dict[str, Any]: AML screening results
            
        Raises:
            AMLError: If AML screening fails
        """
        async def _screen_user(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                # Get user and profile
                user_result = await db_session.execute(
                    select(User)
                    .options(selectinload(User.profile))
                    .where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise AMLError("User not found")
                
                # Prepare screening data
                screening_data = {
                    "user_id": str(user_id),
                    "email": user.email,
                    "phone": user.phone,
                    "screening_type": screening_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if user.profile:
                    screening_data.update({
                        "first_name": user.profile.first_name,
                        "last_name": user.profile.last_name,
                        "date_of_birth": user.profile.date_of_birth.isoformat() if user.profile.date_of_birth else None,
                        "nationality": user.profile.nationality,
                        "country_of_residence": user.profile.country_of_residence,
                        "address": {
                            "line1": user.profile.address_line_1,
                            "line2": user.profile.address_line_2,
                            "city": user.profile.city,
                            "state": user.profile.state_province,
                            "postal_code": user.profile.postal_code,
                            "country": user.profile.country
                        }
                    })
                
                # Perform screening (simplified implementation)
                screening_results = await self._perform_aml_screening(screening_data)
                
                # Calculate risk score
                risk_score = await self._calculate_aml_risk_score(screening_results, user, db_session)
                
                # Determine risk level
                risk_level = self._determine_risk_level(risk_score)
                
                # Create AML screening record
                aml_screening = AMLScreening(
                    user_id=user_id,
                    screening_type=screening_type,
                    status="completed",
                    provider=settings.compliance.aml_provider,
                    screening_data=screening_data,
                    matches=screening_results.get("matches", []),
                    risk_score=risk_score,
                    risk_level=risk_level
                )
                
                db_session.add(aml_screening)
                await db_session.commit()
                
                self.logger.info(f"Completed AML screening for user {user_id}, risk score: {risk_score}")
                
                return {
                    "screening_id": str(aml_screening.id),
                    "risk_score": risk_score,
                    "risk_level": risk_level.value,
                    "matches": screening_results.get("matches", []),
                    "requires_review": risk_score >= settings.compliance.high_risk_threshold,
                    "screening_data": screening_data
                }
                
            except Exception as e:
                self.logger.error(f"AML screening failed for user {user_id}: {e}")
                raise AMLError(f"AML screening failed: {str(e)}")
        
        if session:
            return await _screen_user(session)
        else:
            async with get_async_session_context() as db_session:
                return await _screen_user(db_session)
    
    async def screen_transaction_for_aml(
        self,
        transaction_id: UUID,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Perform AML screening for a transaction.
        
        Args:
            transaction_id: Transaction ID
            session: Database session
            
        Returns:
            Dict[str, Any]: AML screening results
            
        Raises:
            AMLError: If transaction screening fails
        """
        async def _screen_transaction(db_session: AsyncSession) -> Dict[str, Any]:
            try:
                # Get transaction
                txn_result = await db_session.execute(
                    select(Transaction)
                    .options(selectinload(Transaction.user))
                    .where(Transaction.id == transaction_id)
                )
                transaction = txn_result.scalar_one_or_none()
                
                if not transaction:
                    raise AMLError("Transaction not found")
                
                # Prepare screening data
                screening_data = {
                    "transaction_id": str(transaction_id),
                    "user_id": str(transaction.user_id),
                    "amount": str(transaction.amount),
                    "currency": transaction.currency,
                    "transaction_type": transaction.transaction_type.value,
                    "timestamp": transaction.created_at.isoformat()
                }
                
                # Perform screening
                screening_results = await self._perform_transaction_aml_screening(screening_data)
                
                # Calculate risk score
                risk_score = await self._calculate_transaction_risk_score(transaction, db_session)
                
                # Determine risk level
                risk_level = self._determine_risk_level(risk_score)
                
                # Create AML screening record
                aml_screening = AMLScreening(
                    transaction_id=transaction_id,
                    screening_type="transaction",
                    status="completed",
                    provider=settings.compliance.aml_provider,
                    screening_data=screening_data,
                    matches=screening_results.get("matches", []),
                    risk_score=risk_score,
                    risk_level=risk_level
                )
                
                db_session.add(aml_screening)
                await db_session.commit()
                
                self.logger.info(f"Completed transaction AML screening for {transaction_id}, risk score: {risk_score}")
                
                return {
                    "screening_id": str(aml_screening.id),
                    "risk_score": risk_score,
                    "risk_level": risk_level.value,
                    "matches": screening_results.get("matches", []),
                    "requires_review": risk_score >= settings.compliance.high_risk_threshold,
                    "approved": risk_score < settings.compliance.medium_risk_threshold
                }
                
            except Exception as e:
                self.logger.error(f"Transaction AML screening failed for {transaction_id}: {e}")
                raise AMLError(f"Transaction AML screening failed: {str(e)}")
        
        if session:
            return await _screen_transaction(session)
        else:
            async with get_async_session_context() as db_session:
                return await _screen_transaction(db_session)
    
    # ========================================================================
    # Risk Assessment
    # ========================================================================
    
    async def assess_user_risk(
        self,
        user_id: UUID,
        session: Optional[AsyncSession] = None
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment for a user.
        
        Args:
            user_id: User ID
            session: Database session
            
        Returns:
            RiskAssessment: Risk assessment results
            
        Raises:
            RiskAssessmentError: If risk assessment fails
        """
        async def _assess_risk(db_session: AsyncSession) -> RiskAssessment:
            try:
                # Get user with related data
                user_result = await db_session.execute(
                    select(User)
                    .options(
                        selectinload(User.profile),
                        selectinload(User.transactions),
                        selectinload(User.kyc_verifications)
                    )
                    .where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise RiskAssessmentError("User not found")
                
                # Calculate risk factors
                risk_factors = []
                risk_score = 0
                
                # Country risk
                country_risk = self._assess_country_risk(user)
                risk_score += country_risk * self.risk_weights["country_risk"] * 100
                if country_risk > 0.5:
                    risk_factors.append("High-risk country")
                
                # KYC completeness
                kyc_risk = self._assess_kyc_completeness(user)
                risk_score += kyc_risk * self.risk_weights["kyc_completeness"] * 100
                if kyc_risk > 0.5:
                    risk_factors.append("Incomplete KYC")
                
                # Account age
                age_risk = self._assess_account_age(user)
                risk_score += age_risk * self.risk_weights["account_age"] * 100
                if age_risk > 0.5:
                    risk_factors.append("New account")
                
                # Transaction patterns
                pattern_risk = await self._assess_transaction_patterns(user, db_session)
                risk_score += pattern_risk * self.risk_weights["transaction_pattern"] * 100
                if pattern_risk > 0.5:
                    risk_factors.append("Suspicious transaction patterns")
                
                # Transaction volume
                volume_risk = await self._assess_transaction_volume(user, db_session)
                risk_score += volume_risk * self.risk_weights["transaction_volume"] * 100
                if volume_risk > 0.5:
                    risk_factors.append("High transaction volume")
                
                # Velocity
                velocity_risk = await self._assess_transaction_velocity(user, db_session)
                risk_score += velocity_risk * self.risk_weights["velocity"] * 100
                if velocity_risk > 0.5:
                    risk_factors.append("High transaction velocity")
                
                # Cap risk score at 100
                risk_score = min(int(risk_score), 100)
                
                # Determine risk level
                risk_level = self._determine_risk_level(risk_score)
                
                # Calculate next review date
                next_review_date = self._calculate_next_review_date(risk_level)
                
                return RiskAssessment(
                    user_id=user_id,
                    risk_score=risk_score,
                    risk_level=risk_level, 
                    risk_factors=risk_factors,
                    assessment_date=datetime.utcnow(),
                    next_review_date=next_review_date
                )
                
            except Exception as e:
                self.logger.error(f"Risk assessment failed for user {user_id}: {e}")
                raise RiskAssessmentError(f"Risk assessment failed: {str(e)}")
        
        if session:
            return await _assess_risk(session)
        else:
            async with get_async_session_context() as db_session:
                return await _assess_risk(db_session)
    
    # ========================================================================
    # Transaction Compliance Checks
    # ========================================================================
    
    async def check_transaction_compliance(
        self,
        user_id: UUID,
        transaction_type: TransactionType,
        amount: Decimal,
        currency: str,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Check transaction compliance requirements.
        
        Args:
            user_id: User ID
            transaction_type: Transaction type
            amount: Transaction amount
            currency: Currency code
            session: Database session
            
        Returns:
            Dict[str, Any]: Compliance check results
            
        Raises:
            ComplianceError: If compliance check fails
        """
        async def _check_compliance(db_session: AsyncSession) -> Dict[str, Any]:
            compliance_results = {
                "approved": True,
                "requires_kyc": False,
                "requires_aml_screening": False,
                "transaction_limits_exceeded": False,
                "risk_level": "low",
                "restrictions": []
            }
            
            # Get user
            user_result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise ComplianceError("User not found")
            
            # Check KYC requirements
            if user.kyc_status != KYCStatus.APPROVED:
                if amount > Decimal('1000'):  # Require KYC for amounts > $1000
                    compliance_results["requires_kyc"] = True
                    compliance_results["approved"] = False
                    compliance_results["restrictions"].append("KYC verification required for large amounts")
            
            # Check transaction limits
            limits_check = await self._check_transaction_limits(user_id, amount, currency, db_session)
            if not limits_check["within_limits"]:
                compliance_results["transaction_limits_exceeded"] = True
                compliance_results["approved"] = False
                compliance_results["restrictions"].extend(limits_check["violations"])
            
            # Check if AML screening is required
            if amount > settings.compliance.suspicious_activity_threshold:
                compliance_results["requires_aml_screening"] = True
            
            # Assess transaction risk
            risk_assessment = await self.assess_user_risk(user_id, db_session)
            compliance_results["risk_level"] = risk_assessment.risk_level.value
            
            if risk_assessment.risk_level == RiskLevel.HIGH:
                compliance_results["requires_aml_screening"] = True
            
            if risk_assessment.risk_level == RiskLevel.CRITICAL:
                compliance_results["approved"] = False
                compliance_results["restrictions"].append("Account flagged for manual review")
            
            return compliance_results
        
        if session:
            return await _check_compliance(session)
        else:
            async with get_async_session_context() as db_session:
                return await _check_compliance(db_session)
    
    async def check_cross_border_compliance(
        self,
        user_id: UUID,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        recipient_info: Dict[str, Any],
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Check cross-border payment compliance.
        
        Args:
            user_id: User ID
            amount: Payment amount
            source_currency: Source currency
            destination_currency: Destination currency
            recipient_info: Recipient information
            session: Database session
            
        Returns:
            Dict[str, Any]: Compliance check results
        """
        async def _check_cross_border(db_session: AsyncSession) -> Dict[str, Any]:
            # Start with basic transaction compliance
            compliance_results = await self.check_transaction_compliance(
                user_id, TransactionType.CROSS_BORDER_PAYMENT, amount, source_currency, db_session
            )
            
            # Additional cross-border checks
            recipient_country = recipient_info.get("country")
            if recipient_country in self.high_risk_countries:
                compliance_results["approved"] = False
                compliance_results["restrictions"].append(f"Payments to {recipient_country} are restricted")
            
            # Large amount reporting
            if amount > settings.compliance.large_transaction_threshold:
                compliance_results["requires_reporting"] = True
                compliance_results["restrictions"].append("Large transaction reporting required")
            
            return compliance_results
        
        if session:
            return await _check_cross_border(session)
        else:
            async with get_async_session_context() as db_session:
                return await _check_cross_border(db_session)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _calculate_kyc_risk_score(
        self,
        personal_info: Dict[str, Any],
        session: AsyncSession
    ) -> int:
        """Calculate KYC risk score based on personal information."""
        risk_score = 0
        
        # Country risk
        country = personal_info.get("country")
        if country in self.high_risk_countries:
            risk_score += 40
        elif country in self.medium_risk_countries:
            risk_score += 20
        
        # Age risk (younger users may be higher risk)
        date_of_birth = personal_info.get("date_of_birth")
        if date_of_birth:
            try:
                birth_date = datetime.fromisoformat(date_of_birth).date()
                age = (datetime.now().date() - birth_date).days // 365
                if age < 18:
                    risk_score += 50  # Underage
                elif age < 25:
                    risk_score += 15  # Young adult
            except:
                risk_score += 10  # Invalid date
        
        # Occupation risk
        occupation = personal_info.get("occupation", "").lower()
        high_risk_occupations = ["politician", "pep", "arms dealer", "casino"]
        if any(risk_occ in occupation for risk_occ in high_risk_occupations):
            risk_score += 30
        
        return min(risk_score, 100)
    
    async def _calculate_aml_risk_score(
        self,
        screening_results: Dict[str, Any],
        user: User,
        session: AsyncSession
    ) -> int:
        """Calculate AML risk score."""
        risk_score = 0
        
        # Screening matches
        matches = screening_results.get("matches", [])
        if matches:
            risk_score += len(matches) * 20
        
        # User profile risk
        if user.profile:
            if user.profile.country in self.high_risk_countries:
                risk_score += 30
            elif user.profile.country in self.medium_risk_countries:
                risk_score += 15
        
        return min(risk_score, 100)
    
    async def _calculate_transaction_risk_score(
        self,
        transaction: Transaction,
        session: AsyncSession
    ) -> int:
        """Calculate transaction-specific risk score."""
        risk_score = 0
        
        # Large amount
        if transaction.amount > settings.compliance.large_transaction_threshold:
            risk_score += 25
        
        # Suspicious amount threshold
        if transaction.amount > settings.compliance.suspicious_activity_threshold:
            risk_score += 40
        
        # Transaction type risk
        if transaction.transaction_type == TransactionType.CROSS_BORDER_PAYMENT:
            risk_score += 10
        
        return min(risk_score, 100)
    
    async def _perform_aml_screening(self, screening_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform AML screening (simplified implementation)."""
        # In a real implementation, this would call external AML providers
        # For now, return mock results
        return {
            "matches": [],
            "status": "clear",
            "provider_reference": f"mock_screening_{datetime.utcnow().timestamp()}"
        }
    
    async def _perform_transaction_aml_screening(self, screening_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform transaction AML screening."""
        # Mock implementation
        return {
            "matches": [],
            "status": "clear",
            "provider_reference": f"mock_txn_screening_{datetime.utcnow().timestamp()}"
        }
    
    def _assess_country_risk(self, user: User) -> float:
        """Assess country-based risk."""
        if not user.profile or not user.profile.country:
            return 0.3  # Unknown country = medium risk
        
        country = user.profile.country
        if country in self.high_risk_countries:
            return 1.0
        elif country in self.medium_risk_countries:
            return 0.6
        else:
            return 0.1
    
    def _assess_kyc_completeness(self, user: User) -> float:
        """Assess KYC completeness risk."""
        if user.kyc_status == KYCStatus.APPROVED:
            return 0.0
        elif user.kyc_status == KYCStatus.IN_PROGRESS:
            return 0.3
        else:
            return 0.8
    
    def _assess_account_age(self, user: User) -> float:
        """Assess account age risk."""
        account_age = datetime.utcnow() - user.created_at
        age_days = account_age.days
        
        if age_days < 1:
            return 1.0  # Very new account
        elif age_days < 7:
            return 0.7  # New account
        elif age_days < 30:
            return 0.4  # Recent account
        else:
            return 0.1  # Established account
    
    async def _assess_transaction_patterns(self, user: User, session: AsyncSession) -> float:
        """Assess transaction pattern risk."""
        # Simplified pattern analysis
        recent_transactions = [txn for txn in user.transactions if 
                             (datetime.utcnow() - txn.created_at).days <= 30]
        
        if len(recent_transactions) > 100:  # Very high activity
            return 0.8
        elif len(recent_transactions) > 50:  # High activity
            return 0.5
        else:
            return 0.1
    
    async def _assess_transaction_volume(self, user: User, session: AsyncSession) -> float:
        """Assess transaction volume risk."""
        # Calculate 30-day volume
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_transactions = [txn for txn in user.transactions if txn.created_at >= thirty_days_ago]
        
        total_volume = sum(txn.amount for txn in recent_transactions)
        
        if total_volume > 100000:  # > $100k
            return 1.0
        elif total_volume > 50000:  # > $50k
            return 0.7
        elif total_volume > 10000:  # > $10k
            return 0.4
        else:
            return 0.1
    
    async def _assess_transaction_velocity(self, user: User, session: AsyncSession) -> float:
        """Assess transaction velocity risk."""
        # Check for rapid-fire transactions
        recent_transactions = sorted(
            [txn for txn in user.transactions if 
             (datetime.utcnow() - txn.created_at).days <= 1],
            key=lambda x: x.created_at
        )
        
        if len(recent_transactions) < 2:
            return 0.1
        
        # Check for transactions within short time windows
        rapid_transactions = 0
        for i in range(1, len(recent_transactions)):
            time_diff = recent_transactions[i].created_at - recent_transactions[i-1].created_at
            if time_diff.total_seconds() < 300:  # 5 minutes
                rapid_transactions += 1
        
        if rapid_transactions > 5:
            return 1.0
        elif rapid_transactions > 2:
            return 0.6
        else:
            return 0.1
    
    def _determine_risk_level(self, risk_score: int) -> RiskLevel:
        """Determine risk level from score."""
        if risk_score >= settings.compliance.high_risk_threshold:
            return RiskLevel.HIGH
        elif risk_score >= settings.compliance.medium_risk_threshold:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_next_review_date(self, risk_level: RiskLevel) -> datetime:
        """Calculate next review date based on risk level."""
        if risk_level == RiskLevel.HIGH:
            return datetime.utcnow() + timedelta(days=30)  # Monthly review
        elif risk_level == RiskLevel.MEDIUM:
            return datetime.utcnow() + timedelta(days=90)  # Quarterly review
        else:
            return datetime.utcnow() + timedelta(days=365)  # Annual review
    
    async def _check_transaction_limits(
        self,
        user_id: UUID,
        amount: Decimal,
        currency: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Check if transaction exceeds limits."""
        # Get user's recent transactions
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        # Daily limit check
        daily_result = await session.execute(
            select(func.sum(Transaction.amount))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= one_day_ago,
                    Transaction.currency == currency
                )
            )
        )
        daily_volume = daily_result.scalar() or Decimal('0')
        
        # Monthly limit check
        monthly_result = await session.execute(
            select(func.sum(Transaction.amount))
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= thirty_days_ago,
                    Transaction.currency == currency
                )
            )
        )
        monthly_volume = monthly_result.scalar() or Decimal('0')
        
        violations = []
        
        # Check single transaction limit
        if amount > settings.compliance.single_transaction_limit:
            violations.append(f"Single transaction limit exceeded: {amount} > {settings.compliance.single_transaction_limit}")
        
        # Check daily limit
        if daily_volume + amount > settings.compliance.daily_transaction_limit:
            violations.append(f"Daily limit exceeded: {daily_volume + amount} > {settings.compliance.daily_transaction_limit}")
        
        # Check monthly limit
        if monthly_volume + amount > settings.compliance.monthly_transaction_limit:
            violations.append(f"Monthly limit exceeded: {monthly_volume + amount} > {settings.compliance.monthly_transaction_limit}")
        
        return {
            "within_limits": len(violations) == 0,
            "violations": violations,
            "daily_volume": daily_volume,
            "monthly_volume": monthly_volume
        }

