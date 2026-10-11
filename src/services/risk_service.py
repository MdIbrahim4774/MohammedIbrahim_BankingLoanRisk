from typing import List, Dict, Any, Tuple
from src.core.config import settings

class RiskAnalysisService:
    @staticmethod
    def calculate_metrics(
        limit_bal: float,
        pay_statuses: List[int],
        bill_amounts: List[float],
        pay_amounts: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate key financial and behavioral metrics from customer payment series.
        """
        # Ensure positive limit
        safe_limit = max(float(limit_bal), 1.0)
        
        # Max delay (months)
        max_delay = max(pay_statuses) if pay_statuses else 0
        recent_delay = pay_statuses[0] if pay_statuses else 0
        delinquent_months_count = sum(1 for s in pay_statuses if s > 0)
        
        # Bills and payments averages
        avg_bill = sum(bill_amounts) / max(len(bill_amounts), 1)
        avg_pay = sum(pay_amounts) / max(len(pay_amounts), 1)
        total_bill = sum(bill_amounts)
        total_pay = sum(pay_amounts)
        
        # Utilization ratio (average bill / limit)
        utilization_ratio = round(max(0.0, avg_bill / safe_limit), 4)
        
        # Repayment ratio (total paid / total billed)
        if total_bill > 0:
            repayment_ratio = round(min(2.0, max(0.0, total_pay / total_bill)), 4)
        else:
            repayment_ratio = 1.0 if total_pay >= 0 else 0.0

        return {
            "max_delay_months": max_delay,
            "recent_delay": recent_delay,
            "delinquent_months_count": delinquent_months_count,
            "avg_bill_amt": round(avg_bill, 2),
            "avg_pay_amt": round(avg_pay, 2),
            "total_bill_amt": round(total_bill, 2),
            "total_pay_amt": round(total_pay, 2),
            "utilization_ratio": utilization_ratio,
            "repayment_ratio": repayment_ratio
        }

    @classmethod
    def evaluate_risk(
        cls,
        limit_bal: float,
        pay_statuses: List[int],
        bill_amounts: List[float],
        pay_amounts: List[float],
        default_next_month: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluate risk score, risk band (Low, Medium, High), and manual review triggers.
        """
        metrics = cls.calculate_metrics(limit_bal, pay_statuses, bill_amounts, pay_amounts)
        
        max_delay = metrics["max_delay_months"]
        recent_delay = metrics["recent_delay"]
        delinq_count = metrics["delinquent_months_count"]
        util = metrics["utilization_ratio"]
        repay = metrics["repayment_ratio"]
        
        # Base credit risk score calculation (0 to 100 scale)
        score = 15.0
        
        # 1. Delinquency factor (up to 45 pts)
        if max_delay >= 2:
            score += 35.0 + min(10.0, (max_delay - 2) * 2.5)
        elif max_delay == 1:
            score += 20.0
        elif recent_delay > 0:
            score += 15.0
        score += min(10.0, delinq_count * 3.0)
        
        # 2. Credit Utilization factor (up to 25 pts)
        if util >= settings.HIGH_RISK_UTILIZATION_THRESHOLD:
            score += 25.0
        elif util >= settings.MED_RISK_UTILIZATION_THRESHOLD:
            score += 15.0
        elif util >= 0.40:
            score += 8.0
            
        # 3. Repayment capability factor (up to 20 pts)
        if repay < settings.HIGH_RISK_REPAYMENT_RATIO_THRESHOLD:
            score += 20.0
        elif repay < settings.MED_RISK_REPAYMENT_RATIO_THRESHOLD:
            score += 10.0
        elif repay >= 0.90:
            score -= 5.0  # Reward reliable full payers
            
        # 4. Known default indicator
        if default_next_month == 1:
            score += 15.0

        risk_score = round(min(100.0, max(0.0, score)), 2)

        # Documented Risk Bands:
        # High Risk:
        # - max_delay_months >= 2 OR
        # - utilization_ratio >= 0.85 AND repayment_ratio < 0.20 OR
        # - default_payment_next_month == 1 OR
        # - risk_score >= 65
        # Medium Risk:
        # - max_delay_months == 1 OR
        # - utilization_ratio between 0.60 and 0.85 OR
        # - repayment_ratio between 0.20 and 0.50 OR
        # - risk_score between 35 and 64
        # Low Risk:
        # - max_delay_months <= 0 AND utilization_ratio < 0.60 AND repayment_ratio >= 0.50
        
        is_high = (
            max_delay >= settings.HIGH_RISK_MAX_DELAY_MONTHS or
            (util >= settings.HIGH_RISK_UTILIZATION_THRESHOLD and repay < settings.HIGH_RISK_REPAYMENT_RATIO_THRESHOLD) or
            default_next_month == 1 or
            risk_score >= 65.0
        )
        
        is_medium = (
            max_delay == 1 or
            (util >= settings.MED_RISK_UTILIZATION_THRESHOLD and util < settings.HIGH_RISK_UTILIZATION_THRESHOLD) or
            (repay >= settings.HIGH_RISK_REPAYMENT_RATIO_THRESHOLD and repay < settings.MED_RISK_REPAYMENT_RATIO_THRESHOLD) or
            (35.0 <= risk_score < 65.0)
        )
        
        if is_high:
            risk_band = "High"
        elif is_medium:
            risk_band = "Medium"
        else:
            risk_band = "Low"

        # Configurable Business Rules for Additional Review
        review_reasons = []
        rule_triggers = {}
        
        # Rule 1: High exposure account (> 500,000 NTD) with any payment delay
        rule_1_triggered = (limit_bal >= settings.REVIEW_CREDIT_LIMIT_THRESHOLD and max_delay >= 1)
        rule_triggers["high_exposure_delinquency"] = rule_1_triggered
        if rule_1_triggered:
            review_reasons.append(f"High credit limit exposure (NT${limit_bal:,.0f}) with {max_delay}-month payment delay")
            
        # Rule 2: High credit utilization (> 90%) with low repayment (< 15%)
        rule_2_triggered = (util >= settings.REVIEW_UTILIZATION_THRESHOLD and repay < 0.15)
        rule_triggers["extreme_utilization_low_repayment"] = rule_2_triggered
        if rule_2_triggered:
            review_reasons.append(f"Overleveraged account: {util*100:.1f}% credit utilization with only {repay*100:.1f}% repayment ratio")
            
        # Rule 3: Chronic payment delay across multiple billing cycles
        rule_3_triggered = (delinq_count >= settings.REVIEW_CONSECUTIVE_DELAYS and max_delay >= 2)
        rule_triggers["chronic_delinquency"] = rule_3_triggered
        if rule_3_triggered:
            review_reasons.append(f"Chronic payment distress: Delinquency recorded in {delinq_count} billing cycles")
            
        # Rule 4: High active balance with zero recent payment
        latest_bill = bill_amounts[0] if bill_amounts else 0.0
        latest_pay = pay_amounts[0] if pay_amounts else 0.0
        rule_4_triggered = (latest_bill >= 50000.0 and latest_pay <= 0.0 and recent_delay >= 1)
        rule_triggers["large_balance_zero_repayment"] = rule_4_triggered
        if rule_4_triggered:
            review_reasons.append(f"Substantial outstanding balance (NT${latest_bill:,.0f}) with zero recent repayment")

        requires_review = len(review_reasons) > 0 or (risk_band == "High" and limit_bal >= 300000.0)

        # Recommendation
        if risk_band == "High":
            recommendation = "DECLINE_OR_RESTRICT" if not requires_review else "URGENT_CREDIT_REVIEW"
        elif risk_band == "Medium" or requires_review:
            recommendation = "MANUAL_UNDERWRITER_REVIEW"
        else:
            recommendation = "STANDARD_APPROVAL"

        return {
            "risk_score": risk_score,
            "risk_band": risk_band,
            "utilization_ratio": util,
            "max_delay_months": max_delay,
            "avg_bill_amt": metrics["avg_bill_amt"],
            "avg_pay_amt": metrics["avg_pay_amt"],
            "repayment_ratio": repay,
            "requires_manual_review": requires_review,
            "review_reasons": review_reasons,
            "rule_triggers": rule_triggers,
            "approval_recommendation": recommendation
        }

risk_service = RiskAnalysisService()

